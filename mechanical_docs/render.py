"""Render stage, run inside Blender: part thumbnails, an overview and one or two images per step.

    blender -b --python mechanical_docs/render.py -- PROJECT_DIR MESHES_JSON OUT_DIR [--preview] [--views a,b] [--engine E] [--no-lines]
                                                     [--groups ASSEMBLY_ID,...] [--reuse RENDER_DIR]

Reads the validated project (manifest.py), the CAD stage's meshes.json and the
project's optional render.json (illustration settings: looks, sizes). Imports
each part's GLB once, instantiates every occurrence at its canonical world
pose (the scene's +Z-up frame, scaled to metres exactly once), and renders:

    part-<part>.png          the part alone, auto-framed, for the inventory; a long
                             part (extrusion, profile) is turned with its long axis
                             along X and drawn in a wide image
    part-<part>-end.png      a long part seen straight along its long axis: the
                             profile or end detail that identifies it
    overview.png             the finished assembly, instruction camera
    exploded.png             the subassemblies drawn apart (render.json `exploded_view`): every
                             child assembly of the root and the parts directly under it moved
                             as a rigid body by a recorded offset (radial default or the
                             project's override); an illustration, not an order
    group-<assembly>.png     one subassembly alone, every occurrence at its canonical
                             pose, auto-framed: an inspection/parts view, not a step
    joint-<joint>.png        a close-up of one project joint (render.json `joint_views`):
                             the listed occurrences framed alone at their canonical
                             poses, the rest of their context assembly faded or
                             hidden: an inspection view, not a step
    step-NN-<step>.png       parts installed before the step ghosted (flat grey over
                             transparency, `step_context_alpha`; thin outline), the step's additions in
                             their looks with a thick outline, later parts hidden;
                             with an approach hint the addition is drawn displaced
                             by the hint's start offset and an arrow points along
                             the approach to its seat
    step-NN-<step>-result.png  the same step with the addition seated (only when
                             the step has an approach hint)

Every step image uses the instruction view's eye/target/up and one orthographic
scale computed from the whole procedure (final poses and approach poses), so the
camera does not move between steps. Canonical poses are restored and verified
after each view; an approach offset can never leak into the next image.
hotspots/<view>.json carries each visible occurrence's projected pixel box for
web callouts. render-receipt.json records versions, settings, hashes and checks.

--reuse RENDER_DIR copies views from an earlier complete receipt made from the
same scene, assets, instructions, meshes, engine and quality instead of
rendering them again (the inventory and the supplement never change an image,
so they may differ); only views named in --views, absent from that receipt, or
stale under the current settings (a joint view whose specification changed, a
view whose line-art state would differ under the current budget; see reuse.py)
are rendered. Other appearance changes need --views. Each copied
view keeps its own record plus `reused_from`, so the receipt stays honest about
what was rendered when and under which settings.

Studio lighting, look palette, Freestyle subject/context outlines, projection
framing and the matrix_basis restore are adapted from mouse-joysticks-mech
atlas/render.py (commit 22aa7544, Peter Polidoro); station, board and
model-size-unit heuristics were not carried over.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mechanical_docs import explode, geometry, receipts  # noqa: E402
from mechanical_docs import transforms as T  # noqa: E402
from mechanical_docs.manifest import ManifestError, load_project  # noqa: E402
from mechanical_docs.names import slug  # noqa: E402
from mechanical_docs.procedure import approach_pose, derive_states  # noqa: E402
from mechanical_docs.render_settings import load_settings  # noqa: E402
from mechanical_docs.reuse import stale_reason  # noqa: E402

import bpy  # noqa: E402  (only inside Blender)
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402


def log(*a):
    print("[render]", *a, flush=True)


def to_blender(world, factor):
    """A scene-frame 4x4 (declared units) as a Blender matrix in metres."""
    return Matrix(T.scaled_translation(world, factor))


def box_corners(mn, mx):
    return [Vector((x, y, z)) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]


def aabb_of(points):
    mn = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    mx = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return mn, mx


def common_ancestor(scene, occ_ids):
    """The deepest assembly containing every listed occurrence (the root when
    nothing deeper does)."""
    paths = [scene.occurrences[o].path for o in occ_ids]
    common = []
    for level in zip(*paths):
        if len(set(level)) != 1:
            break
        common.append(level[0])
    return common[-1] if common else scene.root_id


def resolve_joint_views(scene, specs):
    """Check `joint_views` against the scene and fill the defaults: view id,
    context assembly (deepest common ancestor unless given)."""
    out = []; seen = set()
    for i, jv in enumerate(specs):
        where = f"render.json joint_views[{i}] ({jv['joint_id']})"
        for oid in jv["occurrence_ids"]:
            if oid not in scene.occurrences:
                hint = " (an assembly id; list its occurrences, or use inspection_groups)" if oid in scene.assemblies else ""
                raise SystemExit(f"{where}: {oid!r} is not an occurrence id in the scene{hint}")
        ctx = jv.get("context")
        if ctx is None:
            ctx_ids = [common_ancestor(scene, jv["occurrence_ids"])]
        else:
            # an explicit context is any set of assembly and/or occurrence ids; the
            # subjects need not lie under it (a joint between two groups fades one frame)
            ctx_ids = [ctx] if isinstance(ctx, str) else list(ctx)
            for c in ctx_ids:
                if c not in scene.assemblies and c not in scene.occurrences:
                    raise SystemExit(f"{where}: context {c!r} is not an assembly or occurrence id in the scene")
        vid = f"joint-{slug(jv.get('id') or jv['joint_id'])}"
        if vid in seen:
            raise SystemExit(f"{where}: view id {vid!r} repeats; give each view of a joint its own 'id'")
        seen.add(vid)
        out.append({"view_id": vid, "id": jv.get("id"), "joint_id": jv["joint_id"], "occurrence_ids": list(jv["occurrence_ids"]),
                    "direction": jv.get("direction"), "context": ctx_ids, "context_style": jv["context_style"]})
    return out


def context_members(scene, ctx_ids):
    """Occurrence ids of the context: every occurrence under each assembly id,
    plus each occurrence id itself; scene order, no repeats."""
    out = []
    for c in ctx_ids:
        for oid in (scene.members(c) if c in scene.assemblies else [c]):
            if oid not in out:
                out.append(oid)
    return out


class Renderer:
    def __init__(self, project, meshes, settings, out_dir, preview, engine=None, lines=True):
        self.project = project
        self.lines_enabled = lines and settings["lines"]["enabled"]
        self.last_view = {}
        self.scene = project.scene
        self.meshes = meshes
        self.s = settings
        self.out = Path(out_dir)
        self.preview = preview
        self.factor = T.unit_factor(self.scene.units, "m")
        self.engine = engine or settings["engine"]
        self.checks = {"mesh_bounds_match": [], "restoration": [], "problems": []}
        self.warnings = []
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scn = bpy.context.scene
        deferred = project.build_scope.deferred_ids(self.scene) if project.build_scope is not None else ()
        self.states = derive_states(project.instructions, self.scene, deferred) if project.instructions is not None else []
        self.import_meshes()
        self.instantiate()
        self.make_materials()
        self.setup_render()
        self.setup_lines()
        self.setup_camera()
        self.setup_studio()

    # ------------------------------------------------------------ geometry

    def import_meshes(self):
        """One mesh datablock per part, from the CAD stage's GLB. The importer
        converts glTF +Y up to Blender +Z up, so the mesh lies in the scene
        frame in metres; checked against meshes.json bounds."""
        self.mesh_of = {}
        mdir = Path(self.meshes["_path"]).parent
        for pid, rec in self.meshes["parts"].items():
            path = mdir / rec["mesh"]["file"]
            actual = receipts.sha256_file(path)
            if actual != rec["mesh"]["sha256"]:
                raise SystemExit(f"{path}: SHA-256 differs from meshes.json; re-run the CAD stage")
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=str(path), import_shading="NORMALS")
            new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
            if len(new) != 1:
                raise SystemExit(f"{path}: expected one mesh object, imported {len(new)}")
            obj = new[0]
            mesh = obj.data
            mesh.name = f"part:{pid}"
            # the imported object sits at identity: its bounds are the mesh's
            mn = Vector(obj.bound_box[0]); mx = Vector(obj.bound_box[6])
            for c in obj.bound_box:
                mn = Vector(map(min, mn, Vector(c))); mx = Vector(map(max, mx, Vector(c)))
            wmn, wmx = geometry.mesh_bounds_m(rec["mesh"])     # asset units -> m, not scene units
            want_mn, want_mx = Vector(wmn), Vector(wmx)
            dev = max((mn - want_mn).length, (mx - want_mx).length)
            ok = dev < 1e-6 + 1e-4 * rec["mesh"]["frame"]["unit_factor"]
            self.checks["mesh_bounds_match"].append({"part_id": pid, "deviation_m": dev, "passed": ok,
                                                     "blender_bounds_m": [list(mn), list(mx)], "expected_bounds_m": [list(want_mn), list(want_mx)]})
            if not ok:
                self.checks["problems"].append(f"{pid}: imported mesh bounds deviate {dev:.6f} m from meshes.json (unit or frame conversion applied twice or not at all)")
            bpy.data.objects.remove(obj)
            for other in [o for o in bpy.data.objects if o not in before]:
                bpy.data.objects.remove(other)
            self.mesh_of[pid] = mesh
            log(f"mesh {pid}: {len(mesh.vertices)} vertices, {len(mesh.polygons)} triangles, bounds {[round(v, 4) for v in mn]}..{[round(v, 4) for v in mx]} m, bounds check {'ok' if ok else 'FAILED'}")

    def instantiate(self):
        """One object per occurrence sharing its part's mesh, at the canonical pose."""
        self.obj_of = {}
        self.canonical = {}
        for occ in self.scene.occurrences.values():
            o = bpy.data.objects.new(f"occ:{slug(occ.id)}", self.mesh_of[occ.part_id])
            self.scn.collection.objects.link(o)
            o.matrix_world = to_blender(occ.world, self.factor)
            o["occurrence_id"] = occ.id; o["part_id"] = occ.part_id
            self.obj_of[occ.id] = o
            # Blender keeps location/rotation/scale as float32 and recomposes
            # the matrix from them; restoring those properties reproduces the
            # world matrix bit for bit, which a matrix assignment would not.
            self.canonical[occ.id] = (o.location.copy(), o.rotation_euler.copy(), o.scale.copy())
        # thumbnail objects: one per part at identity, hidden unless rendering its thumbnail
        self.thumb_of = {}
        for pid, mesh in self.mesh_of.items():
            o = bpy.data.objects.new(f"thumb:{slug(pid)}", mesh)
            self.scn.collection.objects.link(o)
            o.hide_render = True
            o.matrix_world = Matrix(self.scene.basis_to_z_up)     # show the part the way up the scene is
            o["part_id"] = pid
            self.thumb_of[pid] = o
        bpy.context.view_layer.update()
        self.canonical_world = {oid: o.matrix_world.copy() for oid, o in self.obj_of.items()}
        self.all_objs = list(self.obj_of.values()) + list(self.thumb_of.values())
        # a part's thumbnail style follows its extents (the basis only permutes axes)
        self.thumb_style = {}
        for pid, rec in self.meshes["parts"].items():
            mn, mx = geometry.mesh_bounds_m(rec["mesh"])
            e = sorted((b - a for a, b in zip(mn, mx)), reverse=True)
            aspect = e[0] / max(e[1], 1e-9)
            self.thumb_style[pid] = ("long" if aspect >= self.s["thumbnail_long_aspect"] else "square", round(aspect, 2))
        log(f"{len(self.obj_of)} occurrences instantiated from {len(self.mesh_of)} meshes; "
            f"{sum(1 for st, _ in self.thumb_style.values() if st == 'long')} long part(s) get wide thumbnails and end views")

    # ----------------------------------------------------------- materials

    def make_materials(self):
        self.look_mats = {}
        palette = self.s["palette"]
        for name, spec in palette.items():
            m = bpy.data.materials.new(f"look:{name}"); m.use_nodes = True
            bsdf = m.node_tree.nodes["Principled BSDF"]
            b = spec["base"]
            bsdf.inputs["Base Color"].default_value = (b[0], b[1], b[2], 1)
            bsdf.inputs["Metallic"].default_value = spec.get("metallic", 0.0)
            bsdf.inputs["Roughness"].default_value = spec.get("roughness", 0.5)
            if "coat" in spec:
                bsdf.inputs["Coat Weight"].default_value = spec["coat"]
                bsdf.inputs["Coat Roughness"].default_value = spec.get("coat_roughness", 0.1)
            self.look_mats[name] = m

        def flat(name, color):
            m = bpy.data.materials.new(name); m.use_nodes = True
            nt = m.node_tree
            for node in list(nt.nodes):
                if node.type != "OUTPUT_MATERIAL":
                    nt.nodes.remove(node)
            em = nt.nodes.new("ShaderNodeEmission")
            em.inputs["Color"].default_value = (color[0], color[1], color[2], 1); em.inputs["Strength"].default_value = 1.0
            nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
            return m

        self.context_mat = flat("md_context", self.s["context_color"])

        def ghost(name, color, alpha):
            """The flat context colour over transparency: what a step draws its
            already-installed parts with, so an addition behind them stays visible."""
            m = bpy.data.materials.new(name); m.use_nodes = True
            nt = m.node_tree
            for node in list(nt.nodes):
                if node.type != "OUTPUT_MATERIAL":
                    nt.nodes.remove(node)
            em = nt.nodes.new("ShaderNodeEmission")
            em.inputs["Color"].default_value = (color[0], color[1], color[2], 1); em.inputs["Strength"].default_value = 1.0
            tr = nt.nodes.new("ShaderNodeBsdfTransparent")
            mix = nt.nodes.new("ShaderNodeMixShader"); mix.inputs["Fac"].default_value = alpha
            nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
            nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
            try:
                m.surface_render_method = "BLENDED"       # EEVEE Next
            except Exception:
                pass
            return m

        self.ghost_mat = ghost("md_ghost", self.s["context_color"], self.s["step_context_alpha"]) if self.s["step_context_alpha"] < 1.0 else self.context_mat
        self.arrow_mat = flat("md_arrow", self.s["arrow"]["color"])
        # every mesh gets one slot; objects override it per view (slot link OBJECT)
        for pid, mesh in self.mesh_of.items():
            if not mesh.materials:
                mesh.materials.append(self.part_look(pid))
        for o in self.all_objs:
            o.material_slots[0].link = "OBJECT"
            o.material_slots[0].material = self.part_look(o["part_id"])
        for pid, o in self.thumb_of.items():
            o.material_slots[0].material = self.part_look(pid)

    def part_look(self, pid):
        name = self.s["looks"].get(pid, self.s["default_look"])
        if name not in self.look_mats:
            raise SystemExit(f"render.json: unknown look {name!r} for part {pid!r}; palette has {sorted(self.look_mats)}")
        return self.look_mats[name]

    # -------------------------------------------------------------- studio

    def setup_render(self):
        scn = self.scn; s = self.s
        scn.render.engine = self.engine
        self.denoiser = None
        if self.engine == "CYCLES":
            scn.cycles.device = "CPU"
            scn.cycles.use_adaptive_sampling = True
            scn.cycles.adaptive_threshold = s["cycles_adaptive_threshold"]
            scn.cycles.max_bounces = s["cycles_max_bounces"]
            scn.render.use_persistent_data = s["cycles_persistent_data"]
            try:
                scn.cycles.denoiser = "OPENIMAGEDENOISE"; scn.cycles.use_denoising = True
                scn.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
                self.denoiser = "OPENIMAGEDENOISE"
            except Exception:
                scn.cycles.use_denoising = False
                self.warnings.append("Cycles has no denoiser in this Blender build; renders are noisier than the reference pipeline (use the bpy wheel or more samples)")
        scn.render.film_transparent = s["film_transparent"]
        scn.render.image_settings.file_format = "PNG"
        scn.render.image_settings.color_mode = "RGBA" if s["film_transparent"] else "RGB"
        scn.view_settings.view_transform = s["view_transform"]
        try:
            scn.view_settings.look = s.get("look", "None")
        except Exception:
            scn.view_settings.look = "None"
        scn.view_settings.exposure = s["exposure"]
        world = bpy.data.worlds.new("md_world"); world.use_nodes = True
        bg = world.node_tree.nodes["Background"]
        c = s["world"]["color"]
        bg.inputs[0].default_value = (c[0], c[1], c[2], 1); bg.inputs[1].default_value = s["world"]["strength"]
        scn.world = world

    def setup_lines(self):
        scn = self.scn; L = self.s["lines"]
        self.coll_subject = bpy.data.collections.new("md_subject"); scn.collection.children.link(self.coll_subject)
        self.coll_context = bpy.data.collections.new("md_context"); scn.collection.children.link(self.coll_context)
        scn.render.line_thickness_mode = "ABSOLUTE"
        fs = bpy.context.view_layer.freestyle_settings
        fs.crease_angle = math.radians(L["crease_angle_deg"])
        fs.use_culling = True
        for ls in list(fs.linesets):
            fs.linesets.remove(ls)
        for name, coll, spec in (("subject", self.coll_subject, L["subject"]), ("context", self.coll_context, L["context"])):
            ls = fs.linesets.new(name)
            ls.select_by_collection = True; ls.collection = coll; ls.collection_negation = "INCLUSIVE"
            ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True
            ls.select_edge_mark = False; ls.select_contour = False; ls.select_external_contour = False
            c = spec["color"]
            ls.linestyle.color = (c[0], c[1], c[2]); ls.linestyle.thickness = spec["thickness"]; ls.linestyle.alpha = 1.0
        scn.render.use_freestyle = True

    def setup_camera(self):
        cd = bpy.data.cameras.new("cam"); cd.clip_start = 0.0005; cd.clip_end = 1000
        cd.sensor_fit = "AUTO"; cd.lens = 50
        self.cam = bpy.data.objects.new("cam", cd); self.scn.collection.objects.link(self.cam); self.scn.camera = self.cam

    def setup_studio(self):
        """Three area lights on the bounding sphere of everything the procedure shows."""
        pts = self.procedure_points()
        mn, mx = aabb_of(pts)
        ctr = (mn + mx) / 2; R = max((mx - mn).length / 2, 1e-3)
        self.scene_centre, self.scene_radius = ctr, R
        scale = (R / 0.2) ** 2
        self.lights = []
        for name, spec in self.s["studio"].items():
            ld = bpy.data.lights.new(f"light:{name}", type="AREA")
            ld.shape = "SQUARE"; ld.size = spec["size"] * R; ld.energy = spec["watts"] * scale
            lo = bpy.data.objects.new(f"light:{name}", ld); self.scn.collection.objects.link(lo)
            d = Vector(spec["direction"]).normalized()
            lo.location = ctr + d * spec["distance"] * R
            lo.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
            self.lights.append(lo)
        f = self.s["floor"]
        want = f["enabled"] if f["enabled"] != "auto" else self.engine == "CYCLES"
        self.floor = None
        if want and self.engine == "CYCLES" and self.s["film_transparent"]:
            fm = bpy.data.materials.new("md_floor"); fm.use_nodes = True
            bsdf = fm.node_tree.nodes["Principled BSDF"]
            c = f["color"]
            bsdf.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1)
            bsdf.inputs["Roughness"].default_value = f["roughness"]; bsdf.inputs["Metallic"].default_value = 0.0
            me = bpy.data.meshes.new("md_floor"); size = f["size_factor"] * R
            me.from_pydata([(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0)], [], [(0, 1, 2, 3)])
            me.materials.append(fm)
            self.floor = bpy.data.objects.new("md_floor", me); self.scn.collection.objects.link(self.floor)
            self.floor.is_shadow_catcher = True
        elif want and self.engine != "CYCLES":
            self.warnings.append("floor shadow catcher requested but only Cycles supports it; no floor rendered")
        log(f"studio: centre {[round(v, 4) for v in ctr]} m, R {R:.4f} m, {len(self.lights)} lights, floor {'shadow catcher' if self.floor else 'none'}")

    # -------------------------------------------------------------- framing

    def occurrence_corners(self, occ_id, world=None):
        occ = self.scene.occurrences[occ_id]
        rec = self.meshes["parts"][occ.part_id]["mesh"]
        return [Vector(c) for c in geometry.occurrence_corners_m(rec, world or occ.world, self.scene.units)]

    def procedure_points(self):
        """Bounding-box corners of every occurrence at its final pose and at
        every approach start pose, in metres: what the step camera must frame."""
        pts = []
        for oid in self.scene.occurrences:
            pts += self.occurrence_corners(oid)
        for st in self.states:
            ap = approach_pose(self.scene, st)
            if ap:
                pts += self.occurrence_corners(ap[0], ap[1])
        return pts

    def aim(self, eye, target, up):
        """Camera at eye looking at target; Blender cameras look down -Z with +Y up."""
        f = (target - eye).normalized()
        r = f.cross(up).normalized()
        u = r.cross(f).normalized()
        self.cam.matrix_world = Matrix(((r.x, u.x, -f.x, eye.x), (r.y, u.y, -f.y, eye.y), (r.z, u.z, -f.z, eye.z), (0, 0, 0, 1)))
        bpy.context.view_layer.update()

    def set_resolution(self, long_side, aspect):
        ax = aspect[0] / aspect[1]
        if ax >= 1:
            self.scn.render.resolution_x = long_side; self.scn.render.resolution_y = int(round(long_side / ax))
        else:
            self.scn.render.resolution_y = long_side; self.scn.render.resolution_x = int(round(long_side * ax))
        self.scn.render.resolution_percentage = 100

    def fit(self, points, projection, fill):
        """Orthographic: set ortho_scale and recentre so `points` fill `fill`
        of the frame. Perspective: move the camera along its axis instead."""
        cam, cd, scn = self.cam, self.cam.data, self.scn
        cd.type = "ORTHO" if projection == "orthographic" else "PERSP"
        if cd.type == "ORTHO":
            cd.ortho_scale = max(self.scene_radius * 4, 1e-3)
        R = cam.matrix_world.to_3x3()
        xa, ya, back = R.col[0], R.col[1], R.col[2]
        for _ in range(6):
            bpy.context.view_layer.update()
            pts = [world_to_camera_view(scn, cam, p) for p in points]
            xs = [p.x for p in pts]; ys = [p.y for p in pts]
            w = max(xs) - min(xs); h = max(ys) - min(ys)
            f = max(w, h) / fill
            cx = (max(xs) + min(xs)) / 2 - 0.5; cy = (max(ys) + min(ys)) / 2 - 0.5
            landscape = scn.render.resolution_x >= scn.render.resolution_y
            if cd.type == "ORTHO":
                cd.ortho_scale *= f
                vw = cd.ortho_scale if landscape else cd.ortho_scale * scn.render.resolution_x / scn.render.resolution_y
            else:
                loc = cam.matrix_world.translation
                centre = loc - back * (loc - self.scene_centre).dot(back)
                dist = (loc - centre).length * f
                cam.matrix_world.translation = centre + back * dist
                vw = 2 * dist * math.tan(cd.angle / 2) * (1 if landscape else scn.render.resolution_x / scn.render.resolution_y)
            vh = vw * scn.render.resolution_y / scn.render.resolution_x
            cam.matrix_world.translation = cam.matrix_world.translation + xa * cx * vw + ya * cy * vh
            if abs(f - 1) < 1e-4 and abs(cx) < 1e-4 and abs(cy) < 1e-4:
                break
        bpy.context.view_layer.update()
        pts = [world_to_camera_view(scn, cam, p) for p in points]
        return all(0 <= p.x <= 1 and 0 <= p.y <= 1 for p in pts)

    # --------------------------------------------------------------- arrow

    def make_arrow(self, start, end, part_size):
        """A shaft and head from start to end (metres). Removed by restore()."""
        a = self.s["arrow"]
        d = end - start; L = d.length
        if L < 1e-9:
            return None
        d.normalize()
        r = max(part_size * a["shaft_fraction"], self.scene_radius * 0.004)
        head_len = min(r * a["head_length_factor"], L * 0.5)
        shaft_len = L - head_len
        rot = d.to_track_quat("Z", "Y")
        objs = []
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=shaft_len, vertices=24, location=start + d * shaft_len / 2)
        shaft = bpy.context.active_object; shaft.rotation_euler = rot.to_euler(); objs.append(shaft)
        bpy.ops.mesh.primitive_cone_add(radius1=r * a["head_radius_factor"], radius2=0, depth=head_len, vertices=24, location=start + d * (shaft_len + head_len / 2))
        head = bpy.context.active_object; head.rotation_euler = rot.to_euler(); objs.append(head)
        for o in objs:
            o.name = "md_arrow"; o.data.materials.append(self.arrow_mat)
            self.coll_subject.objects.link(o)
        bpy.context.view_layer.update()
        return objs

    # --------------------------------------------------------------- views

    def restore(self):
        for oid, o in self.obj_of.items():
            o.location, o.rotation_euler, o.scale = self.canonical[oid]
            o.hide_render = False
            o.material_slots[0].material = self.part_look(o["part_id"])
        for o in self.thumb_of.values():
            o.hide_render = True
        for coll in (self.coll_subject, self.coll_context):
            for o in list(coll.objects):
                coll.objects.unlink(o)
        for o in [o for o in bpy.data.objects if o.name.startswith("md_arrow")]:
            me = o.data; bpy.data.objects.remove(o); bpy.data.meshes.remove(me)
        bpy.context.view_layer.update()

    def verify_restored(self, view_id):
        """Every occurrence is back at its canonical pose: its world matrix equals
        the one captured at instantiation exactly (both float32), and matches
        the scene's double-precision pose to a micrometre."""
        worst = 0.0
        exact = True
        bpy.context.view_layer.update()
        for oid, o in self.obj_of.items():
            exact &= all(a == b for ra, rb in zip(o.matrix_world, self.canonical_world[oid]) for a, b in zip(ra, rb))
            want = to_blender(self.scene.occurrences[oid].world, self.factor)
            dev = max(abs(a - b) for ra, rb in zip(o.matrix_world, want) for a, b in zip(ra, rb))
            worst = max(worst, dev)
        ok = exact and worst < 1e-6 and not any(o.name.startswith("md_arrow") for o in bpy.data.objects)
        self.checks["restoration"].append({"after_view": view_id, "world_restored_exactly": exact, "max_pose_deviation_m": worst, "passed": ok})
        if not ok:
            self.checks["problems"].append(f"canonical poses not restored after {view_id} (deviation {worst})")

    def place_floor(self, objs, kind):
        """The shadow catcher just under the lowest visible point (never under a
        lifted part alone: the lowest *visible* object sets it), for the view
        kinds the settings name; hidden otherwise."""
        if self.floor is None:
            return
        self.floor.hide_render = kind not in self.s["floor"]["views"]
        pts = [o.matrix_world @ Vector(c) for o in objs if not o.hide_render for c in o.bound_box]
        if not pts or self.floor.hide_render:
            bpy.context.view_layer.update()
            return
        self.floor.location = Vector((self.scene_centre.x, self.scene_centre.y, min(p.z for p in pts) - 1e-4))
        # a camera at or below the catcher plane would see only the catcher (a view
        # from below the frame): no floor for such a view, recorded per view
        if self.cam.matrix_world.translation.z <= self.floor.location.z + 1e-6:
            self.floor.hide_render = True
        bpy.context.view_layer.update()

    def visible_triangles(self):
        return sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and o is not self.floor)

    def render_to(self, view_id, samples):
        scn = self.scn
        # a line set over an empty collection logs "strokes set empty"; skip it
        for ls in bpy.context.view_layer.freestyle_settings.linesets:
            ls.show_render = bool(ls.collection and ls.collection.objects)
        # Freestyle's cost grows superlinearly with the visible edge count: over budget, no lines for this view
        tris = self.visible_triangles()
        budget = self.s["lines"]["preview_max_triangles" if self.preview else "max_triangles"]
        lines = self.lines_enabled and tris <= budget
        if self.lines_enabled and not lines:
            self.warnings.append(f"{view_id}: {tris} visible triangles exceed lines.max_triangles ({budget}); rendered without line art")
        scn.render.use_freestyle = lines
        self.last_view = {"lines": lines, "visible_triangles": tris}
        if self.engine == "CYCLES":
            scn.cycles.samples = samples
        elif self.engine.startswith("BLENDER_EEVEE"):
            scn.eevee.taa_render_samples = samples
        path = self.out / f"{view_id}.png"
        scn.render.filepath = str(path)
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        return path, time.time() - t0

    def hotspots(self, view_id, visible_ids):
        scn, cam = self.scn, self.cam
        W, H = scn.render.resolution_x, scn.render.resolution_y
        out = {"view": view_id, "width": W, "height": H, "occurrences": []}
        for oid in visible_ids:
            o = self.obj_of[oid]
            corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
            pts = [world_to_camera_view(scn, cam, c) for c in corners]
            xs = [p.x for p in pts]; ys = [p.y for p in pts]
            inside = sum(1 for p in pts if 0 <= p.x <= 1 and 0 <= p.y <= 1)
            box = [max(0, min(xs)) * W, (1 - min(1, max(ys))) * H, min(1, max(xs)) * W, (1 - max(0, min(ys))) * H]
            out["occurrences"].append({"id": oid, "part_id": o["part_id"], "box_px": [round(v, 1) for v in box], "corners_in_frame": inside})
        return out

    def overview_camera(self):
        """The first step's instruction view when there are instructions; otherwise
        an automatic orthographic view from `overview_direction`, framing every
        occurrence."""
        if self.project.instructions is not None:
            return self.step_camera_for(self.project.instructions.steps[0].view)
        self.set_resolution(self.long_side(), self.s["aspect"])
        pts = self.procedure_points()
        mn, mx = aabb_of(pts); ctr = (mn + mx) / 2
        d = Vector(self.s["overview_direction"]).normalized()
        self.aim(ctr + d * max((mx - mn).length, 1e-3) * 4, ctr, Vector((0, 0, 1)))
        return self.fit(pts, "orthographic", self.s["fill"])

    def step_camera_for(self, view_id):
        v = self.project.instructions.views[view_id]
        self.set_resolution(self.long_side(), self.s["aspect"])
        self.aim(Vector(v.eye) * self.factor, Vector(v.target) * self.factor, Vector(v.up))
        return self.fit(self.procedure_points(), v.projection, self.s["fill"])

    def long_side(self):
        return self.s["preview_long_side_px"] if self.preview else self.s["long_side_px"]

    def samples(self):
        if self.engine == "CYCLES":
            return self.s["cycles_preview_samples"] if self.preview else self.s["cycles_samples"]
        return self.s["preview_samples"] if self.preview else self.s["samples"]

    def view_record(self, view_id, path, secs, **extra):
        rec = {"id": view_id, "file": path.name, "sha256": receipts.sha256_file(path), "bytes": path.stat().st_size,
               "floor_shadow_catcher": bool(self.floor is not None and not self.floor.hide_render),
               "width": self.scn.render.resolution_x, "height": self.scn.render.resolution_y, "seconds": round(secs, 1),
               "lines": self.last_view.get("lines"), "visible_triangles": self.last_view.get("visible_triangles"),
               "camera": {"type": self.cam.data.type, "ortho_scale_m": self.cam.data.ortho_scale if self.cam.data.type == "ORTHO" else None,
                          "location_m": list(self.cam.matrix_world.translation)}}
        rec.update(extra)
        return rec

    def thumbnail_pose(self, t):
        """Pose the thumbnail object (never an occurrence) for its picture: the
        scene's up orientation, and for a long part a turn that lays its long
        axis along X. Returns (style, long axis letter in the part's own frame)."""
        t.matrix_world = Matrix(self.scene.basis_to_z_up)
        bpy.context.view_layer.update()
        mn, mx = aabb_of([t.matrix_world @ Vector(c) for c in t.bound_box])
        e = mx - mn
        longest = max(range(3), key=lambda i: e[i])
        # the long axis in the part's own frame: the basis column that maps onto `longest`
        B = Matrix(self.scene.basis_to_z_up).to_3x3()
        part_axis = max(range(3), key=lambda j: abs(B[longest][j]))
        style = self.thumb_style[t["part_id"]][0]
        if style == "long":
            if longest == 1:
                t.matrix_world = Matrix.Rotation(-math.pi / 2, 4, "Z") @ t.matrix_world   # Y -> X
            elif longest == 2:
                t.matrix_world = Matrix.Rotation(math.pi / 2, 4, "Y") @ t.matrix_world    # Z -> X
            bpy.context.view_layer.update()
        return style, "xyz"[part_axis]

    def thumbnail_px(self):
        return self.s["thumbnail_px"] if not self.preview else self.s["preview_long_side_px"] // 2

    def show_only_thumb(self, pid):
        self.restore()
        for o in self.obj_of.values():
            o.hide_render = True
        t = self.thumb_of[pid]; t.hide_render = False
        self.coll_subject.objects.link(t)
        return t

    def render_thumbnail(self, pid):
        view_id = f"part-{slug(pid)}"
        t = self.show_only_thumb(pid)
        style, axis = self.thumbnail_pose(t)
        if style == "long":
            wide = self.s["thumbnail_long_aspect_px"]
            self.set_resolution(self.s["thumbnail_long_px"] if not self.preview else self.s["preview_long_side_px"], wide)
            d = Vector(self.s["thumbnail_long_direction"]).normalized()
        else:
            self.set_resolution(self.thumbnail_px(), [1, 1])
            d = Vector(self.s["thumbnail_direction"]).normalized()
        corners = [t.matrix_world @ Vector(c) for c in t.bound_box]
        mn, mx = aabb_of(corners); ctr = (mn + mx) / 2
        self.aim(ctr + d * max((mx - mn).length, 1e-3) * 4, ctr, Vector((0, 0, 1)))
        framed = self.fit(corners, "orthographic", self.s["thumbnail_fill"])
        self.place_floor([t], "part-thumbnail")
        path, secs = self.render_to(view_id, self.samples())
        end_view = f"part-{slug(pid)}-end" if style == "long" and self.s["thumbnail_end_view"] else None
        rec = self.view_record(view_id, path, secs, kind="part-thumbnail", part_id=pid, framed=framed, style=style,
                               long_axis=axis if style == "long" else None, aspect=self.thumb_style[pid][1], end_view=end_view)
        t.matrix_world = Matrix(self.scene.basis_to_z_up)
        self.restore(); self.verify_restored(view_id)
        return rec

    def render_part_end(self, pid):
        """A long part seen straight along its long axis (orthographic): the
        cross-section or end detail. Same object, same canonical geometry."""
        view_id = f"part-{slug(pid)}-end"
        t = self.show_only_thumb(pid)
        style, axis = self.thumbnail_pose(t)        # long axis now along X
        self.set_resolution(self.thumbnail_px(), [1, 1])
        corners = [t.matrix_world @ Vector(c) for c in t.bound_box]
        mn, mx = aabb_of(corners); ctr = (mn + mx) / 2
        self.aim(ctr + Vector((1.0, 0.0, 0.0)) * max((mx - mn).length, 1e-3) * 4, ctr, Vector((0, 0, 1)))
        framed = self.fit(corners, "orthographic", self.s["thumbnail_fill"])
        self.place_floor([t], "part-end")
        path, secs = self.render_to(view_id, self.samples())
        rec = self.view_record(view_id, path, secs, kind="part-end", part_id=pid, framed=framed, style=style, long_axis=axis,
                               aspect=self.thumb_style[pid][1], looking_along=f"+{axis} of the part, towards -{axis}")
        t.matrix_world = Matrix(self.scene.basis_to_z_up)
        self.restore(); self.verify_restored(view_id)
        return rec

    def render_overview(self):
        view_id = "overview"
        self.restore()
        framed = self.overview_camera()
        for o in self.obj_of.values():
            self.coll_subject.objects.link(o)
        self.place_floor(list(self.obj_of.values()), "overview")
        path, secs = self.render_to(view_id, self.samples())
        hs = self.hotspots(view_id, list(self.obj_of))
        self.write_hotspots(hs)
        rec = self.view_record(view_id, path, secs, kind="overview", visible=list(self.obj_of), framed=framed)
        self.restore(); self.verify_restored(view_id)
        return rec

    def render_exploded(self, plan):
        """The subassemblies drawn apart: every top-level group (a child assembly
        of the root with all its occurrences, or the parts directly under the
        root) moved as a rigid body by its offset from `exploded_view`, all in
        their looks with outlines when affordable. Illustration transforms only:
        nothing is hidden or reordered, and the installed poses are restored and
        verified afterwards like every other view."""
        view_id = "exploded"
        self.restore()
        for g in plan["groups"]:
            off = Vector(g["offset_mm"]) * 0.001
            for oid in g["occurrence_ids"]:
                o = self.obj_of[oid]
                o.location = o.location + off
        bpy.context.view_layer.update()
        for o in self.obj_of.values():
            self.coll_subject.objects.link(o)
        self.set_resolution(self.long_side(), self.s["aspect"])
        pts = [o.matrix_world @ Vector(c) for o in self.obj_of.values() for c in o.bound_box]
        mn, mx = aabb_of(pts); ctr = (mn + mx) / 2
        d = Vector(plan["direction"]).normalized() if plan.get("direction") else Vector(self.s["overview_direction"]).normalized()
        self.aim(ctr + d * max((mx - mn).length, 1e-3) * 4, ctr, Vector((0, 0, 1)))
        framed = self.fit(pts, "orthographic", plan["fill"])
        self.place_floor(list(self.obj_of.values()), "exploded")
        path, secs = self.render_to(view_id, self.samples())
        hs = self.hotspots(view_id, list(self.obj_of))
        hs["groups"] = {g["id"]: list(g["occurrence_ids"]) for g in plan["groups"]}
        hs["offsets_mm"] = plan["offsets_mm"]
        self.write_hotspots(hs)
        rec = self.view_record(view_id, path, secs, kind="exploded", visible=list(self.obj_of), framed=framed,
                               offsets_mm=plan["offsets_mm"], spread=plan["spread"],
                               groups=[{"id": g["id"], "offset_mm": g["offset_mm"], "source": g["source"], "occurrence_ids": list(g["occurrence_ids"])} for g in plan["groups"]],
                               direction=[round(v, 4) for v in d], direction_from_settings=plan.get("direction") is not None,
                               poses="exploded", exploded=True, extent_m=[round(v, 4) for v in (mx - mn)],
                               note="exploded illustration: the top-level groups moved apart as rigid bodies by the recorded offsets; "
                                    "not an assembly step, no order, fastener or tool access implied")
        self.restore(); self.verify_restored(view_id)
        return rec

    def facing_direction(self, default, extent):
        """The configured view direction, except that a flat group (one extent
        under a fifth of the next, like a panel with its handles) is viewed
        mostly along its thin axis from the side the default looks from, so the
        face shows instead of the edge. Looks only; nothing moves."""
        d = Vector(default)
        e = sorted((extent[0], extent[1], extent[2]))
        if e[0] < 0.2 * e[1]:
            i = min(range(3), key=lambda k: extent[k])
            sign = 1.0 if d[i] >= 0 else -1.0
            d[i] = sign * 2.5 * max(abs(d[k]) for k in range(3) if k != i)
        return d.normalized()

    def assembly_path(self, gid):
        trail = []; cur = gid
        while cur is not None and cur in self.scene.assemblies and len(trail) <= len(self.scene.assemblies):
            trail.append(cur); cur = self.scene.assemblies[cur].parent_id
        return list(reversed(trail))

    def group_members(self, gid):
        """Occurrence ids under the assembly (any depth), in scene order."""
        return [oid for oid, occ in self.scene.occurrences.items() if gid in occ.path]

    def render_group(self, gid):
        """One subassembly alone, every occurrence at its canonical pose, framed
        from `group_direction`: an inspection/parts view. Nothing is moved,
        exploded or hidden inside the group; no step or sequence is implied."""
        view_id = f"group-{slug(gid)}"
        self.restore()
        members = self.group_members(gid)
        if not members:
            raise SystemExit(f"--groups: assembly {gid!r} has no occurrences")
        for oid, o in self.obj_of.items():
            o.hide_render = oid not in members
        for oid in members:
            self.coll_subject.objects.link(self.obj_of[oid])
        self.set_resolution(self.long_side(), self.s["aspect"])
        pts = []
        for oid in members:
            pts += self.occurrence_corners(oid)
        mn, mx = aabb_of(pts); ctr = (mn + mx) / 2
        d = self.facing_direction(self.s["group_direction"], mx - mn)
        self.aim(ctr + d * max((mx - mn).length, 1e-3) * 4, ctr, Vector((0, 0, 1)))
        framed = self.fit(pts, "orthographic", self.s["group_fill"])
        self.place_floor([self.obj_of[oid] for oid in members], "group")
        path, secs = self.render_to(view_id, self.samples())
        hs = self.hotspots(view_id, members)
        self.write_hotspots(hs)
        asm = self.scene.assemblies[gid]
        parts = {}
        for oid in members:
            pid = self.scene.occurrences[oid].part_id
            parts[pid] = parts.get(pid, 0) + 1
        rec = self.view_record(view_id, path, secs, kind="group", group_id=gid, parent_id=asm.parent_id, assembly_path=self.assembly_path(gid),
                               depth=asm.depth, flexible=asm.flexible, visible=members, direction=[round(v, 4) for v in d],
                               occurrences=[{"id": oid, "part_id": self.scene.occurrences[oid].part_id, "parent_id": self.scene.occurrences[oid].parent_id} for oid in members],
                               parts=parts, poses="canonical", exploded=False, framed=framed,
                               extent_m=[round(v, 4) for v in (mx - mn)],
                               note="inspection view: occurrences at their CAD poses; not an assembly step; no sequence, fasteners or tool access implied")
        self.restore(); self.verify_restored(view_id)
        return rec

    def render_joint(self, spec):
        """A close-up of one project joint: the listed occurrences framed alone
        at their canonical poses, the rest of the context assembly subdued
        (flat grey, thin outline) or hidden, everything else hidden. An
        inspection view, not a step: nothing moves, nothing is invented."""
        view_id = spec["view_id"]
        self.restore()
        subject = list(spec["occurrence_ids"])
        ctx_ids = list(spec["context"]); style = spec["context_style"]
        context = [oid for oid in context_members(self.scene, ctx_ids) if oid not in subject]
        for oid, o in self.obj_of.items():
            if oid in subject:
                self.coll_subject.objects.link(o)
            elif oid in context and style == "faded":
                o.material_slots[0].material = self.context_mat; self.coll_context.objects.link(o)
            else:
                o.hide_render = True
        self.set_resolution(self.long_side(), self.s["aspect"])
        pts = []
        for oid in subject:
            pts += self.occurrence_corners(oid)
        mn, mx = aabb_of(pts); ctr = (mn + mx) / 2
        d = Vector(spec["direction"]).normalized() if spec.get("direction") else self.facing_direction(self.s["joint_direction"], mx - mn)
        # the eye sits outside the whole scene, so no context geometry is cut by the camera plane
        self.aim(ctr + d * max(self.scene_radius * 4, (mx - mn).length * 4, 1e-3), ctr, Vector((0, 0, 1)))
        framed = self.fit(pts, "orthographic", self.s["joint_fill"])
        visible = subject + (context if style == "faded" else [])
        self.place_floor([self.obj_of[oid] for oid in visible], "joint")
        path, secs = self.render_to(view_id, self.samples())
        hs = self.hotspots(view_id, visible)
        self.write_hotspots(hs)
        occ = self.scene.occurrences
        rec = self.view_record(view_id, path, secs, kind="joint", joint_id=spec["joint_id"], occurrence_ids=subject,
                               occurrences=[{"id": oid, "part_id": occ[oid].part_id, "parent_id": occ[oid].parent_id} for oid in subject],
                               context_ids=ctx_ids, context_assembly=ctx_ids[0] if len(ctx_ids) == 1 and ctx_ids[0] in self.scene.assemblies else None,
                               context_style=style, context_occurrences=context,
                               hidden=[oid for oid in self.obj_of if oid not in visible], visible=visible,
                               direction=[round(v, 4) for v in d], direction_from_settings=spec.get("direction") is not None,
                               poses="canonical", exploded=False, framed=framed, extent_m=[round(v, 4) for v in (mx - mn)],
                               note="inspection view, not a step: the joint's occurrences at their CAD poses with the rest of the context subdued; "
                                    "no fastener, sequence or tool access implied")
        self.restore(); self.verify_restored(view_id)
        return rec

    def render_step(self, st, result=False):
        step = st.step
        view_id = f"step-{st.index:02d}-{slug(step.id)}" + ("-result" if result else "")
        self.restore()
        framed = self.step_camera_for(step.view)
        for oid in st.hidden:
            self.obj_of[oid].hide_render = True
        for oid in st.before:
            o = self.obj_of[oid]; o.material_slots[0].material = self.ghost_mat; self.coll_context.objects.link(o)
        for oid in st.added:
            self.coll_subject.objects.link(self.obj_of[oid])
        approach = None
        ap = approach_pose(self.scene, st)
        if ap and not result:
            oid, start, end = ap
            o = self.obj_of[oid]
            o.matrix_world = to_blender(start, self.factor)
            bpy.context.view_layer.update()
            # arrow from the displaced part's leading face to just short of its seat
            d = (Vector(T.translation(end)) - Vector(T.translation(start))) * self.factor
            travel = d.length; d.normalize()
            cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
            mn, mx = aabb_of(cs); ctr = (mn + mx) / 2
            half = abs(d.dot(mx - mn)) / 2
            lead_start = ctr + d * half
            a = self.s["arrow"]
            p0 = lead_start + d * travel * a["start_gap_fraction"]
            p1 = lead_start + d * travel * (1 - a["tip_gap_fraction"])
            part_size = min(v for v in (mx - mn) if v > 1e-9)
            self.make_arrow(p0, p1, part_size)
            approach = {"occurrence_id": oid, "start_world_translation": T.translation(start), "end_world_translation": T.translation(end),
                        "arrow_from_m": list(p0), "arrow_to_m": list(p1), "validation": step.approach.validation}
        visible = st.before + st.added
        self.place_floor([self.obj_of[oid] for oid in visible], "step-result" if result else "step")
        path, secs = self.render_to(view_id, self.samples())
        hs = self.hotspots(view_id, visible)
        self.write_hotspots(hs)
        rec = self.view_record(view_id, path, secs, kind="step-result" if result else "step", step_id=step.id, step_index=st.index,
                               visible=visible, highlighted=st.added, subdued=st.before, hidden=st.hidden, approach=approach, framed=framed,
                               context_alpha=self.s["step_context_alpha"], deferred=st.deferred)
        self.restore(); self.verify_restored(view_id)
        return rec

    def write_hotspots(self, hs):
        d = self.out / "hotspots"; d.mkdir(parents=True, exist_ok=True)
        (d / f"{hs['view']}.json").write_text(json.dumps(hs, indent=1) + "\n")

    # ---------------------------------------------------------------- run

    def plan(self, groups=(), joints=(), exploded=None):
        plan = []
        for pid in self.scene.parts:
            plan.append((f"part-{slug(pid)}", lambda pid=pid: self.render_thumbnail(pid)))
            if self.thumb_style[pid][0] == "long" and self.s["thumbnail_end_view"]:
                plan.append((f"part-{slug(pid)}-end", lambda pid=pid: self.render_part_end(pid)))
        plan.append(("overview", self.render_overview))
        if exploded and exploded["enabled"]:
            plan.append(("exploded", lambda: self.render_exploded(exploded)))
        for gid in groups:
            plan.append((f"group-{slug(gid)}", lambda gid=gid: self.render_group(gid)))
        for jv in joints:
            plan.append((jv["view_id"], lambda jv=jv: self.render_joint(jv)))
        for st in self.states:
            plan.append((f"step-{st.index:02d}-{slug(st.step.id)}", lambda st=st: self.render_step(st)))
            if st.step.approach is not None:
                plan.append((f"step-{st.index:02d}-{slug(st.step.id)}-result", lambda st=st: self.render_step(st, result=True)))
        return plan

    def reuse_view(self, old, reuse):
        """Copy an earlier run's view (image, hotspots, record) after checking the
        image still hashes as that receipt recorded."""
        src = Path(reuse["dir"]) / old["file"]
        if not src.is_file() or receipts.sha256_file(src) != old["sha256"]:
            raise SystemExit(f"--reuse: {src} is missing or differs from its receipt; render it again")
        import shutil
        shutil.copyfile(src, self.out / old["file"])
        hs = Path(reuse["dir"]) / "hotspots" / f"{old['id']}.json"
        if hs.is_file():
            (self.out / "hotspots").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(hs, self.out / "hotspots" / hs.name)
        rec = dict(old)
        if rec.get("reused_from"):
            # already a copy: keep the original render's provenance, record this hop
            rec["reused_via"] = list(rec.get("reused_via", [])) + [reuse["receipt_path"]]
        else:
            rec.update({"reused_from": reuse["receipt_path"], "reused_settings_sha256": reuse["settings_sha256"],
                        "reused_generated_at_utc": reuse["generated_at_utc"], "reused_blender": reuse.get("blender")})
        return rec

    def run(self, only=None, groups=(), reuse=None, joints=(), exploded=None, instructions_changed=False):
        """Render the plan. `only` restricts rendering to those view ids; with
        `reuse`, every other planned view present in the earlier receipt is
        copied and views absent from it are rendered. Returns (views, missing)."""
        self.out.mkdir(parents=True, exist_ok=True)
        views = []
        old = {v["id"]: v for v in reuse["views"]} if reuse else {}
        missing = []
        self.stale = {}
        joint_specs = {jv["view_id"]: jv for jv in joints}
        step_states = {}
        for st in self.states:
            vid = f"step-{st.index:02d}-{slug(st.step.id)}"
            step_states[vid] = (st.added, st.before); step_states[vid + "-result"] = (st.added, st.before)
        budget = self.s["lines"]["preview_max_triangles" if self.preview else "max_triangles"]
        for view_id, fn in self.plan(groups, joints, exploded):
            wanted = not only or view_id in only
            if reuse is not None and view_id in old and not (only and view_id in only):
                reason = stale_reason(old[view_id], joint_specs, self.lines_enabled, budget, exploded, instructions_changed, step_states)
                if reason is None:
                    rec = self.reuse_view(old[view_id], reuse)
                    views.append(rec)
                    log(f"{view_id}: reused from {reuse['receipt_path']} ({rec['width']}x{rec['height']}, {rec['seconds']}s then)")
                    continue
                self.stale[view_id] = reason
                log(f"{view_id}: earlier view is stale ({reason}); rendering")
            if not wanted and reuse is None:
                missing.append(view_id)
                continue
            rec = fn()
            views.append(rec)
            log(f"{view_id}: {rec['width']}x{rec['height']} in {rec['seconds']}s" + ("" if rec.get("framed", True) else "  WARNING: content clipped"))
            if not rec.get("framed", True):
                self.checks["problems"].append(f"{view_id}: framed content does not fit the image")
        return views, missing


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    project_dir, meshes_path, out_dir = Path(argv[0]), Path(argv[1]), Path(argv[2])
    preview = False; only = None; engine = None; lines = True; cli_groups = []; reuse_dir = None; i = 3; instructions_changed = False
    while i < len(argv):
        if argv[i] == "--preview":
            preview = True; i += 1
        elif argv[i] == "--no-lines":
            lines = False; i += 1
        elif argv[i] == "--views":
            only = argv[i + 1].split(","); i += 2
        elif argv[i] == "--groups":
            cli_groups += [g for g in argv[i + 1].split(",") if g]; i += 2
        elif argv[i] == "--reuse":
            reuse_dir = Path(argv[i + 1]); i += 2
        elif argv[i] == "--engine":
            engine = argv[i + 1]; i += 2
        else:
            raise SystemExit(f"unknown argument {argv[i]}")
    try:
        project = load_project(project_dir)
    except ManifestError as e:
        print(e, file=sys.stderr)
        return 2
    meshes = receipts.read_json(meshes_path)
    meshes["_path"] = str(meshes_path.resolve())
    if meshes.get("kind") != "mechanical-docs-mesh-receipt":
        raise SystemExit(f"{meshes_path}: not a mesh receipt")
    # meshes depend on the scene and the asset files only; a changed inventory,
    # supplement or instruction file does not call for a new CAD stage
    stale = {k: v for k, v in project.geometry_input_hashes().items() if meshes["input_hashes"].get(k) != v}
    if stale:
        raise SystemExit(f"{meshes_path} was made from different geometry inputs ({sorted(stale)}); re-run the CAD stage")
    if not meshes.get("all_checks_passed"):
        raise SystemExit(f"{meshes_path}: the CAD stage reported problems; not rendering unchecked geometry")
    settings, settings_path = load_settings(project.dir)
    groups = []
    for g in list(settings["inspection_groups"]) + cli_groups:
        if g not in project.scene.assemblies:
            raise SystemExit(f"--groups/inspection_groups: {g!r} is not an assembly id in the scene")
        if g == project.scene.root_id:
            raise SystemExit(f"--groups/inspection_groups: {g!r} is the root; the overview already shows it")
        if g not in groups:
            groups.append(g)
    joints = resolve_joint_views(project.scene, settings["joint_views"])
    try:
        exploded = explode.resolve(project.scene, meshes, settings)
    except ValueError as e:
        raise SystemExit(str(e))
    reuse = None
    if reuse_dir is not None:
        rp = reuse_dir / "render-receipt.json"
        if not rp.is_file():
            raise SystemExit(f"--reuse: no render receipt at {rp}")
        old = receipts.read_json(rp)
        want_engine = engine or settings["engine"]
        reasons = []
        if old.get("kind") != "mechanical-docs-render-receipt":
            reasons.append("not a render receipt")
        # the inventory, the supplement and the build scope never change a pixel by
        # themselves (a changed step state is caught per view); the instructions may
        # differ too, which stales the overview and every step view but nothing else
        geometry = project.geometry_input_hashes()
        if {k: v for k, v in (old.get("input_hashes") or {}).items() if k in geometry} != geometry:
            reasons.append("different scene or asset hashes")
        ins_key = str(project.instructions.file.relative_to(project.dir)) if project.instructions is not None else "instructions.json"
        instructions_changed = (old.get("input_hashes") or {}).get(ins_key) != project.input_hashes().get(ins_key)
        if old.get("mesh_hashes") != {pid: rec["mesh"]["sha256"] for pid, rec in meshes["parts"].items()}:
            reasons.append("different meshes")
        if old.get("engine") != want_engine:
            reasons.append(f"engine {old.get('engine')} != {want_engine}")
        if bool(old.get("preview")) != preview:
            reasons.append("preview quality differs")
        if not old.get("all_checks_passed"):
            reasons.append("its checks did not all pass")
        if reasons:
            raise SystemExit(f"--reuse: cannot reuse {rp}: " + "; ".join(reasons))
        reuse = {"dir": str(reuse_dir), "receipt_path": str(rp), "views": old["views"], "settings_sha256": old.get("settings_sha256"),
                 "generated_at_utc": old.get("generated_at_utc"), "blender": old.get("blender")}
    t0 = time.time()
    r = Renderer(project, meshes, settings, out_dir, preview, engine, lines)
    views, missing = r.run(only, groups, reuse, joints, exploded, instructions_changed if reuse else False)
    reused = [v["id"] for v in views if v.get("reused_from")]
    receipt = {
        "kind": "mechanical-docs-render-receipt", "generated_at_utc": receipts.utc_now(),
        "blender": bpy.app.version_string, "python": sys.version.split()[0], "engine": r.engine, "denoiser": r.denoiser,
        "preview": preview, "samples": r.samples(), "long_side_px": r.long_side(), "floor_shadow_catcher": r.floor is not None,
        "lines": r.lines_enabled, "lines_max_triangles": settings["lines"]["preview_max_triangles" if preview else "max_triangles"],
        "settings_file": str(settings_path.relative_to(project.dir)) if settings_path else None,
        "settings_sha256": receipts.sha256_text(json.dumps(settings, sort_keys=True)),
        "project_dir": str(project.dir), "scene_id": project.scene.id, "scene_units": project.scene.units, "unit_factor_to_m": r.factor,
        "native_up_axis": project.scene.native_up_axis, "occurrences": len(project.scene.occurrences), "parts": len(project.scene.parts),
        "input_hashes": project.input_hashes(), "meshes_json_sha256": receipts.sha256_file(meshes_path),
        "mesh_hashes": {pid: rec["mesh"]["sha256"] for pid, rec in meshes["parts"].items()},
        "partial": bool(missing), "missing_views": missing, "inventory_only": project.instructions is None,
        "build_scope": None if project.build_scope is None else {"file": str(project.build_scope.file.relative_to(project.dir)), "sha256": project.build_scope.sha256, "phase": project.build_scope.phase,
                                                                   "deferred_steps": [st.step.id for st in r.states if st.deferred], "deferred_occurrences": project.build_scope.deferred_ids(project.scene)},
        "instructions_changed_since_reused": instructions_changed if reuse else None,
        "inspection_groups": groups, "joint_views": joints,
        "exploded_view": {"enabled": exploded["enabled"], "spread": exploded["spread"], "direction": exploded["direction"], "offsets_mm": exploded["offsets_mm"],
                          "groups": [{"id": g["id"], "offset_mm": g["offset_mm"], "source": g["source"], "occurrences": len(g["occurrence_ids"])} for g in exploded["groups"]]},
        "reused_from": reuse["receipt_path"] if reuse else None, "reused_views": reused,
        "rendered_views": [v["id"] for v in views if not v.get("reused_from")], "stale_reused_views": r.stale, "views": views,
        "checks": r.checks, "warnings": r.warnings,
        "all_checks_passed": not r.checks["problems"] and all(c["passed"] for c in r.checks["mesh_bounds_match"]) and all(c["passed"] for c in r.checks["restoration"]),
        "not_checked": ["image legibility (inspect the PNGs)", "insertion path or tool access", "physical assembly"],
        "seconds": round(time.time() - t0, 1),
    }
    receipts.write_json(out_dir / "render-receipt.json", receipt)
    log(f"wrote {out_dir / 'render-receipt.json'}: {len(views)} views ({len(reused)} reused) in {receipt['seconds']}s; "
        f"checks passed: {receipt['all_checks_passed']}" + (f"; PARTIAL, missing {missing}" if missing else ""))
    for w in r.warnings:
        log("WARNING:", w)
    return 0 if receipt["all_checks_passed"] else 1


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    sys.exit(main(argv))

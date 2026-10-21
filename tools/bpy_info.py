"""Report Blender's version and denoiser support (works under the bpy wheel or `blender -b --python`).

The Cycles denoiser enum reads as empty in background mode even when the build
has OpenImageDenoise, so this tries the assignment and reports the build option.
"""
import bpy

scn = bpy.context.scene
scn.render.engine = "CYCLES"
ok = True
try:
    scn.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception as e:  # noqa: BLE001
    ok = False
bo = bpy.app.build_options
print("blender", bpy.app.version_string, "python", bpy.app.version_string and __import__("sys").version.split()[0])
print("build_options.openimagedenoise", getattr(bo, "openimagedenoise", None), "cycles", getattr(bo, "cycles", None), "freestyle", getattr(bo, "freestyle", None))
print("set denoiser OPENIMAGEDENOISE:", "ok" if ok else "FAILED", "-> scene.cycles.denoiser =", repr(scn.cycles.denoiser) if ok else None)

# Environment plan

The supplied manifests are intentionally small:

| Role | Definition | Current use |
| --- | --- | --- |
| Base | `manifest.scm` | Python, PyYAML and Git for source/manifest work |
| CAD | `.guix/manifest-cad.scm` | FreeCAD plus Python/Git for the synthetic STEP fixture |

They use the session's Guix package set. No repository channel pin has yet been
selected; record the actual resolved versions in verification. Introduce deliberate
pins when establishing repeatable tool builds rather than claiming these manifests
alone fix all versions.

The source project `mouse-joysticks-mech` has a committed `pixi.toml` and lock:

- Default: Python, PyYAML, MkDocs and MkDocs Material.
- Rendering: Python 3.11 and Blender 4.5's official `bpy` wheel, including the
  denoising capability used for its existing images.
- PDF: Python/PyYAML, Pandoc and Typst.

Use that as the initial packaging reference when real rendering/publishing commands
are added. Keep a resolved Pixi lock with its manifest and verify actual commands
on the target platform. Do not copy tasks whose scripts have not been extracted.
FreeCAD may need a separate Guix role/process from the bpy Python environment;
exchange files/metadata through a documented interface rather than assuming their
Python ABIs or shared libraries can be mixed.

If using Guix Blender instead, qualify the renderer version and denoiser. The
existing project observed different image quality when denoising was unavailable.
The desired property is reproducible useful output, not merely a command with the
same executable name. No Blender/Pandoc/Typst environment was installed by this
handoff, and no existing environment or channel in another repository was changed.

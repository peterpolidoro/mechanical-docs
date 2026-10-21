"""mechanical-docs: visual inventories and assembly instructions from CAD exports.

Pure-Python modules (manifest, transforms, procedure, gltf, receipts, document,
html, typst, checks) run under any Python 3.11+. Two stage scripts run inside
host applications: `cad_mesh.py` under FreeCADCmd and `render.py` under
Blender. They only import the pure modules, so the package has no third-party
dependency of its own.
"""

__version__ = "0.1.0.dev0"

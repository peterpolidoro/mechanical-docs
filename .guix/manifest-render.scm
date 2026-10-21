(use-modules (guix profiles))
;; Render role: Blender (Guix build: EEVEE Next, Cycles CPU without OpenImageDenoise, Freestyle, glTF I/O).
(specifications->manifest '("python" "git" "blender"))

(use-modules (guix profiles))
;; Publish role: document generation, Typst PDF, Poppler (pdftotext/pdftoppm/pdfimages) and ImageMagick for output checks.
(specifications->manifest '("python" "python-pytest" "git" "typst" "poppler" "imagemagick"))

(use-modules (guix profiles))
;; Base role: manifest validation, document generation and the test suite.
(specifications->manifest '("python" "python-pyyaml" "python-pytest" "git"))

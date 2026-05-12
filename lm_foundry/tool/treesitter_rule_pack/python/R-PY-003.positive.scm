; R-PY-003 positive: specific except + log + re-raise
;
; Matches `except SpecificError as e:` with a body that is NOT just
; a single `pass`. The full canonical form (log.exception(e); raise)
; is too varied to fully match here; this captures the parameter
; shape and the rule pack reports both halves.
;
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

(except_clause
  value: (identifier) @positive.specific_exception
  alias: (identifier))

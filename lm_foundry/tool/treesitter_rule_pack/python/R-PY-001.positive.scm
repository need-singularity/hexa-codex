; R-PY-001 positive: None-sentinel default with body-local init
;
; Matches the idiomatic alternative — a default parameter of None,
; combined with body-local initialisation of the mutable container.
; The body-local init shape is too varied to fully match with one
; query; this captures the parameter half and the rule pack reports
; both halves as evidence.
;
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

(function_definition
  parameters: (parameters
    (default_parameter
      value: (none) @positive.none_sentinel)))

; R-PY-005 anti: dict-as-namespace literal
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: ruff FURB (partial)
; Citation: tier-e-findings.md Part 1 / Python row 5
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — heuristic + needs threshold tuning.
;
; Intent: match dictionary literals where every key is a string and
; the same dict is later indexed by literal string keys (config-like).
; This is a heuristic — the positive form is `@dataclass`. False
; positives expected; severity is `info` not `warn`.
;
; (dictionary
;   (pair
;     key: (string)
;     value: (_))+) @anti.dict_as_namespace

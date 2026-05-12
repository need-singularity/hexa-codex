; R-PY-007 anti: `if len(x) == 0` or `if x == None`
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: ruff E711 (None comparison), E712 (True/False);
;                    pylint C1801 (len-as-condition)
; Citation: tier-e-findings.md Part 1 / Python row 7
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — node name `comparison_operator` needs check.
;
; Intent: match `len(x) == 0` and `x == None` (or `x != None`).
; Idiomatic positives: `not xs` and `x is None`.
;
; (a) len(x) == 0
; (comparison_operator
;   (call
;     function: (identifier) @len_id
;     (#eq? @len_id "len"))
;   "=="
;   (integer) @zero
;   (#eq? @zero "0")) @anti.len_eq_zero
;
; (b) x == None
; (comparison_operator
;   (_)
;   ["==" "!="]
;   (none)) @anti.eq_none

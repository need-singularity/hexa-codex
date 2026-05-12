; R-PY-004 anti: manual file open/close without context manager
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: ruff SIM115
; Citation: tier-e-findings.md Part 1 / Python row 4
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — node names below need confirmation.
;
; Intent: match `f = open(...)` assignments where the file handle's
; `.close()` is called manually rather than via `with`. The full
; flow-sensitive match needs auxiliary post-processing; the query
; below captures the assignment shape and the runner cross-checks
; for a sibling `f.close()` call in the same scope.
;
; (assignment
;   left: (identifier) @file_var
;   right: (call
;     function: (identifier) @open_id
;     (#eq? @open_id "open"))) @anti.manual_file_open

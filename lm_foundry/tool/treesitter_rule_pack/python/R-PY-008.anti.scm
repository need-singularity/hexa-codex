; R-PY-008 anti: os.path family instead of pathlib
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: ruff PTH (full family)
; Citation: tier-e-findings.md Part 1 / Python row 9
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — node name `attribute` needs check.
;
; Intent: match calls to `os.path.{join,exists,isfile,isdir,...}`.
; Idiomatic positive is `pathlib.Path` and `/` operator.
;
; (call
;   function: (attribute
;     object: (attribute
;       object: (identifier) @os_id
;       attribute: (identifier) @path_id)
;     attribute: (identifier) @fn_id)
;   (#eq? @os_id "os")
;   (#eq? @path_id "path")
;   (#match? @fn_id "^(join|exists|isfile|isdir|basename|dirname|splitext|abspath|realpath|relpath|getsize|getmtime)$")) @anti.ospath_call

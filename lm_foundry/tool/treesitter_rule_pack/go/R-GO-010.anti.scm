; R-GO-010 anti: init-required struct (zero value is broken)
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: (manual / design review)
; Citation: tier-e-findings.md Part 1 / Go row 7
; Grammar: tree-sitter-go
; Status: UNVERIFIED — heuristic; severity is `info`.
;
; Intent: match a struct whose surrounding package contains a
; method `(*S).Init()` and where all subsequent uses appear to call
; it. Zero-value-usable types (e.g. `bytes.Buffer`) are idiomatic Go.
;
; (method_declaration
;   receiver: (parameter_list
;     (parameter_declaration
;       type: (pointer_type
;         (type_identifier) @recv_t)))
;   name: (field_identifier) @method_name
;   (#eq? @method_name "Init")) @anti.init_method

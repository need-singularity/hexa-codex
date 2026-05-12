; R-GO-006 anti: `interface{}` parameter (pre-1.18 style)
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: predeclared
; Citation: tier-e-findings.md Part 1 / Go row 8
; Grammar: tree-sitter-go
; Status: UNVERIFIED — node `empty_interface_type` may not exist;
;         tree-sitter-go may parse `interface{}` as an empty
;         `interface_type` with no method specs.
;
; Intent: match parameter or return type that is `interface{}` —
; modern Go uses `any`.
;
; (parameter_declaration
;   type: (interface_type
;     !method_spec_list)) @anti.empty_interface

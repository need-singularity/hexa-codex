; R-GO-009 anti: accept concrete type, return interface
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: (manual) — gocloudstudio idiomatic-go
; Citation: tier-e-findings.md Part 1 / Go row 10
; Grammar: tree-sitter-go
; Status: UNVERIFIED — needs type-of-type analysis at runner level.
;
; Intent: function declared to accept a pointer/concrete type and
; return an interface type. Go's "Postel's law for interfaces"
; reverses this: accept interfaces, return concrete types.
;
; v1 query captures only the function-decl shape; runner resolves
; whether the return type is an interface via type registry.
;
; (function_declaration
;   parameters: (parameter_list)
;   result: (type_identifier) @ret_t) @anti.candidate_iface_return

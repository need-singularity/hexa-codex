; R-GO-008 anti: preemptive `<Name>Service` interface declared up-front
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: interfacebloat (partial)
; Citation: tier-e-findings.md Part 1 / Go row 2
; Grammar: tree-sitter-go
; Status: UNVERIFIED — heuristic; severity is `info`.
;
; Intent: match an interface declaration named `*Service` co-located
; with a struct declaration named `*ServiceImpl` (Java-port smell).
; Idiomatic Go declares concrete first; the consumer declares the
; narrow interface it needs.
;
; (type_declaration
;   (type_spec
;     name: (type_identifier) @iface_name
;     type: (interface_type))
;   (#match? @iface_name "Service$")) @anti.service_interface

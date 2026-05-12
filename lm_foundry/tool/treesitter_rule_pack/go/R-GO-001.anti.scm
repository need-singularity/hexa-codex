; R-GO-001 anti: I-prefixed interface name (Java-style)
;
; Matches `type IReader interface { ... }` — the Go convention is to
; use unprefixed names; the consumer of the interface picks the name.
;
; Linter equivalent: revive var-naming; stylecheck ST1003
; Citation: tier-e-findings.md Part 1 / Go row 1
; Grammar: tree-sitter-go
; Status: UNVERIFIED — node names need confirmation against
;         tree-sitter-go node-types.json in v0.1.3 G-BASE pass.

(type_declaration
  (type_spec
    name: (type_identifier) @iface_name
    type: (interface_type))
  (#match? @iface_name "^I[A-Z]")) @anti.i_prefixed_interface

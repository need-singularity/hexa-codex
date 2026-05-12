; R-GO-001 positive: unprefixed interface name
;
; Matches `type Reader interface { ... }` — a type_spec for an
; interface whose name does not start with `I[A-Z]`.
;
; Grammar: tree-sitter-go
; Status: UNVERIFIED.

(type_declaration
  (type_spec
    name: (type_identifier) @iface_name
    type: (interface_type))
  (#not-match? @iface_name "^I[A-Z]")) @positive.plain_interface

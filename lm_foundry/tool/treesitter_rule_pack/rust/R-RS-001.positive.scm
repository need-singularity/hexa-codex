; R-RS-001 positive: generic struct parameter `<H: Trait>`
;
; Matches a struct declaration that takes a generic parameter with a
; trait bound — the idiomatic alternative to a `Box<dyn Trait>` field.
;
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

(struct_item
  type_parameters: (type_parameters
    (constrained_type_parameter
      bounds: (trait_bounds)))) @positive.generic_struct

; R-RS-001 anti: gratuitous Box<dyn Trait> for struct fields
;
; Matches struct field types of shape `Box<dyn Trait>`. In many cases
; this should be a generic parameter `<T: Trait>` instead — dynamic
; dispatch is rarely needed for a struct's own handler.
;
; Linter equivalent: clippy boxed_local (partial); clippy borrowed_box
; Citation: tier-e-findings.md Part 1 / Rust row 2
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — node names `generic_type` and `dynamic_type` need
;         confirmation against tree-sitter-rust node-types.json.

(generic_type
  type: (type_identifier) @box_id
  type_arguments: (type_arguments
    (dynamic_type) @dyn_arg)
  (#eq? @box_id "Box")) @anti.box_dyn_trait

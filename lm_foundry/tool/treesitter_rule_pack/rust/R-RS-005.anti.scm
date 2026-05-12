; R-RS-005 anti: manual `impl Default` that could be derived
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: clippy derivable_impls
; Citation: tier-e-findings.md Part 1 / Rust row 8
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match `impl Default for S { fn default() -> Self { S { ... } } }`
; where every field is initialised with its own type's Default value
; (literally `0`, `String::new()`, `Vec::new()`, etc.). Idiomatic
; alternative is `#[derive(Default)]`.
;
; (impl_item
;   trait: (type_identifier) @trait_name
;   (#eq? @trait_name "Default")
;   body: (declaration_list
;     (function_item
;       name: (identifier) @fn_name
;       (#eq? @fn_name "default")))) @anti.manual_default_impl

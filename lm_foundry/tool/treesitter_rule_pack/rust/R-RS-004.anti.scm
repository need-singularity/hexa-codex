; R-RS-004 anti: Java-style getter `pub fn get_x(&self) -> &T`
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: clippy wrong_self_convention; Rust API guidelines C-GETTER
; Citation: tier-e-findings.md Part 1 / Rust row 3
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match `pub fn get_<name>(&self) -> ...` inside impl blocks.
; Canonical Rust naming is `fn <name>(&self)` (no `get_` prefix).
;
; (function_item
;   (visibility_modifier)
;   name: (identifier) @fn_name
;   (#match? @fn_name "^get_")
;   parameters: (parameters
;     (self_parameter))) @anti.java_getter

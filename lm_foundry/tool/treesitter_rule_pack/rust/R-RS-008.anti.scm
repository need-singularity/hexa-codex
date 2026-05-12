; R-RS-008 anti: `.clone()` used to defeat the borrow checker
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: clippy redundant_clone
; Citation: tier-e-findings.md Part 1 / Rust row 7
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — heuristic; severity is `info`.
;
; Intent: match `.clone()` calls. Distinguishing legitimate clones
; from borrow-checker-defeating ones needs runner-level data-flow
; (the matched value used both before AND after the clone). v1
; reports raw count; future runner narrows.
;
; (call_expression
;   function: (field_expression
;     field: (field_identifier) @method
;     (#eq? @method "clone"))) @anti.clone_call

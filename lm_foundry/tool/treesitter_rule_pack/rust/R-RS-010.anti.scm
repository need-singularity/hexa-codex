; R-RS-010 anti: factory trait abstraction `trait FooFactory`
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: (manual AST heuristic on `*Factory` names)
; Citation: tier-e-findings.md Part 1 / Rust row 4
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — heuristic; severity is `info`.
;
; Intent: match `trait <Name>Factory` declarations. Java-port smell;
; idiomatic Rust prefers `impl <Foo> { pub fn new(...) -> Self }`.
;
; (trait_item
;   name: (type_identifier) @trait_name
;   (#match? @trait_name "Factory$")) @anti.factory_trait

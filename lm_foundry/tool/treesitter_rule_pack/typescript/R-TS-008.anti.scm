; R-TS-008 anti: class where a module of functions would suffice
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: (manual) — TS handbook "do's and don'ts"
; Citation: tier-e-findings.md Part 1 / TS row 6
; Grammar: tree-sitter-typescript (TS dialect)
; Status: UNVERIFIED — heuristic; severity is `info`.
;
; Intent: match a class declaration whose body contains no state
; (no field declarations, no `this` references) — pure-method bag.
; Idiomatic alternative is to export functions from the module.
;
; (class_declaration
;   body: (class_body
;     (method_definition)+)) @anti.stateless_class

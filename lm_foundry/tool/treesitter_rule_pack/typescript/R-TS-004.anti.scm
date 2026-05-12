; R-TS-004 anti: `Function` or `Object` ambient type used as annotation
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: @typescript-eslint/ban-types
; Citation: tier-e-findings.md Part 1 / TS row 5
; Grammar: tree-sitter-typescript (TS dialect)
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match parameter or property whose type is the bare
; identifier `Function` or `Object`. Idiomatic alternative is a
; precise signature or `Record<string, unknown>` / object literal type.
;
; (type_annotation
;   (type_identifier) @ty
;   (#match? @ty "^(Function|Object)$")) @anti.banned_ambient_type

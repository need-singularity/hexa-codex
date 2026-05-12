; R-TS-010 anti: untagged result union `string | { error: string }`
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: (manual; biome lint discriminated-union partial)
; Citation: tier-e-findings.md Part 1 / TS row 3
; Grammar: tree-sitter-typescript (TS dialect)
; Status: UNVERIFIED — heuristic; severity is `info`.
;
; Intent: match a type alias whose value is a union of mixed-shape
; arms (e.g. a primitive AND an object) with no discriminant field.
; Idiomatic alternative is a discriminated `{ ok: true; ... } | { ok: false; ... }` union.
;
; (type_alias_declaration
;   value: (union_type
;     (predefined_type)
;     (object_type))) @anti.untagged_union

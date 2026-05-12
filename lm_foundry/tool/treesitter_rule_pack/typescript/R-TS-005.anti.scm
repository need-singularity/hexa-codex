; R-TS-005 anti: `// @ts-ignore` blanket comment
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: @typescript-eslint/ban-ts-comment
; Citation: tier-e-findings.md Part 1 / TS row 8
; Grammar: tree-sitter-typescript (TS dialect)
; Status: UNVERIFIED — tree-sitter usually keeps comments as `comment`
;         nodes. Text matching via predicate.
;
; Intent: match `// @ts-ignore` comments — should use
; `// @ts-expect-error: <reason>` instead.
;
; (comment) @c
; (#match? @c "^//\\s*@ts-ignore") @anti.ts_ignore

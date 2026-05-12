; R-TS-003 anti: `as X` cast instead of type narrowing
;
; Matches `<expr> as <Type>` assertions. Some legitimate uses
; exist (`as const`, `as unknown as T` for forced bridges); the
; runner exempts these by checking the asserted type's text.
;
; Linter equivalent: @typescript-eslint/consistent-type-assertions
; Citation: tier-e-findings.md Part 1 / TS row 4
; Grammar: tree-sitter-typescript (TS dialect)
; Status: UNVERIFIED — `as_expression` node identity needs check.

(as_expression
  type: (type_identifier) @target_t
  (#not-eq? @target_t "const")) @anti.as_cast

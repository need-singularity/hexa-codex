; R-TS-007 anti: floating promise (call to async fn with no await/then/void)
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: @typescript-eslint/no-floating-promises
; Citation: tier-e-findings.md Part 1 / TS row 7
; Grammar: tree-sitter-typescript (TS dialect)
; Status: UNVERIFIED — full detection requires type info; v1 uses
;         call-site heuristic and the runner narrows.
;
; Intent: match expression-statements that are direct call_expressions
; without await/void/return prefix. The runner cross-checks with a
; symbol table for async function returns.
;
; (expression_statement
;   (call_expression)) @anti.bare_call_stmt

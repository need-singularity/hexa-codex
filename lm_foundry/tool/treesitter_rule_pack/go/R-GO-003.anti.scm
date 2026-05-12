; R-GO-003 anti: bare `panic("...")` used as control flow
;
; Matches `panic(...)` call expressions in regular code. Some
; legitimate panics exist (init-time invariants, unreachable
; branches) — the runner exempts `init()` functions and `main()`.
;
; Linter equivalent: revive panic
; Citation: tier-e-findings.md Part 1 / Go row 4
; Grammar: tree-sitter-go
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

(call_expression
  function: (identifier) @fn_name
  (#eq? @fn_name "panic")) @anti.bare_panic

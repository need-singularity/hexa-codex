; R-RS-003 anti: `let _ = expr` ignoring a Result
;
; Matches `let _ = <call>;` where the call's return type is (likely)
; a Result. The runner narrows this with type-info post-processing
; or, in static mode, matches by call-name heuristic
; (writeln!, write!, send, …) — see clippy let_underscore_must_use
; for the canonical set.
;
; Linter equivalent: clippy let_underscore_must_use
; Citation: tier-e-findings.md Part 1 / Rust row 5
; Grammar: tree-sitter-rust
; Status: UNVERIFIED — node name `underscore_pattern` (or `_pattern`)
;         needs confirmation in v0.1.3.

(let_declaration
  pattern: (_) @underscore_pat
  (#eq? @underscore_pat "_")
  value: (_)) @anti.let_underscore_ignores_result

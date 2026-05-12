; R-C-006 anti: macro-as-function with unparenthesised args
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: clang-tidy bugprone-macro-parentheses
; Citation: tier-e-findings.md Part 1 / C row 6
; Grammar: tree-sitter-c
; Status: UNVERIFIED — preprocessor node names need confirmation.
;
; Intent: match `#define NAME(args) body` where `body` uses one of the
; macro parameters without surrounding parentheses. Idiomatic
; alternative is to either use a `static inline` function or fully
; parenthesise: `#define SQ(x) ((x) * (x))`.
;
; (preproc_function_def
;   name: (identifier)
;   parameters: (preproc_params)
;   value: (preproc_arg) @body) @anti.macro_function_candidate

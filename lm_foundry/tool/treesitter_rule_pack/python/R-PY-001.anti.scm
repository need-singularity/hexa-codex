; R-PY-001 anti: mutable default argument
;
; Matches function definitions whose default parameter value is a
; mutable literal (list, dict, set). These are evaluated once at
; definition time and shared across calls — a classic Python gotcha.
;
; Linter equivalent: ruff B006
; Citation: tier-e-findings.md Part 1 / Python row 1
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — node names below need confirmation against
;         tree-sitter-python node-types.json in v0.1.3 G-BASE pass.

(function_definition
  parameters: (parameters
    (default_parameter
      value: [
        (list)
        (dictionary)
        (set)
      ] @anti.mutable_default)))

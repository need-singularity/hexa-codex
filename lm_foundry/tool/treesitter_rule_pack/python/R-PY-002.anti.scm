; R-PY-002 anti: for i in range(len(x))
;
; Matches a for-loop whose iterable is range() of len() — should
; use enumerate() instead when both the index and value are used.
;
; Linter equivalent: ruff PLR1736; pylint consider-using-enumerate
; Citation: tier-e-findings.md Part 1 / Python row 2
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

(for_statement
  right: (call
    function: (identifier) @range_id
    arguments: (argument_list
      (call
        function: (identifier) @len_id)))
  (#eq? @range_id "range")
  (#eq? @len_id "len")) @anti.range_len_loop

; R-PY-002 positive: for i, x in enumerate(xs)
;
; Matches the idiomatic enumerate() form — for-loop whose iterable
; is a call to enumerate().
;
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

(for_statement
  right: (call
    function: (identifier) @enumerate_id
    (#eq? @enumerate_id "enumerate"))) @positive.enumerate_loop

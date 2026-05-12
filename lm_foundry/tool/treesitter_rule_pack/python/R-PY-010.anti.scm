; R-PY-010 anti: Java-style getter method
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: (manual) — no canonical Python lint
; Citation: tier-e-findings.md Part 1 / Python row 8
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — heuristic; severity is `info`.
;
; Intent: match a method named `get_<name>` whose body is a single
; `return self._<name>` (or `return self.<name>`). The idiomatic
; Python form is direct attribute access, optionally via @property.
;
; (function_definition
;   name: (identifier) @method_name
;   (#match? @method_name "^get_")
;   body: (block
;     (return_statement
;       (attribute
;         object: (identifier) @self_id
;         (#eq? @self_id "self"))))) @anti.java_getter

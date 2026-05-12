; R-GO-005 anti: getter named `GetFoo` (Java-style)
;
; STUB - implementation pending v0.1.3 G-BASE
;
; Linter equivalent: revive getter-return; golint
; Citation: tier-e-findings.md Part 1 / Go row 6
; Grammar: tree-sitter-go
; Status: UNVERIFIED — node names need confirmation.
;
; Intent: match method declarations whose name starts with `Get`
; and whose body is a single `return s.<field>`. Go convention is
; to name the method after the field (no `Get` prefix).
;
; (method_declaration
;   name: (field_identifier) @method_name
;   (#match? @method_name "^Get[A-Z]")
;   body: (block
;     (return_statement
;       (expression_list
;         (selector_expression))))) @anti.get_prefixed_getter

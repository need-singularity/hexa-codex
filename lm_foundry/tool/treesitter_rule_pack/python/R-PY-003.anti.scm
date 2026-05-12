; R-PY-003 anti: bare or overly-broad except (with pass body)
;
; Matches `except:` (bare) and `except Exception: pass` / `except: pass`
; — both swallow exceptions silently, defeat debugging, and mask bugs.
;
; Linter equivalent: ruff E722 (bare except); ruff BLE001 (broad except);
;                    ruff S110 (try/except/pass)
; Citation: tier-e-findings.md Part 1 / Python row 3
; Grammar: tree-sitter-python 0.20+
; Status: UNVERIFIED — node names need confirmation in v0.1.3.

; (a) bare `except:`
(except_clause
  !value) @anti.bare_except

; (b) `except: pass` or `except Exception: pass`
(except_clause
  body: (block (pass_statement))) @anti.silent_except

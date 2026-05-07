# hexa-codex — runnable surface fan-out + future spec PDF rebuild.
#
# Mirrors hexa-sscb/build/Makefile. At v1.0.0 there is no canonical PDF
# to rebuild (the seed is markdown-only); the `pdf` target is a placeholder
# that builds a single-PDF export of any verb spec when invoked.
#
# Usage:
#   make -C build verify       # run all 5 verifiers
#   make -C build verify-json  # JSON output for CI
#   make -C build test         # pytest tests/ -m auto
#   make -C build test-hexa    # pytest tests/ -m hexa (requires hexa-lang)
#   make -C build selftest     # 17-verb spec presence (.hexa)
#   make -C build install-test # hx install hexa-codex --entry cli/hexa-codex.hexa
#   make -C build pdf VERB=alignment  # one-off PDF (alignment/ai-alignment.md)
#   make -C build ci           # verify + test (no hexa-lang required)
#   make -C build everything   # ci + test-hexa + selftest

ROOT     := ..
PYTHON   ?= python3
HEXA     ?= /Users/ghost/.hx/bin/hexa
HX       ?= /Users/ghost/.hx/bin/hx
PANDOC   := pandoc
OUT      := out

PANDOC_FLAGS := \
  --pdf-engine=xelatex \
  --variable=geometry:a4paper,margin=25mm \
  --variable=fontsize:11pt \
  --variable=colorlinks:true \
  --variable=linkcolor:black \
  --variable=urlcolor:blue \
  --syntax-highlighting=tango \
  --toc \
  --toc-depth=2

.PHONY: all verify verify-json test test-hexa selftest install-test pdf clean check ci everything help

all: ci

# ── runnable surface fan-out ─────────────────────────────────────────

verify:
	@cd $(ROOT) && $(PYTHON) verify/cli.py all

verify-json:
	@cd $(ROOT) && $(PYTHON) verify/cli.py all --json

test:
	@cd $(ROOT) && $(PYTHON) -m pytest tests/ -m auto -v

test-hexa:
	@cd $(ROOT) && $(PYTHON) -m pytest tests/ -m hexa -v

selftest:
	@cd $(ROOT) && HEXA_CODEX_ROOT=$$PWD $(HEXA) run cli/hexa-codex.hexa selftest

install-test:
	@$(HX) install hexa-codex --entry cli/hexa-codex.hexa

# ── PDF (per-verb, on-demand) ────────────────────────────────────────

VERB ?= alignment

# Resolve the spec path for VERB via verify/verb_query.py (so this Makefile
# has zero hard-coded verb→path mapping).
pdf: | $(OUT)
	@cd $(ROOT) && \
	  PATH=$$( $(PYTHON) verify/verb_query.py --json $(VERB) | $(PYTHON) -c "import json,sys; print(json.load(sys.stdin)[0]['path'])" ); \
	  if [ -z "$$PATH" ]; then echo "VERB=$(VERB) not found"; exit 2; fi; \
	  echo "  pandoc → build/$(OUT)/$(VERB).pdf  (source: $$PATH)"; \
	  $(PANDOC) $(PANDOC_FLAGS) \
	    --metadata=title:"hexa-codex — $(VERB)" \
	    --metadata=date:"$$( date +%Y-%m-%d )" \
	    -o build/$(OUT)/$(VERB).pdf $$PATH

build/$(OUT):
	@mkdir -p $(OUT)

$(OUT):
	@mkdir -p $(OUT)

clean:
	rm -rf $(OUT)

check:
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "MISSING: $(PYTHON)"; exit 1; }
	@command -v $(HEXA)   >/dev/null 2>&1 || { echo "OPTIONAL MISSING: $(HEXA)  (hx install hexa-lang)"; }
	@command -v $(PANDOC) >/dev/null 2>&1 || { echo "OPTIONAL MISSING: $(PANDOC)  (brew install pandoc)"; }
	@$(PYTHON) --version
	@echo "OK: required toolchain ready (Python)"

# ── CI surface ───────────────────────────────────────────────────────

ci: verify test
	@echo
	@echo "  ✓ ci surface PASSED"
	@echo "    · verify   — 5 verifiers (n6/inventory/group/release/falsifiers)"
	@echo "    · test     — pytest tests/ -m auto"

everything: ci selftest test-hexa
	@echo "  ✓ everything PASSED (ci + selftest + hexa-lang tests)"

help:
	@echo "hexa-codex/build/Makefile targets:"
	@echo "  verify        run all 5 verifiers"
	@echo "  verify-json   JSON output for CI"
	@echo "  test          pytest -m auto"
	@echo "  test-hexa     pytest -m hexa (requires hexa-lang)"
	@echo "  selftest      cli/hexa-codex.hexa selftest"
	@echo "  install-test  hx install hexa-codex (with --entry workaround)"
	@echo "  pdf VERB=...  build a per-verb PDF"
	@echo "  ci            verify + test (default)"
	@echo "  everything    ci + selftest + hexa tests"
	@echo "  check         toolchain probe"
	@echo "  clean         remove build artifacts"

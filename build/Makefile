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
# HEXA points at the real local interpreter to bypass the ~/.hx/bin/hexa
# wrapper that unconditionally routes `run` / `batch` to `hexa-r ubu-1`.
# RESOURCE_LOCAL_HEXA=1 is also exported so any nested `hexa run` chain
# stays local even when invoked through the wrapper.
HEXA     ?= /Users/ghost/.hx/packages/hexa/hexa.real
HX       ?= /Users/ghost/.hx/bin/hx
PANDOC   := pandoc
OUT      := out
HEXA_LOCAL_ENV := RESOURCE_LOCAL_HEXA=1 HEXA_CODEX_ROOT=$$PWD

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

.PHONY: all verify verify-json verify-hexa verify-saturation test test-hexa test-hexa-all selftest install-test pdf clean check ci everything help

all: ci

# ── runnable surface fan-out ─────────────────────────────────────────

# Legacy Python verify (kept for the spec/inventory/group/release
# checks; the .hexa-native runnable surface is the primary path now).
verify:
	@cd $(ROOT) && $(PYTHON) verify/cli.py all

verify-json:
	@cd $(ROOT) && $(PYTHON) verify/cli.py all --json

# .hexa-native verify all — runs the saturation_check aggregator which
# re-runs the 6 closure components and emits the sat-1 marker.
verify-hexa: verify-saturation

verify-saturation:
	@cd $(ROOT) && $(HEXA_LOCAL_ENV) $(HEXA) run verify/saturation_check.hexa

test:
	@cd $(ROOT) && $(PYTHON) -m pytest tests/ -m auto -v

test-hexa:
	@cd $(ROOT) && $(PYTHON) -m pytest tests/ -m hexa -v

# Full .hexa regression — 24 wrappers via tests/test_all.hexa.
test-hexa-all:
	@cd $(ROOT) && $(HEXA_LOCAL_ENV) $(HEXA) run tests/test_all.hexa

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
	@echo "    · verify   — Python verifiers (n6/inventory/group/release/falsifiers)"
	@echo "    · test     — pytest tests/ -m auto"

# sat-1 surface — .hexa-native primary path. Single command that re-runs
# the 6 closure components and exits 0 iff the recipe §7.2 sat-1 gate
# passes.
sat1: verify-saturation
	@echo
	@echo "  ✓ sat-1 closure verified"
	@echo "    · saturation_check  — falsifier_check + lint + cross-pillar +"
	@echo "                          lattice_arithmetic + lattice_check +"
	@echo "                          cross_doc_audit  →  sat-1 PASS"

everything: ci selftest test-hexa-all sat1
	@echo "  ✓ everything PASSED (ci + selftest + 24 .hexa tests + sat-1)"

help:
	@echo "hexa-codex/build/Makefile targets:"
	@echo "  verify         Python legacy verifiers"
	@echo "  verify-json    JSON output for CI"
	@echo "  verify-hexa    .hexa-native verify (alias for verify-saturation)"
	@echo "  verify-saturation  one-shot sat-1 marker (recipe §7.2 gate)"
	@echo "  test           pytest -m auto (83 cases)"
	@echo "  test-hexa      pytest -m hexa (requires hexa-lang)"
	@echo "  test-hexa-all  full 24-wrapper regression (tests/test_all.hexa)"
	@echo "  selftest       cli/hexa-codex.hexa selftest"
	@echo "  install-test   hx install hexa-codex (with --entry workaround)"
	@echo "  pdf VERB=...   build a per-verb PDF"
	@echo "  ci             Python verify + test (legacy CI)"
	@echo "  sat1           .hexa-native sat-1 closure verdict"
	@echo "  everything     ci + selftest + .hexa tests + sat-1"
	@echo "  check          toolchain probe"
	@echo "  clean          remove build artifacts"

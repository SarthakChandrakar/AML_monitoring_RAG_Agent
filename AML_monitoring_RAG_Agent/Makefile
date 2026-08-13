.PHONY: setup build-kb test test-risk test-compliance eval-smoke check-claims help

PYTHON = python

help:
	@echo "AML RAG Agent Makefile Targets:"
	@echo "  setup         : Install dependencies"
	@echo "  build-kb      : Build two-store kb_store index"
	@echo "  test          : Run all pytest unit tests"
	@echo "  test-risk     : Test pure risk engine"
	@echo "  test-compliance: Test compliance realism layer"
	@echo "  eval-smoke    : Run 5-item evaluation harness smoke test"
	@echo "  check-claims  : Run CI documentation claim check"

setup:
	$(PYTHON) -m pip install -r requirements.txt

build-kb:
	$(PYTHON) build_two_stores.py

test:
	$(PYTHON) -m pytest tests/

test-risk:
	$(PYTHON) -m pytest tests/test_risk_engine_pure.py

test-compliance:
	$(PYTHON) -m pytest tests/test_compliance_realism.py

eval-smoke:
	$(PYTHON) eval/faithfulness/runner.py

check-claims:
	$(PYTHON) scripts/check_claims.py

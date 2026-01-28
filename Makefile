VENV?=.venv
PYTHON=$(VENV)/bin/python
PYTHONPATH?=src
SWIFT_PACKAGE=swift/SystemPolicyAgent
AGENT_BIN=bin/system-policy-agent

.PHONY: setup build build-agent run-agent run-api test clean

setup:
	python3 -m venv $(VENV)

build-agent:
	swift build -c release --package-path $(SWIFT_PACKAGE)
	mkdir -p bin
	cp $(SWIFT_PACKAGE)/.build/release/SystemPolicyAgent $(AGENT_BIN)

build: build-agent
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m compileall src

run-agent: build-agent
	$(AGENT_BIN) $(ARGS)

run-api:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m api.main

test: build-agent
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -p 'test_*.py'

clean:
	rm -rf $(VENV) dist/ build/ __pycache__/ .pytest_cache/ bin/ $(SWIFT_PACKAGE)/.build
	rm -f data/profiles/*.mobileconfig data/policy_state.json

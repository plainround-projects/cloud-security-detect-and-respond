# make validate | lint | test | check | demo-drill   work offline, with no account and no credentials (make help lists all)
# make up | run | attack | respond | measure | down   need two sandbox accounts and credentials (see docs/RUNBOOK.md)
PYTHON ?= $(shell command -v python3.13 || command -v python3.12 || command -v python3)
TF ?= terraform
VENV := .venv
PY := $(VENV)/bin/python
STAMP := $(VENV)/.installed
ENVS := security workload
BUILD := build
# Placeholder values only, so the provider can start; plan_only makes it skip every call to AWS.
OFFLINE := env -u AWS_PROFILE AWS_ACCESS_KEY_ID=plan-only AWS_SECRET_ACCESS_KEY=plan-only AWS_EC2_METADATA_DISABLED=true
DR := $(PY) -m detect_respond
REHEARSAL := fixtures/drill

.PHONY: help install fmt lint test test-policy test-e2e audit plan check validate fixtures demo-drill review \
        up run attack respond measure down clean

help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | sort

$(STAMP): requirements-dev.lock pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -q --require-hashes -r requirements-dev.lock
	$(VENV)/bin/pip install -q --no-deps -e .
	touch $@

install: $(STAMP) ## create .venv from the lock file

fmt: $(STAMP) ## apply ruff, terraform fmt and opa fmt
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .
	$(TF) fmt -recursive infra
	opa fmt -w policy

lint: $(STAMP) ## ruff, mypy, import rules, terraform fmt, tflint, checkov, opa check, shellcheck
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .
	$(VENV)/bin/mypy
	$(VENV)/bin/lint-imports
	$(TF) fmt -check -recursive infra
	tflint --init
	tflint --recursive --config $(CURDIR)/.tflint.hcl
	checkov -d infra --framework terraform --quiet --compact
	opa fmt --list --fail policy
	opa check --strict policy
	shellcheck scripts/*.sh

test: $(STAMP) test-policy ## unit tests with coverage, and the policy tests
	$(PY) -m pytest tests/unit --cov --cov-report=term
	$(PY) -m coverage report --include='src/*/domain/*,src/*/application/*' --fail-under=95

test-policy: ## opa unit tests: a deny and an allow case for every rule
	opa test policy

# Needs terraform. Runs the whole offline pipeline through make.
test-e2e: $(STAMP) ## the plan-and-check pipeline through make, as a reader runs it
	$(PY) -m pytest tests/e2e -m e2e

audit: $(STAMP) ## check the locked dependencies for known vulnerabilities
	$(VENV)/bin/pip-audit --no-deps --disable-pip -r requirements-dev.lock

plan: $(STAMP) ## terraform plan of both environments with no credentials: build/<env>.json
	mkdir -p $(BUILD)
	@for env in $(ENVS); do \
	  dir=infra/environments/$$env; \
	  $(TF) -chdir=$$dir init -backend=false -input=false >/dev/null && \
	  $(OFFLINE) $(TF) -chdir=$$dir plan -var-file=plan-only.tfvars -out=$(CURDIR)/$(BUILD)/$$env.tfplan -input=false -lock=false -no-color | grep -E "^Plan:|Error" && \
	  $(TF) -chdir=$$dir show -json $(CURDIR)/$(BUILD)/$$env.tfplan > $(BUILD)/$$env.json || exit 1; \
	done

check: $(STAMP) ## policy rules on both plans, and the rules in the plan equal detections/ (make plan first)
	@for env in $(ENVS); do \
	  echo "== policy rules on $$env"; \
	  opa eval --fail-defined --format pretty -d policy -i $(BUILD)/$$env.json 'data.detection.deny[_]' || exit 1; \
	done
	$(DR) audit-rules --plan $(BUILD)/workload.json

fixtures: ## regenerate fixtures/ (the synthetic archive and posture findings); the tests check they are current
	$(PY) scripts/make_drill_fixtures.py fixtures

# The lesson's step 5 on a rehearsal archive: detect, rebuild the timeline from the logs only, measure, verify the archive.
demo-drill: $(STAMP) ## replay the rehearsal archive: alerts, timeline, time to detect and contain, archive integrity
	@echo "== detections over the archive (D1, D2 and D4 must fire)"
	@$(DR) scan --archive $(REHEARSAL) --expect D1,D2,D4 | tail -n 1
	@echo "== the timeline, from the logs only"
	@$(DR) drill --archive $(REHEARSAL) --alerts $(REHEARSAL)/alerts.json
	@echo "== the archive against its digests"
	@$(DR) verify-archive --archive $(REHEARSAL)
	@echo "== the posture baseline"
	@$(DR) posture --findings fixtures/posture --accepted fixtures/posture/accepted.json
	@echo "== containment, as a dry run"
	@$(DR) contain --access-key-id AKIADRILLEXAMPLE0001 | cut -c1-160

review: $(STAMP) ## regenerate docs/REHEARSAL_REVIEW.md from the rehearsal archive
	$(DR) review --archive $(REHEARSAL) --alerts $(REHEARSAL)/alerts.json --output docs/REHEARSAL_REVIEW.md

validate: $(STAMP) plan ## terraform fmt and validate, credential-free plans, the rules, the replay, the review is current
	$(TF) fmt -check -recursive infra
	@for env in $(ENVS); do $(TF) -chdir=infra/environments/$$env validate || exit 1; done
	$(MAKE) --no-print-directory check
	$(MAKE) --no-print-directory demo-drill
	$(DR) review --archive $(REHEARSAL) --alerts $(REHEARSAL)/alerts.json --check docs/REHEARSAL_REVIEW.md

up: ## deploy the archive to the security account, then the trail and detections to the workload account
	scripts/01-deploy-security.sh
	scripts/02-deploy-workload.sh

run: ## check the archive, plant the drill exception, take the posture baseline
	scripts/03-verify-archive.sh
	scripts/04-drill-setup.sh
	scripts/05-posture-baseline.sh before

attack: ## play the attacker against the drill resources (write down the clock time it prints)
	scripts/07-drill-attack.sh

respond: ## contain from the evidence; add APPLY=--apply to change anything (a dry run by default)
	scripts/08-contain.sh $(APPLY)

measure: ## copy the archive out, verify it, rebuild the timeline, measure both times, write the review
	scripts/09-collect-and-measure.sh

down: ## remove the drill exception and delete the workload account's resources (the archive follows after its retention)
	scripts/10-teardown.sh

clean:
	rm -rf $(VENV) $(BUILD) .pytest_cache .mypy_cache .ruff_cache .coverage .import_linter_cache evidence \
	  infra/environments/security/.terraform infra/environments/workload/.terraform

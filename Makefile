UV ?= uv

.PHONY: install lint format typecheck test acceptance property arch crap mutation docs smoke smoke-offline qa

install:
	$(UV) sync --all-groups

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

typecheck:
	$(UV) run ty check

test:
	$(UV) run pytest --cov --cov-report=term-missing --cov-report=json

property:
	$(UV) run pytest tests/unit -k "hypothesis or invariant or always or idempotent or round_trip" -q

acceptance:
	$(UV) run pytest tests/acceptance -q

arch:
	$(UV) run lint-imports

crap:
	$(UV) run python scripts/crap.py

mutation:
	rm -rf mutants
	$(UV) run python scripts/mutation.py

docs:
	$(UV) run mkdocs build --strict

smoke-offline:
	$(UV) run python scripts/smoke.py

smoke:
	$(UV) run agrifm-g build --manifest data/sample_manifest.json --out out/smoke --cache .cache/pdfs
	$(UV) run agrifm-g verify --dataset out/smoke

qa: lint typecheck test property acceptance arch crap mutation docs smoke-offline
	@echo "gauntlet passed"

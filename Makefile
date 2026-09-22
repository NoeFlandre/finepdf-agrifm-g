UV ?= uv
REPO ?= NoeFlandre/finepdf-agrifm-g

.PHONY: install lint format typecheck test acceptance property arch crap mutation docs smoke smoke-offline publish-check qa grid5000-preflight grid5000-submit grid5000-status grid5000-fetch grid5000-cancel grid5000-cleanup

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
	$(UV) run python scripts/mutation.py

docs:
	$(UV) run mkdocs build --strict

smoke-offline:
	$(UV) run python scripts/smoke.py

smoke:
	$(UV) run agrifm-g build --manifest data/sample_manifest.json --out out/smoke --cache .cache/pdfs
	$(UV) run agrifm-g verify --dataset out/smoke
	$(UV) run agrifm-g package --dataset out/smoke --out out/smoke-publish --repo $(REPO)

publish-check:
	AGRIFM_G_INTEGRATION=1 $(UV) run pytest tests/integration/test_published_dataset.py -q

grid5000-preflight:
	$(UV) run python -m scripts.grid5000 preflight

grid5000-submit:
	$(UV) run python -m scripts.grid5000 submit --repo $(REPO)

grid5000-status:
	@test -n "$(RUN_ID)" || (echo "set RUN_ID=<run-id>" >&2; exit 2)
	$(UV) run python -m scripts.grid5000 status --run-id $(RUN_ID)

grid5000-fetch:
	@test -n "$(RUN_ID)" || (echo "set RUN_ID=<run-id>" >&2; exit 2)
	$(UV) run python -m scripts.grid5000 fetch --run-id $(RUN_ID)

grid5000-cancel:
	@test -n "$(RUN_ID)" || (echo "set RUN_ID=<run-id>" >&2; exit 2)
	$(UV) run python -m scripts.grid5000 cancel --run-id $(RUN_ID)

grid5000-cleanup:
	@test -n "$(RUN_ID)" || (echo "set RUN_ID=<run-id>" >&2; exit 2)
	$(UV) run python -m scripts.grid5000 cleanup --run-id $(RUN_ID) --confirm-run-id $(RUN_ID)

qa: lint typecheck test property acceptance arch crap mutation docs smoke-offline
	@echo "gauntlet passed"

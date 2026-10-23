# PYTHONPATH=src: macOS can flag the editable-install .pth file as hidden; Python 3.12 then skips it.
export PYTHONPATH := src

run:
	uv run python -m tk.ui.app

test:
	uv run pytest -q

e2e:
	uv run pytest -q -m e2e

sensitivity:
	uv run python scripts/make_sensitivity.py

lint:
	uv run ruff check .
	uv run mypy src

reference:
	uv run python scripts/make_reference.py

.PHONY: run test e2e lint reference routes sensitivity
routes:
	uv run python scripts/make_routes.py


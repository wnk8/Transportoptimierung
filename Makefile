run:
	uv run python -m tk.ui.app

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run mypy src

reference:
	uv run python scripts/make_reference.py

.PHONY: run test lint reference

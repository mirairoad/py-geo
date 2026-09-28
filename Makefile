.PHONY: dev fix check test

dev:
	uv run serve

fix:
	uv run ruff check --fix .
	uv run ruff format .

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run basedpyright
	uv run pytest

test:
	uv run pytest $(ARGS)

test:
	uv run ruff check . --fix
	uv run black .
	uv run mypy .
	uv run jactionlint

run:
	uv run python -m personal_chemical_database
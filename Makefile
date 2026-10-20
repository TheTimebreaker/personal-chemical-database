test:
	uv run ruff check . --fix
	uv run black .
	uv run mypy .
	uv run jactionlint --profile correctness
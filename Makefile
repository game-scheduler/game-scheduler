.PHONY: setup-local-python act-ci

setup-local-python:
	uv sync --group dev
	uv run --group dev pre-commit install

act-ci:
	scripts/run-act.sh push --job code-quality

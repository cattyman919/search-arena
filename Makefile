.DEFAULT_GOAL := help
.PHONY: help install run test lint format typecheck check clean

help: ## Show available targets
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

install: ## Install dependencies (uv sync)
	uv sync

run: ## Launch the Streamlit app
	@test -f app.py || { echo "app.py not found yet"; exit 1; }
	uv run streamlit run app.py

test: ## Run the test suite
	uv run pytest -q

lint: ## Lint and check formatting with ruff
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-format and fix lint issues
	uv run ruff format .
	uv run ruff check --fix .

typecheck: ## Static type check with mypy
	uv run mypy .

check: lint typecheck test ## Run lint, typecheck and tests

clean: ## Remove caches
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache

.PHONY: install dev-install test lint format type-check run clean help

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	poetry install --no-dev

dev-install: ## Install all dependencies including dev
	poetry install

test: ## Run tests
	poetry run pytest -v

test-cov: ## Run tests with coverage
	poetry run pytest --cov=bot --cov-report=html --cov-report=term

lint: ## Run linter
	poetry run ruff check bot tests

format: ## Format code with black
	poetry run black bot tests

format-check: ## Check code formatting
	poetry run black --check bot tests

type-check: ## Run type checker
	poetry run mypy bot

check-all: lint format-check type-check test ## Run all checks

run: ## Run the bot
	poetry run python -m bot.main

	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache
	rm -rf *.db *.log

db-reset: ## Reset database (delete all data)
	rm -f bot_data.db
	@echo "Database reset complete"


# Justfile

default: help

install: ## Install the environment
	@echo "🚀 Creating virtual environment using pyenv and PDM"
	@pdm install

check: ## Run code quality tools.
	@echo "🚀 Checking pdm lock file consistency with 'pyproject.toml': Running pdm lock --check"
	@pdm lock --check
	@echo "🚀 Linting code: Running pre-commit"
	@pdm run pre-commit run -a
	@echo "🚀 Linting with ruff"
	@pdm run ruff check tests httpie_websockets.py --config pyproject.toml
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@pdm run deptry .

format: ## Format code with ruff and isort
	@echo "🚀 Formatting code: Running ruff"
	@pdm run ruff check --fix . --config pyproject.toml
	@echo "🚀 Formatting code: Running isort"
	@pdm run isort . --settings-path pyproject.toml

test: ## Test the code with pytest.
	@echo "🚀 Testing code: Running pytest"
	@pdm run pytest --cov --cov-config=pyproject.toml --cov-report=xml tests

build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@pdm build

clean-build: ## clean build artifacts
	@rm -rf dist

publish: ## publish a release to pypi.
	@echo "🚀 Publishing."
	@pdm publish --username __token__

publish-test: ## publish a release to testpypi
	@echo "🚀 Publishing to testpypi."
	@pdm publish -r testpypi --username __token__

build-and-publish: build publish ## Build and publish.

docs-test: ## Test if documentation can be built without warnings or errors
	@pdm run mkdocs build -s

docs: ## Build and serve the documentation
	@pdm run mkdocs serve

help:
	just --list

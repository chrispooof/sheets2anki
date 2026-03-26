sources = __init__.py remote_decks/*.py

.PHONY: .uv ## Check that uv is installed
.uv:
	@uv --version || echo 'Please install uv: https://docs.astral.sh/uv/'

.PHONY: install ## Install the package, dependencies, and pre-commit for local development
install:
	uv sync
	uv run pre-commit install

.PHONY: format
format: .uv ## Auto-format python source files
	uv run ruff check --fix $(sources)
	uv run ruff format $(sources)

.PHONY: lint ## Lint python source files
lint: .uv
	uv run ruff check $(sources)
	uv run ruff format --check $(sources)

.PHONY: quality ## Run all quality checks
quality: .uv format lint
	make format
	make lint

.PHONY: test ## Run unit tests
test: .uv
	uv run pytest tests/

.PHONY: install-addon ## Install the addon to Anki for local development
install-addon:
	rm -rf /Users/$(USER)/Library/Application\ Support/Anki2/addons21/$(ID)/ && \
    mkdir -p /Users/$(USER)/Library/Application\ Support/Anki2/addons21/$(ID)/ && \
	cp -af __init__.py config.json meta.json remote_decks /Users/$(USER)/Library/Application\ Support/Anki2/addons21/$(ID)/

# Odysseyra TravelBook build system.
#
# One entry point that installs everything on demand, then either builds the
# command-line tool or runs the PWA (browser viewer) locally. Dependencies are
# installed automatically the first time a target needs them (via stamp files),
# so `make cli` / `make dev` / `make preview` work from a fresh checkout.
#
#   make            # this help
#   make install    # Python venv + web npm deps
#   make cli        # install & verify the `odysseyra-travelBook` CLI
#   make dev        # run the PWA dev server (hot reload)
#   make preview    # build the PWA and serve it locally
#
# Override the interpreter with `make PYTHON=python3.13 ...`; the PWA host/port
# with `make preview HOST=0.0.0.0 PORT=4173`.

PYTHON ?= python3
VENV   := .venv
BIN    := $(VENV)/bin
PIP    := $(BIN)/pip
WEB    := web

# Stamp files record that a slow install step succeeded, so it re-runs only when
# its manifest (pyproject.toml / package.json) changes — not on every `make`.
VENV_STAMP := $(VENV)/.install-stamp
WEB_DEPS   := $(WEB)/node_modules/.install-stamp

.DEFAULT_GOAL := help

# ------------------------------------------------------------------ help
.PHONY: help
help: ## Show this help
	@echo "Odysseyra TravelBook — make targets:"
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make install"
	@echo "  make pdf FILE=examples/france.json OUT=out.pdf"
	@echo "  make preview HOST=0.0.0.0 PORT=4173"

# --------------------------------------------------- dependency install
# Create the venv (if missing) and editable-install odysseyra_travelbook + dev extras.
$(VENV_STAMP): pyproject.toml
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@touch $@

# Install the web (PWA) npm dependencies.
$(WEB_DEPS): $(WEB)/package.json
	cd $(WEB) && npm install
	@touch $@

.PHONY: install
install: $(VENV_STAMP) $(WEB_DEPS) ## Install all deps (Python venv + web npm)
	@echo "✓ all dependencies installed"

.PHONY: deps-py
deps-py: $(VENV_STAMP) ## Install Python deps only (into .venv)

.PHONY: deps-web
deps-web: $(WEB_DEPS) ## Install web (npm) deps only

# ----------------------------------------------------- command-line tool
.PHONY: cli
cli: $(VENV_STAMP) ## Install & verify the odysseyra-travelBook CLI
	@$(BIN)/odysseyra-travelBook --help >/dev/null
	@echo "✓ CLI ready. Run: $(BIN)/odysseyra-travelBook <cmd>   (or: source $(VENV)/bin/activate)"

.PHONY: hooks
hooks: ## Enable the repo git hooks (stamps the build version on push to main)
	@git config core.hooksPath .githooks
	@chmod +x .githooks/* 2>/dev/null || true
	@echo "✓ git hooks enabled (core.hooksPath = .githooks)"

.PHONY: wheel-dist
wheel-dist: $(VENV_STAMP) ## Build a distributable odysseyra_travelbook wheel into dist/
	$(PIP) wheel . --no-deps -w dist
	@echo "✓ wheel written to dist/"

.PHONY: pdf
pdf: $(VENV_STAMP) ## Build a PDF: make pdf FILE=examples/x.json [OUT=out.pdf]
	@test -n "$(FILE)" || { echo "usage: make pdf FILE=path/to.json [OUT=out.pdf]"; exit 2; }
	$(BIN)/odysseyra-travelBook build "$(FILE)" -o "$(or $(OUT),out.pdf)"
	@echo "✓ wrote $(or $(OUT),out.pdf)"

.PHONY: test
test: $(VENV_STAMP) ## Run the Python test suite
	$(BIN)/pytest

# ------------------------------------------------------- PWA (viewer)
# The browser runs a Python *wheel* built from src/, not the source tree, so it
# must be (re)built whenever the package changes. build-wheel.sh defaults to
# this repo's .venv pip, which the venv stamp guarantees exists.
.PHONY: wheel
wheel: $(VENV_STAMP) ## Build the in-browser Python wheel (web/public/py)
	cd $(WEB) && npm run wheel

.PHONY: dev
dev: $(WEB_DEPS) wheel ## Run the PWA dev server (Vite, hot reload)
	cd $(WEB) && npm run dev -- $(if $(HOST),--host $(HOST)) $(if $(PORT),--port $(PORT))

.PHONY: build-web
build-web: $(WEB_DEPS) wheel ## Build the PWA into web/dist
	cd $(WEB) && npm run build

.PHONY: preview
preview: build-web ## Build the PWA and serve it locally (default port 4173)
	cd $(WEB) && npm run preview -- $(if $(HOST),--host $(HOST)) --port $(or $(PORT),4173)

# ------------------------------------------------------------ cleanup
.PHONY: clean
clean: ## Remove build artifacts (dist, web/dist, in-browser wheels, caches)
	rm -rf dist $(WEB)/dist $(WEB)/public/py
	rm -rf *.egg-info src/*.egg-info
	find . -path ./$(VENV) -prune -o -name __pycache__ -type d -exec rm -rf {} +
	@echo "✓ cleaned build artifacts"

.PHONY: distclean
distclean: clean ## Also remove the venv and web/node_modules
	rm -rf $(VENV) $(WEB)/node_modules
	@echo "✓ removed venv and node_modules"

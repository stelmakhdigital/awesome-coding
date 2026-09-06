# awesome-coding — туллинг
#
# Цели:
#   make validate              — все проверки (frontmatter + manifest + ссылки)
#   make validate-frontmatter  — только frontmatter
#   make validate-manifest     — только manifest
#   make validate-links        — только ссылки
#   make validate-mermaid      — синтаксис всех mermaid-блоков (нужен node + npm i)
#   make search Q=async        — поиск записей в manifest по тегу/названию
#   make check-versions        — сверка закреплённых версий с актуальными (сеть)

PYTHON ?= python3
NODE ?= node

.PHONY: help validate validate-frontmatter validate-manifest validate-links \
        validate-mermaid search check-versions

help:
	@echo "Цели:"
	@echo "  validate              — все проверки (frontmatter + manifest + ссылки)"
	@echo "  validate-frontmatter  — YAML frontmatter (обязательные поля, id, статусы)"
	@echo "  validate-manifest     — index/manifest.yaml (пути, соответствие frontmatter)"
	@echo "  validate-links        — относительные markdown-ссылки"
	@echo "  validate-mermaid      — синтаксис mermaid-блоков (нужны node + npm install в tools/)"
	@echo "  search Q=<запрос>     — поиск записей в manifest по тегу/названию"
	@echo "  check-versions        — сверка версий из AGENTS.md с актуальными (нужна сеть)"
	@echo ""
	@echo "Зависимости: $(PYTHON) 3.9+, PyYAML (pip install pyyaml); для validate-mermaid — node 20+"

validate: validate-frontmatter validate-manifest validate-links

validate-frontmatter:
	$(PYTHON) tools/validate.py --check frontmatter

validate-manifest:
	$(PYTHON) tools/validate.py --check manifest

validate-links:
	$(PYTHON) tools/validate.py --check links

validate-mermaid:
	@test -f tools/node_modules/mermaid/package.json \
		|| { echo "нужны зависимости: cd tools && npm install"; exit 1; }
	$(NODE) tools/validate_mermaid.mjs

search:
	@test -n "$(Q)" || { echo "Использование: make search Q=async"; exit 1; }
	$(PYTHON) tools/search.py "$(Q)"

check-versions:
	$(PYTHON) tools/check_versions.py

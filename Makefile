# awesome-coding — туллинг
#
# Цели:
#   make validate              — все проверки (frontmatter + manifest + индексы + README + ссылки)
#   make validate-frontmatter  — только frontmatter
#   make validate-manifest     — только manifest
#   make validate-indexes      — README каталогов ↔ файлы раздела
#   make readme                — перегенерировать «Статус разделов» из index/*.yaml
#   make validate-links        — только ссылки
#   make validate-mermaid      — синтаксис всех mermaid-блоков (нужен node + npm i)
#   make search Q=async        — поиск записей по тегу/названию по index/*.yaml
#   make verify                — прогон код-блоков через тулчейны в Docker (нужен docker)
#   make verify-fix            — то же + поднять verified/updated в index/ по итогу
#   make check-versions        — сверка закреплённых версий с актуальными (сеть)
#   make check-stale           — записи с устаревшим `updated` (квартальный аудит)

PYTHON ?= python3
NODE ?= node

.PHONY: help validate validate-frontmatter validate-manifest validate-indexes \
        validate-links validate-mermaid validate-readme readme search verify verify-fix \
        check-versions check-stale

help:
	@echo "Цели:"
	@echo "  validate              — все проверки (frontmatter + manifest + индексы + README + ссылки)"
	@echo "  validate-frontmatter  — YAML frontmatter (обязательные поля, id, статусы)"
	@echo "  validate-manifest     — index/*.yaml (пути, соответствие frontmatter)"
	@echo "  validate-indexes      — README каталогов упоминают все файлы раздела"
	@echo "  readme                — перегенерировать «Статус разделов» из index/*.yaml"
	@echo "  validate-links        — относительные markdown-ссылки"
	@echo "  validate-mermaid      — синтаксис mermaid-блоков (нужны node + npm install в tools/)"
	@echo "  search Q=<запрос>     — поиск записей по тегу/названию по index/*.yaml"
	@echo "  verify                — код-блоки записей через реальные тулчейны (Docker)"
	@echo "  verify-fix            — verify + поднять verified/updated в index/, где прогон доказал"
	@echo "  check-versions        — сверка версий из AGENTS.md с актуальными (нужна сеть)"
	@echo '  check-stale           — устаревший frontmatter `updated` (> 180 дней)'
	@echo ""
	@echo "Зависимости: $(PYTHON) 3.9+, PyYAML (pip install pyyaml); validate-mermaid — node 20+; verify — docker"

validate: validate-frontmatter validate-manifest validate-indexes validate-readme validate-links

validate-frontmatter:
	$(PYTHON) tools/validate.py --check frontmatter

validate-manifest:
	$(PYTHON) tools/validate.py --check manifest

validate-indexes:
	$(PYTHON) tools/validate.py --check indexes

validate-readme:
	$(PYTHON) tools/readme.py --check

readme:
	$(PYTHON) tools/readme.py

validate-links:
	$(PYTHON) tools/validate.py --check links

validate-mermaid:
	@test -f tools/node_modules/mermaid/package.json \
		|| { echo "нужны зависимости: cd tools && npm install"; exit 1; }
	$(NODE) tools/validate_mermaid.mjs

search:
	@test -n "$(Q)" || { echo "Использование: make search Q=async"; exit 1; }
	$(PYTHON) tools/search.py "$(Q)"

verify:
	$(PYTHON) tools/verify_snippets.py --jobs 8

verify-fix:
	$(PYTHON) tools/verify_snippets.py --jobs 8 --fix-index

check-versions:
	$(PYTHON) tools/check_versions.py

check-stale:
	$(PYTHON) tools/check_stale.py

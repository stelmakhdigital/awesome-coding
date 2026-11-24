# awesome-coding — туллинг
#
# Цели:
#   make validate              — все проверки (frontmatter + manifest + индексы + текст + алиасы + README + ссылки)
#   make validate-frontmatter  — только frontmatter
#   make validate-manifest     — только manifest
#   make validate-indexes      — README каталогов ↔ файлы раздела
#   make readme                — перегенерировать «Статус разделов» из index/*.yaml
#   make validate-links        — только ссылки
#   make validate-mermaid      — синтаксис всех mermaid-блоков (нужен node + npm i)
#   make test                  — тесты туллинга (валидатор, разбор формата, поиск)
#   make search Q=async        — поиск записей по тегу/названию/алиасу (ранжировано)
#   make verify                — прогон код-блоков через тулчейны в Docker (нужен docker)
#   make verify-fix            — то же + поднять verified/updated в index/ по итогу
#   make gofmt RECORD=go/snippets/x.md — отформатировать go-блоки записи на месте (нужен docker)
#   make check-versions        — сверка закреплённых версий с актуальными (сеть)
#   make check-stale           — записи с устаревшим `updated` (квартальный аудит)
#   make release-check VERSION=vN.N — сверить блок CHANGELOG и пин SKILL.md перед тегом

PYTHON ?= python3
NODE ?= node

.PHONY: help validate validate-frontmatter validate-manifest validate-indexes \
        validate-structure validate-text validate-aliases \
        validate-links validate-mermaid validate-readme readme test search verify verify-fix \
        check-versions check-stale gofmt release-check

help:
	@echo "Цели:"
	@echo "  validate              — все проверки (frontmatter + каталог + текст + README + ссылки)"
	@echo "  validate-frontmatter  — YAML frontmatter (обязательные поля, id, статусы)"
	@echo "  validate-manifest     — index/*.yaml (пути, соответствие frontmatter)"
	@echo "  validate-indexes      — README каталогов упоминают все файлы раздела"
	@echo "  validate-structure    — у сниппетов/паттернов есть разделы выбора и Related"
	@echo "  validate-text         — CJK и смешение раскладок в прозе"
	@echo "  validate-aliases      — index/aliases.yaml: форма ключей и существующие id"
	@echo "  readme                — перегенерировать «Статус разделов» из index/*.yaml"
	@echo "  validate-links        — относительные markdown-ссылки"
	@echo "  validate-mermaid      — синтаксис mermaid-блоков (нужны node + npm install в tools/)"
	@echo "  test                  — тесты туллинга (вердикты раннеров, валидатор, поиск)"
	@echo "  search Q=<запрос>     — поиск по тегу/названию/алиасу, от близких к далёким"
	@echo "  verify                — код-блоки записей через реальные тулчейны (Docker)"
	@echo "  verify-fix            — verify + поднять verified/updated в index/, где прогон доказал"
	@echo "  gofmt RECORD=<путь>     — отформатировать go-блоки записи на месте (Docker)"
	@echo "  release-check VERSION=vN.N — блок CHANGELOG и пин SKILL.md согласованы"
	@echo "  check-versions        — сверка версий из AGENTS.md с актуальными (нужна сеть)"
	@echo '  check-stale           — устаревший frontmatter `updated` (> 180 дней)'
	@echo ""
	@echo "Зависимости: $(PYTHON) 3.9+, PyYAML (pip install pyyaml); validate-mermaid — node 20+; verify — docker"

validate: validate-frontmatter validate-manifest validate-indexes validate-structure validate-text validate-aliases validate-readme validate-links

validate-frontmatter:
	$(PYTHON) tools/validate.py --check frontmatter

validate-manifest:
	$(PYTHON) tools/validate.py --check manifest

validate-indexes:
	$(PYTHON) tools/validate.py --check indexes

validate-structure:
	$(PYTHON) tools/validate.py --check structure

validate-text:
	$(PYTHON) tools/validate.py --check text

validate-aliases:
	$(PYTHON) tools/validate.py --check aliases

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

test:
	$(PYTHON) tools/test_tools.py

search:
	@test -n "$(Q)" || { echo "Использование: make search Q=async"; exit 1; }
	$(PYTHON) tools/search.py "$(Q)"

verify:
	$(PYTHON) tools/verify_snippets.py --jobs 8

verify-fix:
	$(PYTHON) tools/verify_snippets.py --jobs 8 --fix-index

check-versions:
	$(PYTHON) tools/check_versions.py

gofmt:
	$(PYTHON) tools/gofmt_records.py $(RECORD)

release-check:
	$(PYTHON) tools/release.py check --version $(VERSION)

check-stale:
	$(PYTHON) tools/check_stale.py

# awesome-coding — туллинг
#
# Цели:
#   make validate              — все проверки (frontmatter + manifest + ссылки)
#   make validate-frontmatter  — только frontmatter
#   make validate-manifest     — только manifest
#   make validate-links        — только ссылки

PYTHON ?= python3

.PHONY: help validate validate-frontmatter validate-manifest validate-links

help:
	@echo "Цели:"
	@echo "  validate              — все проверки"
	@echo "  validate-frontmatter  — YAML frontmatter (обязательные поля, id, статусы)"
	@echo "  validate-manifest     — index/manifest.yaml (пути, соответствие frontmatter)"
	@echo "  validate-links        — относительные markdown-ссылки"
	@echo ""
	@echo "Зависимости: $(PYTHON) 3.9+, PyYAML (pip install pyyaml)"

validate: validate-frontmatter validate-manifest validate-links

validate-frontmatter:
	$(PYTHON) tools/validate.py --check frontmatter

validate-manifest:
	$(PYTHON) tools/validate.py --check manifest

validate-links:
	$(PYTHON) tools/validate.py --check links

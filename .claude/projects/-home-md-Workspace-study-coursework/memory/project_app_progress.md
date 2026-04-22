---
name: app_progress
description: Текущий прогресс разработки Python-приложения (app/), статус задач §5.1–§5.12
type: project
---

Разработка Python-приложения app/ ведётся по ТЗ docs/app_tz.md.

**Why:** ЭП-отчёт содержит плейсхолдеры для 4 скриншотов GUI и 3 приложений. Нужен рабочий MVP.

**How to apply:** При продолжении работы — сверяться с этим статусом и docs/app_tz.md §5.X.

## Статус задач (по состоянию на 2026-04-23)

| Задача | Статус | Файлы |
|--------|--------|-------|
| §5.1 Инфраструктура | ✅ DONE | data/graph_calibration.json, app/main.py, app/ui/main_window.py (скелет), black+pyyaml+pytest в venv |
| §5.2 graph/model.py | ✅ DONE | app/graph/model.py, app/tests/test_model.py (7/7 ✓) |
| §5.3 db/repository.py | ✅ DONE | app/db/schema.sql, app/db/repository.py, app/tests/test_repository.py (4/4 ✓) |
| §5.4 db/seed.py | ✅ DONE | app/db/seed.py, app/db/crypters.db (120 записей) |
| §5.5 graph/optimizer.py | ✅ DONE | app/graph/optimizer.py, app/tests/test_optimizer.py (5/5 ✓) |
| §5.6 builder/assembler.py | ✅ DONE | app/builder/assembler.py |
| §5.7 ui/config_form.py | ✅ DONE | app/ui/config_form.py |
| §5.8 ui/results_panel.py | ✅ DONE | app/ui/results_panel.py, main_window.py обновлён |
| §5.10 ui/reference_db_widget.py |  ✅DONE | app/ui/reference_db_widget.py |
| §5.9 visualizer + graph_widget | ✅DONE | app/graph/visualizer.py, app/ui/graph_widget.py |
| §5.11 experiments | ✅DONE | app/experiments/*, app/ui/experiments_widget.py |
| Финальная интеграция | ⏳ PENDING | main_window.py — подключить ReferenceDbWidget + ExperimentsWidget |
| §5.12 C++ криптеры | ⏳ ОТЛОЖЕНО | crypters/crypter_{b,c,d}/main.cpp — под ЭП-таблицу |

## Итого тестов: 16/16 ✅

## Что осталось после агентов
1. Проверить §5.9 и §5.11 (импорты + тесты).
2. В main_window.py заменить заглушки «База эталонных» и «Эксперименты» на реальные виджеты.
3. Сделать тест-прогон приложения через headless QApplication.
4. Снять 4 скриншота для ЭП-отчёта.

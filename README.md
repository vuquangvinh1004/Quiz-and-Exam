# Quiz Desktop App

Desktop-first, offline-first quiz application built with Python and PySide6.

## Quick Start (Development)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
python main.py
```

## Run Tests

```bash
pytest tests/unit -v
```

## Project Structure

```
quiz_desktop_app/
├── main.py              Application entry point
├── config/              Settings, paths, database config
├── core/
│   ├── database/        SQLAlchemy models, Alembic migrations, session
│   ├── domain/          Entities and service layer stubs
│   └── utils/           Constants, exceptions, logger, helpers, validators
├── modules/             Business logic modules (import, grading, runner, …)
├── ui/                  PySide6 views, widgets, dialogs, styles
├── tests/               Unit, integration and UI tests
└── data/                User data (gitignored)
```

## Tech Stack

| Component | Library |
|---|---|
| Desktop UI | PySide6 ≥ 6.6 |
| Database | SQLite via SQLAlchemy ≥ 2.0 |
| Migrations | Alembic ≥ 1.13 |
| Settings | pydantic-settings ≥ 2.0 |
| Logging | loguru ≥ 0.7 |
| Testing | pytest + pytest-qt + pytest-cov |
| Packaging | PyInstaller ≥ 6.0 |

## Import Format

See [QUIZ_APP_IMPORT_FORMAT.md](QUIZ_APP_IMPORT_FORMAT.md) for the official
CSV / Excel import schema.

## Architecture

See [QUIZ_APP_ARCHITECTURE.md](QUIZ_APP_ARCHITECTURE.md) for the full design
document including database schema, mode rules and coding standards.

## Software Design Philosophy

This project follows strategic design principles adapted from
`philosophy_of_software_design.md` to keep long-term complexity under control.

1. Prioritize reducing complexity over short-term implementation speed.
2. Prefer deep modules: small interfaces, stronger internal implementation.
3. Avoid pass-through classes and methods that do not add abstraction value.
4. Pull complexity downward into services/modules, not UI event handlers.
5. Keep business rules in a single source of truth to prevent leakage.
6. Use targeted exception handling; broad catches must log context and recovery.
7. Add regression and architecture guardrail tests when making risky changes.

For full project-level policy, see:

- [QUIZ_APP_ARCHITECTURE.md](QUIZ_APP_ARCHITECTURE.md)
- [QUIZ_APP_ROADMAP.md](QUIZ_APP_ROADMAP.md)

# Contributing

Thank you for contributing to this project.

## Development Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r requirements-dev.txt`
3. Run the app:
   - `python main.py`

## Quality Checks

Before opening a pull request:
1. Run lint and format checks:
   - `ruff check .`
   - `ruff format --check .`
2. Run tests:
   - `python -m pytest tests/unit tests/integration -q`
   - `python -m pytest tests/ui -q`

## Pull Request Guidelines

- Keep changes focused and reviewable.
- Add or update tests for logic changes.
- Update docs when behavior, architecture, or workflows change.
- Follow existing naming and structure conventions.

## Security and Privacy

Do not commit local data or secrets.
Blocked examples include:
- `data/**`, backups, logs
- `*.db`, `*.sqlite`, `*.sqlite3`
- `.env`, keys, credentials

The repository includes automated guards in pre-commit and CI to prevent accidental leaks.

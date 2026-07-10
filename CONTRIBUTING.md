# Contributing to Competitor Intelligence Engine

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Set up** the development environment (see README.md)
4. **Create** a feature branch: `git checkout -b feature/your-feature-name`

## Development Workflow

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

### Running Tests

```bash
# Unit tests only (no database required)
pytest tests/unit/

# Integration tests (requires PostgreSQL or will use SQLite)
CI_TEST_DATABASE_URL=sqlite+aiosqlite:///:memory: pytest tests/integration/

# Full suite
CI_TEST_DATABASE_URL=sqlite+aiosqlite:///:memory: pytest tests/
```

### Code Quality

All contributions must pass:

```bash
ruff check .          # Linting
black --check .       # Formatting
mypy app/             # Type checking
```

To auto-fix:

```bash
ruff check . --fix
black .
```

## Submitting Changes

1. Ensure **all tests pass** and **CI is green**
2. Add tests for any new functionality
3. Update documentation if needed
4. Submit a **Pull Request** with a clear description of the changes

## Adding a New Parser Strategy

1. Create `app/parsers/strategies/your_strategy.py`
2. Implement `ParsingStrategy` base class
3. Add to `DEFAULT_STRATEGIES` in `app/parsers/strategy_parser.py`
4. Add unit tests in `tests/unit/test_your_strategy.py`

## Adding a New Collector

1. Create `app/collectors/your_collector.py`
2. Extend `BaseCollector`
3. Add repository in `app/database/repositories/`
4. Add DB model in `app/database/models.py`
5. Create Alembic migration: `alembic revision --autogenerate -m "add your table"`

## Reporting Bugs

Use the [GitHub issue tracker](.github/ISSUE_TEMPLATE/bug_report.md).  
Include steps to reproduce, expected behavior, and actual behavior.

## Code of Conduct

Be respectful, constructive, and welcoming. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

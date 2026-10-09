# Contributing to SyncLab

Thank you for contributing to SyncLab! Follow these guidelines to ensure smooth collaboration:

## Development Setup

1. Clone repository: `git clone https://github.com/kkm121/SyncLab.git`
2. Create environment: `python -m venv .venv` and activate it.
3. Install dependencies: `pip install -r requirements.txt`
4. Run tests: `python -m pytest -v` (must pass 100% with exit code 0).
5. Run demonstration: `python scripts/demo_synclab.py`

## Branching & Commit Conventions

- Use feature branches: `feature/<name>` or `bugfix/<name>`.
- Follow Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.

## Pull Requests

- Verify all 32 pytest tests pass before submitting.
- Fill out the PR template with verification logs and description.

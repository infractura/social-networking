# Contributing Guide

Thank you for considering contributing to Social Integrator!

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/yourusername/social-integrator.git
   cd social-integrator
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   .\venv\Scripts\activate  # Windows
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Code Style

We use the following tools to maintain code quality:

- Black for code formatting
- isort for import sorting
- Ruff for linting
- mypy for type checking

These checks are automatically run by pre-commit hooks.

## Testing

Run the test suite:

```bash
pytest

# Run with coverage
pytest --cov=social_integrator

# Run integration tests
pytest --run-integration
```

## Documentation

Build the documentation:

```bash
mkdocs build

# Serve documentation locally
mkdocs serve
```

## Pull Request Process

1. Create a new branch for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

3. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Open a Pull Request

## Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- feat: A new feature
- fix: A bug fix
- docs: Documentation changes
- style: Code style changes (formatting, etc)
- refactor: Code refactoring
- test: Adding or updating tests
- chore: Maintenance tasks

## Code of Conduct

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md).
By participating in this project you agree to abide by its terms.

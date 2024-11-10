#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd: str) -> int:
    """Run a shell command and return its exit code."""
    return subprocess.call(cmd, shell=True)

def test(args: argparse.Namespace) -> int:
    """Run tests with optional coverage."""
    cmd = ["pytest"]
    if args.coverage:
        cmd.extend(["--cov=social_integrator", "--cov-report=term-missing"])
    if args.integration:
        cmd.append("--run-integration")
    return run_command(" ".join(cmd))

def lint(args: argparse.Namespace) -> int:
    """Run linting tools."""
    cmds = [
        "black .",
        "isort .",
        "ruff check .",
        "mypy src tests"
    ]
    for cmd in cmds:
        if result := run_command(cmd):
            return result
    return 0

def docs(args: argparse.Namespace) -> int:
    """Build and serve documentation."""
    if args.serve:
        return run_command("mkdocs serve")
    return run_command("mkdocs build")

def clean(args: argparse.Namespace) -> int:
    """Clean build artifacts."""
    cmds = [
        "rm -rf build/ dist/ *.egg-info",
        "find . -type d -name __pycache__ -exec rm -rf {} +",
        "find . -type f -name "*.pyc" -delete",
        "find . -type f -name "*.pyo" -delete",
        "find . -type f -name "*.pyd" -delete",
        "find . -type f -name ".coverage" -delete",
        "find . -type d -name "htmlcov" -exec rm -rf {} +",
        "find . -type d -name ".pytest_cache" -exec rm -rf {} +",
        "find . -type d -name ".mypy_cache" -exec rm -rf {} +",
        "find . -type d -name ".ruff_cache" -exec rm -rf {} +"
    ]
    for cmd in cmds:
        if result := run_command(cmd):
            return result
    return 0

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Development helper script")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("-c", "--coverage", action="store_true", help="Run with coverage")
    test_parser.add_argument("-i", "--integration", action="store_true", help="Run integration tests")

    # Lint command
    subparsers.add_parser("lint", help="Run linting tools")

    # Docs command
    docs_parser = subparsers.add_parser("docs", help="Build documentation")
    docs_parser.add_argument("-s", "--serve", action="store_true", help="Serve documentation")

    # Clean command
    subparsers.add_parser("clean", help="Clean build artifacts")

    args = parser.parse_args()

    commands = {
        "test": test,
        "lint": lint,
        "docs": docs,
        "clean": clean
    }

    return commands[args.command](args)

if __name__ == "__main__":
    sys.exit(main())

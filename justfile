set windows-shell := ["pwsh.exe", "-c"]

# Print the help message.
@help:
    echo "Usage: just [RECIPE]\n"
    just --list

# Run all tests.
test:
    uv run pytest

# Run tests with verbose output.
test-verbose:
    uv run pytest -v

# Run all pre-commit hooks.
pre-commit:
    uv run prek run --all-files

# Aliases
alias t := test
alias tv := test-verbose
alias pc := pre-commit

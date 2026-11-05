set windows-shell := ["pwsh.exe", "-c"]

# Print the help message.
@help:
    echo "Usage: just [RECIPE]\n"
    just --list

# Build the examples gallery (pass --no-run, --no-cache or example paths).
# The `docs` group holds the libraries the examples import.
gallery *args:
    uv run --group docs zallery {{args}}

# Build documentation.
docs: gallery
    uv run zensical build --strict

# Serve documentation locally for development.
serve-docs: gallery
    uv run zensical serve

# Clean documentation build artifacts.
[unix]
clean-docs:
    rm -rf site/ docs/examples/_built docs/examples/index.md

# Clean documentation build artifacts.
[windows]
clean-docs:
    foreach ($p in 'site', 'docs/examples/_built', 'docs/examples/index.md') { if (Test-Path $p) { Remove-Item -Recurse -Force $p } }

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
alias g := gallery
alias d := docs
alias cd := clean-docs
alias sd := serve-docs
alias t := test
alias tv := test-verbose
alias pc := pre-commit

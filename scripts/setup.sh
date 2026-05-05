#!/usr/bin/env sh
set -eu

echo "Setting up Easy Sanity..."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed."
  echo "Install it from https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

uv sync
uv run easy-sanity install-browser

echo
echo "Setup complete."
echo "Next steps:"
echo "1. Add this repo as an MCP server in your IDE."
echo "2. Restart the IDE."
echo "3. Try sample_tasks_list or sample_tasks_import to load example smoke tasks."

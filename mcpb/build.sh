#!/usr/bin/env bash
# Build dist/pindropped-mcp-<version>.mcpb (Claude Desktop extension, uv runtime).
set -euo pipefail
cd "$(dirname "$0")/.."
VER=$(python3 -c "import json;print(json.load(open('mcpb/manifest.json'))['version'])")
STAGE=$(mktemp -d)
cp mcpb/manifest.json pyproject.toml README.md LICENSE "$STAGE/"
cp assets/logo-400.png "$STAGE/icon.png"
mkdir -p "$STAGE/src" && cp -r src/pindropped_mcp "$STAGE/src/"
find "$STAGE" -name __pycache__ -prune -exec rm -rf {} +
mkdir -p dist
npx -y @anthropic-ai/mcpb validate "$STAGE/manifest.json"
npx -y @anthropic-ai/mcpb pack "$STAGE" "dist/pindropped-mcp-$VER.mcpb"
rm -rf "$STAGE"
sha256sum "dist/pindropped-mcp-$VER.mcpb"

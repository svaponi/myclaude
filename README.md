# myclaude

Interactive CLI tool for managing your Claude MCPs and agent skills on a per-repository basis.

![myclaude.gif](myclaude.gif)

## Prerequisites

- `uv` (install via Homebrew: `brew install uv`)

## Installation

Define `MYCLAUDE_HOME` variable in your terminal (change it to a different location if you want):

```shell
MYCLAUDE_HOME="$HOME/.myclaude"
```

Then run the following commands to generate the `myclaude` executable:

```shell
[ -d "$MYCLAUDE_HOME" ] || mkdir -p "$MYCLAUDE_HOME"
curl -fsSL https://raw.githubusercontent.com/svaponi/myclaude/HEAD/myclaude.py > "$MYCLAUDE_HOME/myclaude.py"

cat << EOF > myclaude
#!/usr/bin/env bash
uv run --script "$MYCLAUDE_HOME/myclaude.py" "\$@" || exit 0
claude "\$@"
EOF

chmod +x myclaude
```

Then copy `myclaude` to any directory on your `PATH`.

### MCPs

Create a `$MYCLAUDE_HOME/mcps.json` file with the following structure (add your own MCP servers as needed):

```json
{
  "mcpServers": {
    "atlassian": {
      "type": "http",
      "url": "https://mcp.atlassian.com/v1/mcp"
    },
    "datadog": {
      "type": "http",
      "url": "https://mcp.datadoghq.com/api/unstable/mcp-server/mcp?toolsets=core"
    }
  }
}
```

### Skills

Create a `$MYCLAUDE_HOME/skills` directory with same structure as `.claude/skills` (add your own skills as needed):

```
<MYCLAUDE_HOME>
  +-- skills  
  |  +-- grill-me
  |  |   +-- SKILL.md
  |  +-- ubiquitous-language
  |  |   +-- SKILL.md
  |  +-- ...
  |      
  +-- mcps.json
```
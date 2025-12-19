# mcp-browsy

World-class browser automation MCP using direct CDP connection.

**No extension required** - just launch and automate.

## Features

- **Direct CDP Connection**: Connects directly to Chrome DevTools Protocol, no Playwright relay
- **Hybrid Launch Strategy**: Connects to existing Chrome or launches new instance
- **Profile Support**: Uses your existing Chrome profile or temporary profile when needed
- **Cross-Platform**: Works on macOS, Windows, and Linux

## Installation

```bash
pip install -e .
```

## Usage

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "mcp-browsy": {
      "command": "mcp-browsy"
    }
  }
}
```

## Tools

### Lifecycle
- `browsy_launch` - Launch browser and connect
- `browsy_close` - Close browser and cleanup

### Navigation
- `browsy_navigate` - Navigate to URL
- `browsy_reload` - Reload page
- `browsy_back` / `browsy_forward` - History navigation
- `browsy_tabs` - List open tabs
- `browsy_tab_switch` / `browsy_tab_new` / `browsy_tab_close` - Tab management

### Input
- `browsy_click` - Click element or coordinates
- `browsy_type` - Type text into element
- `browsy_press` - Press keyboard key
- `browsy_hover` - Hover over element
- `browsy_scroll` - Scroll page or element
- `browsy_select` - Select dropdown option

### Inspection
- `browsy_snapshot` - Get accessibility tree snapshot
- `browsy_screenshot` - Capture screenshot
- `browsy_get_text` / `browsy_get_html` - Extract content
- `browsy_evaluate` - Execute JavaScript
- `browsy_cookies` - Get browser cookies

## Architecture

```
mcp-browsy
├── cdp.py          # Async WebSocket CDP client
├── browser.py      # BrowserManager with launch/connect
├── dom.py          # DOM element utilities
├── server.py       # FastMCP server entry point
└── tools/
    ├── navigation.py  # URL and history tools
    ├── input.py       # Mouse and keyboard tools
    └── inspection.py  # Snapshot and screenshot tools
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run server
mcp-browsy
```

## License

MIT

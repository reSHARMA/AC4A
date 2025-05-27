# Element Hider System

A visual element hiding system for web browsers, inspired by uBlock Origin's zapper mode. Hide unwanted elements on any website with persistent rule storage.

## Features

- **Visual Element Picker**: Point-and-click interface to hide elements
- **Persistent Rules**: Automatically saves hiding rules to JSON config file
- **Domain-Based Rules**: Rules are organized by domain for easy management
- **Automatic Application**: Hidden elements stay hidden across browsing sessions
- **Real-time Feedback**: Visual indicators and confirmations for user actions

## Quick Start

### Normal Mode (Default)
Applies saved element hiding rules automatically:
```bash
./setup.sh
# or
./setup.sh --normal
```

### Zapper Mode (Configuration)
Visual element picker interface for creating new rules:
```bash
./setup.sh --config
```

## Modes

### 🎯 Zapper Mode (`--config`)
Pure visual interface for element hiding configuration:
- **No command line interface** - everything is visual
- **Hover** over elements to highlight them
- **Click** to hide elements permanently  
- **Auto-save** rules to `element_hiding_config.json`
- **Press ESC** to temporarily disable zapper
- **Navigate freely** and zap elements on any website

Visual indicators:
- Red crosshair cursor when zapper is active
- "🎯 ZAPPER MODE" indicator in top-right corner
- Red outline highlights elements on hover
- Green confirmation when elements are zapped

### 📋 Normal Mode (`--normal`)
Lightweight browser with automatic rule application:
- Loads saved rules from configuration file
- Automatically hides elements based on existing rules
- No configuration interface
- Optimized for browsing with pre-configured rules

## Configuration File

Rules are stored in `element_hiding_config.json`:
```json
{
  "rules": {
    "example.com": [
      ".advertisement",
      "#popup-banner",
      "[data-ad-slot]"
    ],
    "news-site.com": [
      ".sidebar-ads",
      ".newsletter-signup"
    ]
  }
}
```

## Browser Access

Once running, access the browser through:

- **VNC Web Interface**: http://localhost:6080/vnc.html (main browser interface)
- **DevTools Protocol**: http://localhost:9222 (browser debugging)
- **Screenshot API**: http://localhost:8080 (programmatic screenshots)

## Technical Details

### Element Selector Generation
The system generates CSS selectors in order of preference:
1. **ID selector**: `#unique-id` (most reliable)
2. **Class selector**: `.class1.class2` (good for styled elements)
3. **Data attribute**: `[data-attribute="value"]` (semantic selectors)
4. **Nth-of-type**: `div:nth-of-type(3)` (positional fallback)

### Rule Application
- Rules are injected as CSS with `display: none !important`
- Applied on page load and navigation events
- New pages automatically inherit domain rules
- Real-time application as rules are created

### Files

- `browser_launcher_with_hider.js` - Zapper mode browser launcher
- `browser_launcher.js` - Normal mode browser launcher  
- `element_hider.js` - Core element hiding logic
- `element_hiding_config.json` - Rule storage (auto-created)
- `setup.sh` - Main setup script with mode selection

## Examples

### Basic Zapping Workflow
1. Run `./setup.sh --config` to start zapper mode
2. Navigate to any website in the browser
3. Hover over annoying elements (ads, popups, etc.)
4. Click to hide them permanently
5. Rules are automatically saved and applied

### Managing Rules
Since there's no CLI in config mode, rule management is purely visual:
- **Add rules**: Click elements in zapper mode
- **Remove rules**: Edit `element_hiding_config.json` manually
- **View rules**: Check the JSON file or console output

## Troubleshooting

### Zapper Not Working
- Check for "🎯 ZAPPER MODE" indicator in browser
- Press ESC to toggle zapper on/off
- Look for red crosshair cursor
- Check browser console for error messages

### Rules Not Saving
- Verify write permissions on `element_hiding_config.json`
- Check console output for save confirmations
- Ensure browser can access local file system

### Extension Issues
- uBlock Origin Lite should load automatically
- Check DevTools for extension errors
- Verify extension files in `../extension/ublock-origin-lite/`

For more help, check the console output or setup script diagnostics. 
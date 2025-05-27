# HTML Source API

This document describes the HTML source API endpoints that allow you to retrieve the HTML content of webpages currently displayed in the Chromium browser.

## Overview

The HTML source API uses Chrome DevTools Protocol (CDP) to communicate directly with the Chromium browser and extract the HTML content of the currently active page. This is equivalent to pressing `Ctrl+U` in the browser to view the page source.

## Prerequisites

- Chromium must be launched with DevTools Protocol enabled (`--remote-debugging-port=9222`)
- The Flask server must be running with the required dependencies (`requests`, `websocket-client`)

## API Endpoints

### 1. Get HTML Source

**Endpoint:** `GET /html-source`

**Description:** Retrieves the HTML source code of the currently active page in Chromium.

**Response:**
```json
{
  "success": true,
  "url": "https://example.com",
  "title": "Example Domain",
  "html": "<!DOCTYPE html><html>...</html>",
  "timestamp": 1703123456.789
}
```

**Error Response:**
```json
{
  "error": "No active browser tab found",
  "message": "Chrome DevTools Protocol connection failed or no tabs available"
}
```

### 2. Get Browser Tabs

**Endpoint:** `GET /tabs`

**Description:** Lists all open tabs in the Chromium browser.

**Response:**
```json
{
  "success": true,
  "tabs": [
    {
      "id": "tab-id-123",
      "title": "Example Domain",
      "url": "https://example.com",
      "active": true
    }
  ],
  "count": 1
}
```

### 3. Health Check (Updated)

**Endpoint:** `GET /health`

**Description:** Checks server health and HTML source capability.

**Response:**
```json
{
  "status": "healthy",
  "screenshot_available": true,
  "screenshot_path": "/path/to/screenshot.png",
  "html_source_available": true,
  "cdp_endpoint": "http://localhost:9222"
}
```

## Usage Examples

### Using curl

```bash
# Get HTML source
curl http://localhost:8080/html-source

# Get browser tabs
curl http://localhost:8080/tabs

# Check health
curl http://localhost:8080/health
```

### Using Python

```python
import requests

# Get HTML source
response = requests.get('http://localhost:8080/html-source')
if response.status_code == 200:
    data = response.json()
    html_content = data['html']
    print(f"Page title: {data['title']}")
    print(f"HTML length: {len(html_content)} characters")
else:
    print(f"Error: {response.json()}")
```

### Using JavaScript

```javascript
// Get HTML source
fetch('http://localhost:8080/html-source')
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      console.log('Page title:', data.title);
      console.log('HTML content:', data.html);
    } else {
      console.error('Error:', data.error);
    }
  });
```

## Testing

### Quick CDP Test
First, verify that Chrome DevTools Protocol is working:

```bash
python3 test_cdp_connection.py
```

### Full API Test
Run the comprehensive test script to verify the HTML source API:

```bash
python3 test_html_api.py
```

## How It Works

1. **Browser Launch**: Uses Playwright to launch Chromium with DevTools Protocol enabled
2. **Chrome DevTools Protocol**: The API connects to Chromium's DevTools Protocol endpoint (port 9222)
3. **Tab Discovery**: It finds the currently active tab (non-DevTools tabs)
4. **WebSocket Connection**: Establishes a WebSocket connection to the specific tab
5. **JavaScript Execution**: Executes `document.documentElement.outerHTML` to get the full HTML
6. **Response**: Returns the HTML content along with metadata

## Troubleshooting

### Browser fails to start with "unknown option --args"
This was fixed by replacing `npx playwright open` with a proper Node.js launcher script (`browser_launcher.js`) that uses Playwright's programmatic API to launch Chromium with the correct DevTools Protocol flags.

### WebSocket 403 Forbidden Error
If you see an error like "Handshake status 403 Forbidden" or "Rejected an incoming WebSocket connection", this is a CORS issue with the Chrome DevTools Protocol. The fix is to add the `--remote-allow-origins=*` flag to the browser launch arguments, which is already included in the `browser_launcher.js` script.

**Error message:**
```
Rejected an incoming WebSocket connection from the http://localhost:9222 origin. 
Use the command line flag --remote-allow-origins=http://localhost:9222 to allow connections from this origin
```

**Solution:** The browser launcher now includes `--remote-allow-origins=*` to allow WebSocket connections from any origin.

### HTML source not available
- Ensure Chromium is running with the new launcher: `node browser_launcher.js`
- Check that port 9222 is not blocked by firewall
- Verify the browser is running and has at least one tab open
- Run `python3 test_cdp_connection.py` to verify CDP connectivity
- Check the Flask server logs for detailed error messages

### Connection timeout
- The browser may be unresponsive
- Try refreshing the page in the browser
- Restart the browser if necessary
- Check browser logs for errors

### Empty or invalid HTML
- The page may still be loading
- Some pages use heavy JavaScript that modifies the DOM after initial load
- The API captures the current state of the DOM, not the original source

## Security Considerations

- The DevTools Protocol provides full access to the browser
- Only expose this API on trusted networks
- Consider adding authentication if needed
- The HTML content may contain sensitive information

## Limitations

- Only works with Chromium-based browsers
- Requires DevTools Protocol to be enabled
- May not capture dynamically generated content that loads after the initial request
- Limited to the currently active tab (first non-DevTools tab found) 
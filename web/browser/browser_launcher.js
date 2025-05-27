const { chromium } = require('playwright');
const path = require('path');

async function launchBrowser() {
  console.log('Launching Chromium with DevTools Protocol enabled and uBlock Origin...');
  
  try {
    // Get the absolute path to the uBlock Origin extension
    // The setup script copies extension to ~/browser-remote/extension/, not inside playwright-project
    const extensionPath = path.resolve(__dirname, '..', 'extension', 'ublock-origin', 'uBlock0.chromium');
    console.log('uBlock Origin extension path:', extensionPath);
    
    // Verify extension exists
    const fs = require('fs');
    const manifestPath = path.join(extensionPath, 'manifest.json');
    if (!fs.existsSync(manifestPath)) {
      throw new Error(`Extension manifest not found at: ${manifestPath}`);
    }
    
    console.log('✓ Extension manifest found');
    
    // Launch browser with extension using official Playwright pattern
    const userDataDir = '';  // Empty string for temporary profile
    const context = await chromium.launchPersistentContext(userDataDir, {
      channel: 'chromium',  // Important: Use chromium channel for extensions
      headless: false,
      args: [
        '--remote-debugging-port=9222',
        '--remote-debugging-address=0.0.0.0',
        '--remote-allow-origins=*',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-features=TranslateUI',
        '--disable-ipc-flooding-protection',
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`
      ],
      viewport: { width: 1024, height: 768 },
      env: {
        DISPLAY: process.env.DISPLAY || ':99'
      }
    });

    console.log('✓ Browser launched successfully with uBlock Origin extension');
    console.log('DevTools Protocol available at: http://localhost:9222');
    console.log('WebSocket connections allowed from all origins');

    // Test extension loading
    console.log('Testing extension loading...');
    const page = await context.newPage();
    
    // Check if extension loaded by looking for background page
    let backgroundPage = context.backgroundPages()[0];
    if (!backgroundPage) {
      console.log('Waiting for background page...');
      backgroundPage = await context.waitForEvent('backgroundpage').catch(() => null);
    }
    
    if (backgroundPage) {
      console.log('✓ uBlock Origin background page detected - extension loaded successfully!');
    } else {
      console.log('⚠ No background page detected, but browser launched');
    }
    
    // Navigate to example.com
    await page.goto('https://example.com');
    console.log('✓ Navigated to https://example.com');
    console.log('Browser is ready for remote control');

    // Keep the browser running
    console.log('Browser will stay open. Press Ctrl+C to close.');
    
    // Handle graceful shutdown
    process.on('SIGINT', async () => {
      console.log('\nShutting down browser...');
      await context.close();
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      console.log('\nShutting down browser...');
      await context.close();
      process.exit(0);
    });

    // Keep the process alive
    await new Promise(() => {});
    
  } catch (error) {
    console.error('Failed to launch browser:', error);
    if (error.message.includes('manifest')) {
      console.log('\nExtension loading failed. Check:');
      console.log('1. Extension path is correct');
      console.log('2. manifest.json exists and is readable');
      console.log('3. Extension is compatible with Chromium');
    }
    process.exit(1);
  }
}

launchBrowser(); 
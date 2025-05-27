const { chromium } = require('playwright');

async function launchBrowser() {
  console.log('Launching Chromium with DevTools Protocol enabled...');
  
  try {
    // Launch browser with DevTools Protocol enabled
    const browser = await chromium.launch({
      headless: false,
      args: [
        '--remote-debugging-port=9222',
        '--remote-debugging-address=0.0.0.0',
        '--remote-allow-origins=*',  // Allow WebSocket connections from any origin
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-features=TranslateUI',
        '--disable-ipc-flooding-protection'
      ],
      env: {
        DISPLAY: process.env.DISPLAY || ':99'
      }
    });

    console.log('Browser launched successfully');
    console.log('DevTools Protocol available at: http://localhost:9222');
    console.log('WebSocket connections allowed from all origins');

    // Create a new page and navigate to example.com
    const context = await browser.newContext({
      viewport: { width: 1024, height: 768 }
    });
    
    const page = await context.newPage();
    await page.goto('https://example.com');
    
    console.log('Navigated to https://example.com');
    console.log('Browser is ready for remote control');

    // Keep the browser running
    console.log('Browser will stay open. Press Ctrl+C to close.');
    
    // Handle graceful shutdown
    process.on('SIGINT', async () => {
      console.log('\nShutting down browser...');
      await browser.close();
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      console.log('\nShutting down browser...');
      await browser.close();
      process.exit(0);
    });

    // Keep the process alive
    await new Promise(() => {});
    
  } catch (error) {
    console.error('Failed to launch browser:', error);
    process.exit(1);
  }
}

launchBrowser(); 
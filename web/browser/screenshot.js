const { chromium } = require('playwright');

async function waitForServer(url, maxRetries = 30) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) return true;
    } catch (e) {
      console.log(`Waiting for server... attempt ${i + 1}/${maxRetries}`);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
  return false;
}

async function takeScreenshot() {
  // Wait for noVNC server to be ready
  const serverReady = await waitForServer('http://localhost:6080/vnc_lite.html');
  if (!serverReady) {
    console.error('Failed to connect to noVNC server');
    process.exit(1);
  }

  const browser = await chromium.launch({
    args: [
      '--window-size=1024,768',
      '--window-position=0,0',
      '--force-device-scale-factor=1',
      '--disable-gpu',
      '--no-sandbox'
    ]
  });
  const context = await browser.newContext({
    viewport: { width: 1024, height: 768 },
    deviceScaleFactor: 1,
    isMobile: false
  });
  const page = await context.newPage();
  
  try {
    await page.goto('http://localhost:6080/vnc_lite.html');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#screen canvas', { timeout: 10000 });

    // Take initial screenshot
    await page.screenshot({ 
      path: process.argv[2],
      fullPage: false,
      omitBackground: false,
      type: 'png',
      scale: 'device'
    });

    // Keep taking screenshots every second
    while (true) {
      await page.screenshot({ 
        path: process.argv[2],
        fullPage: false,
        omitBackground: false,
        type: 'png',
        scale: 'device'
      });
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

  } catch (error) {
    console.error('Screenshot failed:', error);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

takeScreenshot().catch(console.error); 
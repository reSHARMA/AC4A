const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Minimum size to accept a frame (skip dark/blank so we don't overwrite good with bad)
const MIN_FRAME_BYTES = 5000;

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

// Write to .tmp then rename atomically so readers never get a half-written file
function writeScreenshotAtomically(buffer, outputPath) {
  const dir = path.dirname(outputPath);
  const tmpPath = path.join(dir, path.basename(outputPath) + '.tmp');
  fs.writeFileSync(tmpPath, buffer);
  fs.renameSync(tmpPath, outputPath);
}

async function takeScreenshot() {
  const outputPath = process.argv[2];
  if (!outputPath) {
    console.error('Usage: node screenshot.js <output.png>');
    process.exit(1);
  }

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

    // Give noVNC time to paint the first frame
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Loop: capture noVNC canvas every second, write atomically, skip bad/dark frames
    while (true) {
      const buffer = await page.screenshot({
        fullPage: false,
        omitBackground: false,
        type: 'png',
        scale: 'device'
      });
      if (buffer && buffer.length >= MIN_FRAME_BYTES) {
        writeScreenshotAtomically(buffer, outputPath);
      }
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

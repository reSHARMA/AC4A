const { chromium } = require('playwright');
const path = require('path');
const ElementHider = require('./element_hider');

async function launchBrowserWithElementHider() {
  console.log('🎯 Launching browser in ZAPPER MODE...');
  console.log('Point and click elements to hide them forever!');
  
  // Initialize element hider
  const elementHider = new ElementHider(path.join(__dirname, 'element_hiding_config.json'));
  console.log('✓ Element Hider initialized');
  
  // Show current rules count
  const ruleCount = Object.keys(elementHider.config.rules).length;
  if (ruleCount > 0) {
    console.log(`📋 Currently configured for ${ruleCount} domains`);
    elementHider.listRules();
  } else {
    console.log('📋 No element hiding rules configured yet');
  }
  
  try {
    // Get the absolute path to the uBlock Origin Lite extension
    const extensionPath = path.resolve(__dirname, '..', 'extension', 'ublock-origin-lite', 'uBOLite.chromium');
    console.log('uBlock Origin Lite extension path:', extensionPath);
    
    // Verify extension exists
    const fs = require('fs');
    const manifestPath = path.join(extensionPath, 'manifest.json');
    if (!fs.existsSync(manifestPath)) {
      throw new Error(`Extension manifest not found at: ${manifestPath}`);
    }
    
    console.log('✓ Extension manifest found');
    
    // Launch browser with extension
    const userDataDir = '';
    const context = await chromium.launchPersistentContext(userDataDir, {
      channel: 'chromium',
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

    console.log('✓ Browser launched successfully with uBlock Origin Lite');
    console.log('DevTools Protocol available at: http://localhost:9222');

    // Create initial page
    const page = await context.newPage();
    
    // Apply element hiding rules to all new pages
    context.on('page', async (newPage) => {
      console.log(`📄 New page opened: ${newPage.url()}`);
      await elementHider.applyToPage(newPage);
      await enableZapperMode(newPage, elementHider);
    });
    
    // Navigate to example.com initially with zapper mode enabled
    await page.goto('https://example.com');
    await elementHider.applyToPage(page);
    await enableZapperMode(page, elementHider);
    console.log('✓ Navigated to https://example.com with zapper mode active');

    console.log('');
    console.log('🎯 ZAPPER MODE ACTIVE');
    console.log('====================');
    console.log('• Hover over any element to highlight it');
    console.log('• Click to HIDE the element forever');
    console.log('• Rules auto-save to element_hiding_config.json');
    console.log('• Press ESC to temporarily disable zapper');
    console.log('• Navigate to any website and zap away!');
    console.log('• Use Ctrl+C to exit when done');
    console.log('');

    // Keep monitoring for new element selections
    monitorElementSelection(page, elementHider);
    
    // Handle graceful shutdown
    process.on('SIGINT', async () => {
      console.log('\n👋 Shutting down zapper mode...');
      try {
        await context.close();
      } catch (error) {
        console.error('Error closing context:', error);
      }
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      console.log('\n👋 Shutting down zapper mode...');
      try {
        await context.close();
      } catch (error) {
        console.error('Error closing context:', error);
      }
      process.exit(0);
    });

    // Keep the process alive
    await new Promise(() => {});
    
  } catch (error) {
    console.error('Failed to launch browser:', error);
    process.exit(1);
  }
}

// Function to enable zapper mode on a page
async function enableZapperMode(page, elementHider) {
  console.log('🎯 Activating zapper mode on page...');
  
  // Inject zapper script that auto-enables using Playwright's addInitScript
  await page.addInitScript(() => {
    let isZapperActive = true;  // Always active in config mode
    let highlightedElement = null;
    
    function enableZapper() {
      document.body.style.cursor = 'crosshair';
      
      // Add visual indicator
      if (!document.getElementById('zapper-indicator')) {
        const indicator = document.createElement('div');
        indicator.id = 'zapper-indicator';
        indicator.style.cssText = `
          position: fixed;
          top: 10px;
          right: 10px;
          background: #ff4444;
          color: white;
          padding: 8px 12px;
          border-radius: 6px;
          font-family: Arial, sans-serif;
          font-size: 12px;
          font-weight: bold;
          z-index: 999999;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        `;
        indicator.textContent = '🎯 ZAPPER MODE';
        document.body.appendChild(indicator);
      }
      
      document.addEventListener('mouseover', highlightElement, { passive: true });
      document.addEventListener('mouseout', unhighlightElement, { passive: true });
      document.addEventListener('click', zapElement, { capture: true });
      
      // Add escape key listener to temporarily disable
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          toggleZapper();
        }
      });
    }
    
    function toggleZapper() {
      isZapperActive = !isZapperActive;
      const indicator = document.getElementById('zapper-indicator');
      
      if (isZapperActive) {
        document.body.style.cursor = 'crosshair';
        if (indicator) indicator.textContent = '🎯 ZAPPER MODE';
        console.log('🎯 Zapper mode enabled. Click elements to hide them.');
      } else {
        document.body.style.cursor = 'default';
        if (indicator) indicator.textContent = '😴 ZAPPER OFF';
        if (highlightedElement) unhighlightElement();
        console.log('😴 Zapper mode disabled. Press ESC to re-enable.');
      }
    }
    
    function highlightElement(e) {
      if (!isZapperActive) return;
      
      // Don't highlight the zapper indicator
      if (e.target.id === 'zapper-indicator') return;
      
      if (highlightedElement) {
        unhighlightElement();
      }
      
      highlightedElement = e.target;
      highlightedElement.style.outline = '3px solid #ff4444';
      highlightedElement.style.backgroundColor = 'rgba(255, 68, 68, 0.1)';
      highlightedElement.style.transition = 'all 0.1s ease';
    }
    
    function unhighlightElement() {
      if (highlightedElement) {
        highlightedElement.style.outline = '';
        highlightedElement.style.backgroundColor = '';
        highlightedElement.style.transition = '';
        highlightedElement = null;
      }
    }
    
    function zapElement(e) {
      if (!isZapperActive) return;
      if (e.target.id === 'zapper-indicator') return;
      
      e.preventDefault();
      e.stopPropagation();
      
      const element = e.target;
      const selector = generateSelector(element);
      
      // Hide the element immediately with animation
      element.style.transition = 'all 0.3s ease';
      element.style.opacity = '0';
      element.style.transform = 'scale(0.8)';
      
      setTimeout(() => {
        element.style.display = 'none';
      }, 300);
      
      // Send selector to parent for saving
      window.selectedElementSelector = selector;
      window.selectedElementDomain = window.location.hostname;
      
      console.log(`⚡ ZAPPED: ${selector} on ${window.location.hostname}`);
      
      // Show brief confirmation
      showZapConfirmation(selector);
    }
    
    function showZapConfirmation(selector) {
      const confirmation = document.createElement('div');
      confirmation.style.cssText = `
        position: fixed;
        top: 50px;
        right: 10px;
        background: #22c55e;
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-family: Arial, sans-serif;
        font-size: 11px;
        z-index: 999999;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease;
      `;
      confirmation.textContent = `⚡ Zapped: ${selector.substring(0, 30)}...`;
      document.body.appendChild(confirmation);
      
      setTimeout(() => {
        confirmation.remove();
      }, 3000);
    }
    
    function generateSelector(element) {
      // Try to generate a unique selector
      if (element.id) {
        return `#${element.id}`;
      }
      
      if (element.className) {
        const classes = element.className.trim().split(/\s+/).filter(c => c);
        if (classes.length > 0) {
          return `.${classes.join('.')}`;
        }
      }
      
      // Try data attributes
      for (const attr of element.attributes) {
        if (attr.name.startsWith('data-') && attr.value) {
          return `[${attr.name}="${attr.value}"]`;
        }
      }
      
      // Fallback to tag + nth-child
      const parent = element.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(child => 
          child.tagName === element.tagName
        );
        const index = siblings.indexOf(element) + 1;
        return `${element.tagName.toLowerCase()}:nth-of-type(${index})`;
      }
      
      return element.tagName.toLowerCase();
    }
    
    // Auto-enable zapper when script loads
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', enableZapper);
    } else {
      enableZapper();
    }
  });
}

// Function to monitor and auto-save element selections
async function monitorElementSelection(page, elementHider) {
  setInterval(async () => {
    try {
      const result = await page.evaluate(() => {
        if (window.selectedElementSelector && window.selectedElementDomain) {
          const selector = window.selectedElementSelector;
          const domain = window.selectedElementDomain;
          
          // Clear the selection
          window.selectedElementSelector = null;
          window.selectedElementDomain = null;
          
          return { selector, domain };
        }
        return null;
      });
      
      if (result) {
        const { selector, domain } = result;
        const added = elementHider.addRule(domain, selector);
        
        if (added) {
          console.log(`✅ Auto-saved rule: ${domain} -> ${selector}`);
        }
      }
    } catch (error) {
      // Ignore errors during monitoring (e.g., page navigation)
    }
  }, 200); // Check every 200ms for quick response
}

launchBrowserWithElementHider(); 
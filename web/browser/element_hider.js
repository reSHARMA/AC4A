/**
 * Element Hider - Custom element hiding with persistent config
 * Similar to uBlock's zapper mode but with configuration file storage
 */

const fs = require('fs');
const path = require('path');

class ElementHider {
  constructor(configPath = './element_hiding_config.json') {
    this.configPath = configPath;
    this.config = this.loadConfig();
  }

  /**
   * Load configuration from file
   */
  loadConfig() {
    try {
      if (fs.existsSync(this.configPath)) {
        const data = fs.readFileSync(this.configPath, 'utf8');
        return JSON.parse(data);
      }
    } catch (error) {
      console.error('Error loading config:', error);
    }
    
    // Default config structure
    return {
      version: "1.0",
      rules: {
        // "example.com": [
        //   ".cookie-banner",
        //   "div[class*='gdpr']",
        //   "#annoying-popup"
        // ]
      }
    };
  }

  /**
   * Save configuration to file
   */
  saveConfig() {
    try {
      fs.writeFileSync(this.configPath, JSON.stringify(this.config, null, 2));
      console.log(`✓ Configuration saved to ${this.configPath}`);
    } catch (error) {
      console.error('Error saving config:', error);
    }
  }

  /**
   * Add a hiding rule for a specific domain
   */
  addRule(domain, selector) {
    if (!this.config.rules[domain]) {
      this.config.rules[domain] = [];
    }
    
    if (!this.config.rules[domain].includes(selector)) {
      this.config.rules[domain].push(selector);
      console.log(`✓ Added rule: ${domain} -> ${selector}`);
      this.saveConfig();
      return true;
    } else {
      console.log(`Rule already exists: ${domain} -> ${selector}`);
      return false;
    }
  }

  /**
   * Remove a hiding rule
   */
  removeRule(domain, selector) {
    if (this.config.rules[domain]) {
      const index = this.config.rules[domain].indexOf(selector);
      if (index > -1) {
        this.config.rules[domain].splice(index, 1);
        if (this.config.rules[domain].length === 0) {
          delete this.config.rules[domain];
        }
        console.log(`✓ Removed rule: ${domain} -> ${selector}`);
        this.saveConfig();
        return true;
      }
    }
    console.log(`Rule not found: ${domain} -> ${selector}`);
    return false;
  }

  /**
   * Get CSS for a specific domain
   */
  getCSSForDomain(domain) {
    const rules = this.config.rules[domain] || [];
    if (rules.length === 0) return '';
    
    return rules.map(selector => `${selector} { display: none !important; }`).join('\n');
  }

  /**
   * Generate CSS for all domains
   */
  generateAllCSS() {
    let css = '/* Auto-generated element hiding rules */\n';
    
    for (const [domain, selectors] of Object.entries(this.config.rules)) {
      css += `\n/* Rules for ${domain} */\n`;
      for (const selector of selectors) {
        css += `${selector} { display: none !important; }\n`;
      }
    }
    
    return css;
  }

  /**
   * Apply hiding rules to a page context
   */
  async applyToPage(page) {
    try {
      const url = page.url();
      const domain = new URL(url).hostname;
      const css = this.getCSSForDomain(domain);
      
      if (css) {
        await page.addStyleTag({ content: css });
        console.log(`✓ Applied ${this.config.rules[domain].length} hiding rules to ${domain}`);
      }
    } catch (error) {
      console.error('Error applying rules to page:', error);
    }
  }

  /**
   * Interactive element picker (similar to zapper mode)
   */
  async enableElementPicker(page) {
    console.log('🎯 Element picker mode enabled. Click elements to hide them.');
    
    // Inject element picker script
    await page.evaluateOnNewDocument(() => {
      let isPickerActive = false;
      let highlightedElement = null;
      
      function enablePicker() {
        isPickerActive = true;
        document.body.style.cursor = 'crosshair';
        
        document.addEventListener('mouseover', highlightElement);
        document.addEventListener('mouseout', unhighlightElement);
        document.addEventListener('click', selectElement);
        
        // Add escape key listener
        document.addEventListener('keydown', (e) => {
          if (e.key === 'Escape') {
            disablePicker();
          }
        });
        
        console.log('🎯 Element picker active. Hover and click to select elements. Press Esc to exit.');
      }
      
      function disablePicker() {
        isPickerActive = false;
        document.body.style.cursor = 'default';
        
        document.removeEventListener('mouseover', highlightElement);
        document.removeEventListener('mouseout', unhighlightElement);
        document.removeEventListener('click', selectElement);
        
        if (highlightedElement) {
          unhighlightElement();
        }
        
        console.log('Element picker disabled.');
      }
      
      function highlightElement(e) {
        if (!isPickerActive) return;
        
        if (highlightedElement) {
          unhighlightElement();
        }
        
        highlightedElement = e.target;
        highlightedElement.style.outline = '3px solid red';
        highlightedElement.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';
      }
      
      function unhighlightElement() {
        if (highlightedElement) {
          highlightedElement.style.outline = '';
          highlightedElement.style.backgroundColor = '';
          highlightedElement = null;
        }
      }
      
      function selectElement(e) {
        if (!isPickerActive) return;
        
        e.preventDefault();
        e.stopPropagation();
        
        const element = e.target;
        const selector = generateSelector(element);
        
        // Hide the element immediately
        element.style.display = 'none';
        
        // Send selector to parent for saving
        window.selectedElementSelector = selector;
        
        console.log(`Selected element: ${selector}`);
        disablePicker();
      }
      
      function generateSelector(element) {
        // Try to generate a unique selector
        if (element.id) {
          return `#${element.id}`;
        }
        
        if (element.className) {
          const classes = element.className.trim().split(/\s+/);
          return `.${classes.join('.')}`;
        }
        
        // Fallback to tag + nth-child
        const parent = element.parentElement;
        if (parent) {
          const siblings = Array.from(parent.children);
          const index = siblings.indexOf(element) + 1;
          return `${element.tagName.toLowerCase()}:nth-child(${index})`;
        }
        
        return element.tagName.toLowerCase();
      }
      
      // Auto-enable picker when script loads
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', enablePicker);
      } else {
        enablePicker();
      }
    });
  }

  /**
   * List all rules
   */
  listRules() {
    console.log('\n📋 Current hiding rules:');
    console.log('========================');
    
    if (Object.keys(this.config.rules).length === 0) {
      console.log('No rules configured.');
      return;
    }
    
    for (const [domain, selectors] of Object.entries(this.config.rules)) {
      console.log(`\n🌐 ${domain}:`);
      selectors.forEach((selector, index) => {
        console.log(`  ${index + 1}. ${selector}`);
      });
    }
  }
}

module.exports = ElementHider;

// CLI usage if run directly
if (require.main === module) {
  const elementHider = new ElementHider();
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.log('Element Hider - Usage:');
    console.log('  node element_hider.js list                           - List all rules');
    console.log('  node element_hider.js add <domain> <selector>        - Add a rule');
    console.log('  node element_hider.js remove <domain> <selector>     - Remove a rule');
    console.log('  node element_hider.js css <domain>                   - Generate CSS for domain');
    console.log('  node element_hider.js generate                       - Generate all CSS');
    elementHider.listRules();
  } else if (args[0] === 'list') {
    elementHider.listRules();
  } else if (args[0] === 'add' && args.length >= 3) {
    elementHider.addRule(args[1], args[2]);
  } else if (args[0] === 'remove' && args.length >= 3) {
    elementHider.removeRule(args[1], args[2]);
  } else if (args[0] === 'css' && args.length >= 2) {
    console.log(elementHider.getCSSForDomain(args[1]));
  } else if (args[0] === 'generate') {
    console.log(elementHider.generateAllCSS());
  }
} 
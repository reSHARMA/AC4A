import logging
import re
import sys

# ANSI color codes
class Colors:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    RESET = '\033[0m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # Styles
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Custom formatter that adds colors to console output
class ColoredFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: Colors.BLUE + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + Colors.RESET,
        logging.INFO: Colors.GREEN + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + Colors.RESET,
        logging.WARNING: Colors.YELLOW + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + Colors.RESET,
        logging.ERROR: Colors.RED + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + Colors.RESET,
        logging.CRITICAL: Colors.BOLD + Colors.RED + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + Colors.RESET
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Create file handler (without colors)
file_handler = logging.FileHandler("debug.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Create console handler (with colors)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColoredFormatter())

# Don't configure the root logger with basicConfig - this can override existing configurations
# instead, we'll apply our handlers to each logger we create

def get_logger(name):
    """
    Get a logger with the specified name.
    This ensures consistent logging configuration across the application.
    
    Args:
        name (str): Name of the logger, typically __name__ of the module
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Skip configuration if this is the policy_system logger that was already configured
    if name == 'policy_system' and logger.handlers:
        return logger
    
    # Add our handlers if they don't already exist on this logger
    has_file_handler = False
    has_console_handler = False
    
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            has_file_handler = True
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            has_console_handler = True
    
    if not has_file_handler:
        logger.addHandler(file_handler)
    if not has_console_handler:
        logger.addHandler(console_handler)
    
    # Set propagation to False to avoid duplicate logs
    logger.propagate = False
    
    return logger

def set_log_level(level):
    """
    Set the log level for the root logger
    
    Args:
        level: The logging level (e.g., logging.DEBUG, logging.INFO)
    """
    logging.getLogger().setLevel(level)

def clean_ansi_colors(text):
    """
    Remove ANSI color codes from text for log files
    
    Args:
        text (str): Text that may contain ANSI color codes
        
    Returns:
        str: Cleaned text without ANSI codes
    """
    if isinstance(text, str):
        return re.sub(r'\033\[\d+(;\d+)*m', '', text)
    return str(text)

# Legacy debug_print function for backward compatibility
def debug_print(*args, **kwargs):
    """
    Legacy debug_print function for backward compatibility.
    This logs at DEBUG level and attempts to preserve the original behavior.
    
    Args:
        *args: Arguments to log
        **kwargs: Keyword arguments
    """
    logger = logging.getLogger('debug_print')
    
    # Add our handlers if they don't already exist on this logger
    has_file_handler = False
    has_console_handler = False
    
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            has_file_handler = True
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            has_console_handler = True
    
    if not has_file_handler:
        logger.addHandler(file_handler)
    if not has_console_handler:
        logger.addHandler(console_handler)
    
    # Set propagation to False to avoid duplicate logs
    logger.propagate = False
    
    # Clean ANSI codes from args for log file
    clean_args = [clean_ansi_colors(arg) for arg in args]
    message = " ".join(str(arg) for arg in clean_args)
    
    # Log at DEBUG level
    logger.debug(message)
    
    # If DEBUG flag was True in the original, also print to console
    # This preserves the original behavior where debug_print
    # would write to debug.log file and also print to console if DEBUG=True
    if kwargs.get('force_print', False):
        print(*args)

def migrate_to_logger_helper(file_path):
    """
    Helper function to migrate a file from using debug_print to using proper logger.
    
    This function analyzes a file and provides recommendations for migrating from
    debug_print usage to proper logger usage.
    
    Args:
        file_path (str): Path to the file to analyze
        
    Returns:
        dict: Dictionary with migration recommendations
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if the file imports debug_print
        imports_debug_print = "from config import debug_print" in content
        
        # Check how many times debug_print is used
        debug_print_count = content.count("debug_print(")
        
        # Find all debug_print calls
        import re
        debug_print_calls = re.findall(r'debug_print\((.*?)\)', content, re.DOTALL)
        
        # Analyze if the file already imports logging
        has_logging = "import logging" in content
        
        # Generate recommended logger setup for this file
        logger_setup = "from src.utils.logger import get_logger\n\n# Set up logger\nlogger = get_logger(__name__)\n"
        
        # Generate example conversions
        example_conversions = []
        for call in debug_print_calls[:5]:  # Limit to first 5 examples
            # Determine log level based on content
            level = "debug"
            if "error" in call.lower() or "exception" in call.lower() or "fail" in call.lower():
                level = "error"
            elif "warn" in call.lower():
                level = "warning"
            
            # Format the conversion example
            original = f"debug_print({call})"
            converted = f"logger.{level}({call})"
            example_conversions.append({"original": original, "converted": converted})
        
        return {
            "file_path": file_path,
            "imports_debug_print": imports_debug_print,
            "debug_print_count": debug_print_count,
            "has_logging": has_logging,
            "recommended_setup": logger_setup,
            "example_conversions": example_conversions
        }
    except Exception as e:
        return {
            "file_path": file_path,
            "error": str(e)
        } 
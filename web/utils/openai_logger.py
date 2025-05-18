import logging
import json
from datetime import datetime

class OpenAILogHandler(logging.Handler):
    """Custom handler for OpenAI API logging"""
    
    def emit(self, record):
        try:
            # Get the log message
            msg = self.format(record)
            
            # Add timestamp
            timestamp = datetime.now().isoformat()
            
            # Create a structured log entry
            log_entry = {
                'timestamp': timestamp,
                'level': record.levelname,
                'message': msg,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            # If there's extra data in the record, add it
            if hasattr(record, 'openai_data'):
                log_entry['openai_data'] = record.openai_data
            
            # Write to a dedicated OpenAI log file
            with open('openai_calls.log', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            self.handleError(record)

def setup_openai_logging():
    """Set up OpenAI-specific logging configuration"""
    # Create the OpenAI logger
    openai_logger = logging.getLogger('OpenAI')
    openai_logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    for handler in openai_logger.handlers[:]:
        openai_logger.removeHandler(handler)
    
    # Create and add our custom handler
    handler = OpenAILogHandler()
    handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to logger
    openai_logger.addHandler(handler)
    
    return openai_logger 
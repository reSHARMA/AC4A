import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient, AzureOpenAIChatCompletionClient

# Set up logging
logger = logging.getLogger(__name__)

class LoggingModelClient(ChatCompletionClient):
    """A wrapper around ChatCompletionClient that logs all API calls"""
    
    def __init__(self, model_client: ChatCompletionClient):
        self.model_client = model_client
        self.log_file = 'autogen_api_calls.log'
        self.log_entries = []  # Store log entries in memory
        
        # Clear the log file when initializing
        try:
            with open(self.log_file, 'w') as f:
                f.write('')  # Clear the file
            logger.info(f"Cleared existing log file: {self.log_file}")
        except Exception as e:
            logger.error(f"Error clearing log file: {str(e)}")
    
    def _serialize_tool_schema(self, tool: Any) -> Dict[str, Any]:
        """Convert a tool schema to a serializable dictionary with better formatting"""
        # Handle FunctionTool objects
        if hasattr(tool, 'function'):
            function = tool.function
            # Extract the full function schema
            schema = {
                'type': getattr(tool, 'type', 'function'),
                'function': {
                    'name': getattr(function, 'name', str(function)),
                    'description': getattr(function, 'description', ''),
                    'parameters': {}
                }
            }
            
            # Extract parameters if available
            if hasattr(function, 'parameters'):
                params = function.parameters
                if hasattr(params, 'model_dump'):
                    schema['function']['parameters'] = params.model_dump()
                elif hasattr(params, 'dict'):
                    schema['function']['parameters'] = params.dict()
                elif isinstance(params, dict):
                    schema['function']['parameters'] = params
                else:
                    schema['function']['parameters'] = {
                        'type': 'object',
                        'properties': {},
                        'required': []
                    }
                    
                # Ensure properties and required fields are properly formatted
                if 'properties' in schema['function']['parameters']:
                    schema['function']['parameters']['properties'] = {
                        k: v for k, v in schema['function']['parameters']['properties'].items()
                    }
                if 'required' in schema['function']['parameters']:
                    schema['function']['parameters']['required'] = list(schema['function']['parameters']['required'])
            
            return schema
        
        # Handle dictionary tools
        if isinstance(tool, dict):
            serialized = tool.copy()
            if 'function' in serialized:
                function = serialized['function']
                if isinstance(function, dict):
                    if 'parameters' in function:
                        if isinstance(function['parameters'], dict):
                            if 'properties' in function['parameters']:
                                function['parameters']['properties'] = {
                                    k: v for k, v in function['parameters']['properties'].items()
                                }
                            if 'required' in function['parameters']:
                                function['parameters']['required'] = list(function['parameters']['required'])
                    serialized['function'] = function
            return serialized
        
        # Fallback for other types
        return {'type': 'function', 'function': str(tool)}

    def _serialize_message(self, message: Any) -> Dict[str, Any]:
        """Convert a message object to a serializable dictionary"""
        if isinstance(message, dict):
            return message
            
        # Create base message dict
        message_dict = {
            'role': getattr(message, 'role', str(message)),
            'content': getattr(message, 'content', str(message))
        }
        
        # Handle function calls
        if hasattr(message, 'function_call'):
            function_call = message.function_call
            if function_call:
                message_dict['function_call'] = {
                    'name': getattr(function_call, 'name', str(function_call)),
                    'arguments': getattr(function_call, 'arguments', str(function_call))
                }
        
        # Handle tool calls
        if hasattr(message, 'tool_calls'):
            tool_calls = message.tool_calls
            if tool_calls:
                message_dict['tool_calls'] = [
                    {
                        'id': getattr(tool_call, 'id', str(tool_call)),
                        'type': getattr(tool_call, 'type', 'function'),
                        'function': {
                            'name': getattr(tool_call.function, 'name', str(tool_call.function)),
                            'arguments': getattr(tool_call.function, 'arguments', str(tool_call.function))
                        }
                    }
                    for tool_call in tool_calls
                ]
        
        return message_dict
    
    def _serialize_messages(self, messages: List[Any]) -> List[Dict[str, Any]]:
        """Convert a list of message objects to serializable dictionaries"""
        return [self._serialize_message(msg) for msg in messages]

    def _serialize_response(self, response: Any) -> Dict[str, Any]:
        """Convert a response object to a serializable dictionary"""
        if response is None:
            return {}
            
        # Handle different response types
        if hasattr(response, 'choices'):
            # Standard OpenAI response format
            message = response.choices[0].message
            return {
                'content': getattr(message, 'content', str(message)),
                'finish_reason': response.choices[0].finish_reason,
                'function_call': self._serialize_message(message).get('function_call'),
                'tool_calls': self._serialize_message(message).get('tool_calls')
            }
        else:
            # Handle other response types
            return {
                'content': str(response),
                'message': self._serialize_message(response.message) if hasattr(response, 'message') else None
            }
        
    def _serialize_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Convert kwargs to serializable dictionary"""
        serializable = {}
        for key, value in kwargs.items():
            # Skip non-serializable objects
            if key in ['cancellation_token']:
                continue
                
            # Handle tools
            if key == 'tools':
                serializable[key] = []
                for tool in value:
                    try:
                        logger.debug(f"Processing tool: {type(tool)}")
                        if hasattr(tool, 'function'):
                            function = tool.function
                            logger.debug(f"Function details - name: {getattr(function, 'name', '')}, description: {getattr(function, 'description', '')}")
                            
                            # Get the function schema
                            if hasattr(function, 'schema'):
                                schema = function.schema
                                logger.debug(f"Found schema: {schema}")
                                tool_schema = {
                                    'type': getattr(tool, 'type', 'function'),
                                    'function': schema
                                }
                            else:
                                # Try to construct schema from attributes
                                tool_schema = {
                                    'type': getattr(tool, 'type', 'function'),
                                    'function': {
                                        'name': getattr(function, 'name', ''),
                                        'description': getattr(function, 'description', ''),
                                        'parameters': {}
                                    }
                                }
                                
                                # Try to get parameters
                                if hasattr(function, 'parameters'):
                                    params = function.parameters
                                    logger.debug(f"Parameters type: {type(params)}")
                                    
                                    # Try different methods to get parameters
                                    if hasattr(params, 'model_dump'):
                                        tool_schema['function']['parameters'] = params.model_dump()
                                    elif hasattr(params, 'dict'):
                                        tool_schema['function']['parameters'] = params.dict()
                                    elif isinstance(params, dict):
                                        tool_schema['function']['parameters'] = params
                                    else:
                                        # Try to get parameters as attributes
                                        tool_schema['function']['parameters'] = {
                                            'type': 'object',
                                            'properties': {},
                                            'required': []
                                        }
                                        
                                        # Try to get properties
                                        if hasattr(params, 'properties'):
                                            props = params.properties
                                            if hasattr(props, 'model_dump'):
                                                tool_schema['function']['parameters']['properties'] = props.model_dump()
                                            elif hasattr(props, 'dict'):
                                                tool_schema['function']['parameters']['properties'] = props.dict()
                                            elif isinstance(props, dict):
                                                tool_schema['function']['parameters']['properties'] = props
                                        
                                        # Try to get required fields
                                        if hasattr(params, 'required'):
                                            req = params.required
                                            if isinstance(req, (list, tuple)):
                                                tool_schema['function']['parameters']['required'] = list(req)
                                            elif hasattr(req, 'model_dump'):
                                                tool_schema['function']['parameters']['required'] = req.model_dump()
                                            elif hasattr(req, 'dict'):
                                                tool_schema['function']['parameters']['required'] = req.dict()
                            
                            logger.debug(f"Final tool schema: {tool_schema}")
                            serializable[key].append(tool_schema)
                        else:
                            # Try to get schema directly
                            if hasattr(tool, 'schema'):
                                tool_schema = {
                                    'type': getattr(tool, 'type', 'function'),
                                    'function': tool.schema
                                }
                                serializable[key].append(tool_schema)
                            else:
                                # Fallback for non-FunctionTool objects
                                serializable[key].append(self._serialize_tool_schema(tool))
                    except Exception as e:
                        logger.error(f"Error serializing tool: {str(e)}", exc_info=True)
                        serializable[key].append({'type': 'function', 'function': str(tool)})
            
            # Handle functions
            elif key == 'functions':
                serializable[key] = [self._serialize_tool_schema(func) for func in value]
            
            # Handle other values
            else:
                try:
                    json.dumps(value)  # Test if value is JSON serializable
                    serializable[key] = value
                except (TypeError, ValueError):
                    serializable[key] = str(value)
                    
        return serializable
        
    def _log_api_call(self, request: Dict[str, Any], response: Any = None, error: Exception = None):
        """Log an API call to the log file"""
        try:
            timestamp = datetime.now().isoformat()
            
            # Create a serializable copy of the request
            serializable_request = {
                'model': request.get('model', 'unknown'),
                'messages': self._serialize_messages(request.get('messages', [])),
                'temperature': request.get('temperature', 1.0),
                'max_tokens': request.get('max_tokens', None),
                'stream': request.get('stream', False)
            }
            
            # Add serializable kwargs
            serializable_request.update(self._serialize_kwargs(request))
            
            log_entry = {
                'timestamp': timestamp,
                'request': serializable_request
            }
            
            if response:
                log_entry['response'] = self._serialize_response(response)
                
            if error:
                log_entry['error'] = str(error)
            
            # Add to in-memory log entries
            self.log_entries.append(log_entry)
            
            # Write all entries to file
            with open(self.log_file, 'w') as f:
                for entry in self.log_entries:
                    f.write(json.dumps(entry, indent=2) + '\n')
                    
        except Exception as e:
            logger.error(f"Error logging API call: {str(e)}")
            
    async def create(self, messages: List[Dict[str, str]], **kwargs):
        """Override the create method to add logging"""
        try:
            # Prepare request data for logging
            request_data = {'messages': messages, **kwargs}
            
            # Log the request
            self._log_api_call(request_data)
            
            # Make the actual API call
            response = await self.model_client.create(messages=messages, **kwargs)
            
            # Log the response
            self._log_api_call(request_data, response)
            
            return response
        except Exception as e:
            # Log any errors
            self._log_api_call({'messages': messages, **kwargs}, error=e)
            raise

    # Implement required abstract methods
    @property
    def model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return self.model_client.model_info

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Get model capabilities"""
        return self.model_client.capabilities

    async def create_stream(self, messages: List[Dict[str, str]], **kwargs):
        """Create a streaming response"""
        try:
            # Prepare request data for logging
            request_data = {'messages': messages, **kwargs}
            
            # Log the request
            self._log_api_call(request_data)
            
            # Make the actual API call
            async for response in self.model_client.create_stream(messages=messages, **kwargs):
                # Log each chunk of the response
                self._log_api_call(request_data, response)
                yield response
        except Exception as e:
            # Log any errors
            self._log_api_call(request_data, error=e)
            raise

    def count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in messages"""
        return self.model_client.count_tokens(messages)

    @property
    def remaining_tokens(self) -> int:
        """Get remaining tokens"""
        return self.model_client.remaining_tokens

    @property
    def total_usage(self) -> Dict[str, int]:
        """Get total token usage"""
        return self.model_client.total_usage

    @property
    def actual_usage(self) -> Dict[str, int]:
        """Get actual token usage"""
        return self.model_client.actual_usage 
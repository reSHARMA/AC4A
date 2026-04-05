import os
import re
import logging
from dotenv import load_dotenv
from autogen_core.models import ChatCompletionClient, ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, ChainedTokenCredential, AzureCliCredential, get_bearer_token_provider
from .logging_model_client import LoggingModelClient

# Set up logging
logger = logging.getLogger(__name__)

def setup_model_client():
    """Set up the model client for autogen"""
    logger.info("Setting up model client")
    # Look for .env in the web/ directory (sibling of this agent/ package)
    _env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(_env_path)
    load_dotenv()  # also try cwd as fallback
    
    # Try OpenAI configuration first
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        logger.info("Using OpenAI configuration")
        model_name = f"{os.getenv('CHAT_MODEL')}-{os.getenv('CHAT_MODEL_DATE')}"
        # model_info is required for custom/newer model names not in autogen's built-in list
        model_info = {
            "vision": True,
            "function_calling": True,
            "json_output": True,
            "family": ModelFamily.UNKNOWN,
        }
        base_client = OpenAIChatCompletionClient(
            model=model_name,
            api_key=openai_api_key,
            model_info=model_info,
        )
    else:
        # Fallback to Azure OpenAI
        logger.info("Using Azure OpenAI configuration")
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION')
        scope = os.getenv('AZURE_OPENAI_TOKEN_SCOPES')
        deployment = f"{os.getenv('CHAT_MODEL')}_{os.getenv('CHAT_MODEL_DATE')}"
        
        if not all([endpoint, api_version, scope, deployment]):
            logger.error("Missing required Azure OpenAI configuration")
            logger.error(f"endpoint: {endpoint}")
            logger.error(f"api_version: {api_version}")
            logger.error(f"scope: {scope}")
            logger.error(f"deployment: {deployment}")
            raise ValueError("Missing required Azure OpenAI configuration")
        
        credential = get_bearer_token_provider(ChainedTokenCredential(
            AzureCliCredential(),
            DefaultAzureCredential(
                exclude_cli_credential=True,
                exclude_environment_credential=True,
                exclude_shared_token_cache_credential=True,
                exclude_developer_cli_credential=True,
                exclude_powershell_credential=True,
                exclude_interactive_browser_credential=True,
                exclude_visual_studio_code_credentials=True,
                managed_identity_client_id=os.environ.get("DEFAULT_IDENTITY_CLIENT_ID"),
            )
        ), scope)

        # Define model info for the custom model
        model_info = {
            "context_length": 128000,
            "max_tokens": 4096,
            "input_cost_per_token": 0.0,
            "output_cost_per_token": 0.0,
            "model_type": "chat",
            "supports_functions": True,
            "supports_vision": False,
            "supports_streaming": True,
            "vision": False,
            "json_output": True,
            "function_calling": True
        }

        # Create the Azure OpenAI client using autogen's AzureOpenAIChatCompletionClient
        base_client = AzureOpenAIChatCompletionClient(
            model=deployment,
            azure_endpoint=endpoint,
            api_version=api_version,
            azure_ad_token_provider=credential,
            model_info=model_info
        )
    
    # Create the logging wrapper
    logging_client = LoggingModelClient(base_client)
    
    # Try to set up autogen configuration if available
    try:
        import importlib.util
        if importlib.util.find_spec("autogen_core") is not None:
            from autogen_core import config_list
            if config_list and len(config_list) > 0:
                config_list[0]["model"] = logging_client
                logger.info("Successfully configured autogen with logging client")
        else:
            logger.info("autogen_core module not found, skipping autogen configuration")
    except Exception as e:
        logger.warning(f"Could not configure autogen: {str(e)}")
    
    return logging_client 
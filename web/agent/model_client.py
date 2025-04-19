import os
import re
import logging
from dotenv import load_dotenv
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, ChainedTokenCredential, AzureCliCredential, get_bearer_token_provider

# Set up logging
logger = logging.getLogger(__name__)

def setup_model_client():
    """Set up the model client for autogen"""
    logger.info("Setting up model client")
    load_dotenv()
    
    # Try OpenAI configuration first
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        logger.info("Using OpenAI configuration")
        return OpenAIChatCompletionClient(
            model="gpt-4",
            api_key=openai_api_key
        )
    else:
        # Fallback to Azure OpenAI
        logger.info("Using Azure OpenAI configuration")
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION')
        scope = os.getenv('AZURE_OPENAI_TOKEN_SCOPES')
        deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')
        
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
        return AzureOpenAIChatCompletionClient(
            model=deployment,
            azure_endpoint=endpoint,
            api_version=api_version,
            azure_ad_token_provider=credential,
            model_info=model_info
        ) 
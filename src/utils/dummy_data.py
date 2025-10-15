import os
from openai import OpenAI, AzureOpenAI
from azure.identity import AzureCliCredential, DefaultAzureCredential, get_bearer_token_provider, ChainedTokenCredential
from dotenv import load_dotenv
from config import debug_print
import re
import logging as logger
from web.utils.openai_logger import setup_openai_logging
logger = logger.getLogger(__name__)
# Load environment variables from .env file
load_dotenv()

# Set up OpenAI logger
openai_logger = setup_openai_logging()

history = ""

def call_openai_api(system: str, prompt: str, mode: str) -> str:
    """
    Calls the OpenAI API with the given prompt and returns the response.
    If OpenAI API key is unavailable, falls back to Azure OpenAI client.

    Args:
        system (str): The system prompt/instructions
        prompt (str): The prompt to send to the OpenAI API
        mode (str): The mode to use ("perm", "app", or "computer-use")

    Returns:
        str: The response from the OpenAI API.
    """
    try:
        # Try OpenAI client first
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key:
            client = OpenAI(api_key=openai_api_key)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            
            # Check if prompt contains image data
            if isinstance(prompt, dict) and "image" in prompt:
                # Handle image input
                content = [
                    {"type": "text", "text": prompt.get("text", "")},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": prompt["image"]
                        }
                    }
                ]
            else:
                # Handle text-only input
                content = prompt

            messages.append({
                "role": "user",
                "content": content
            })

            # Log the API call
            openai_logger.debug("Making OpenAI API call", extra={
                'openai_data': {
                    'messages': messages,
                    'temperature': 1
                }
            })
            model = "gpt-4o-2024-11-20" 
            if mode == "perm":
                model = f"{os.getenv('PERM_MODEL')}-{os.getenv('PERM_MODEL_DATE')}"
            elif mode == "app":
                model = f"{os.getenv('APP_BACKEND_MODEL')}-{os.getenv('APP_BACKEND_MODEL_DATE')}"
            elif mode == "computer-use":
                model = f"{os.getenv('PERM_MODEL')}-{os.getenv('PERM_MODEL_DATE')}"

            completion = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=1,
            )
            return completion.choices[0].message.content
        else:
            # Fallback to Azure OpenAI client
            logger.info("OpenAI API key not found, using Azure OpenAI client")
            
            # Get the scope from the environment variable
            scope = os.getenv('AZURE_OPENAI_TOKEN_SCOPES')
            
            # Create the credential chain
            credential = get_bearer_token_provider(ChainedTokenCredential(
                AzureCliCredential(),
                DefaultAzureCredential(
                    managed_identity_client_id=os.environ.get("DEFAULT_IDENTITY_CLIENT_ID"),
                )
            ), scope)

            api_version = os.getenv('AZURE_OPENAI_API_VERSION')
            model_name = os.getenv('AZURE_OPENAI_DEPLOYMENT')
            endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            if mode == "perm":
                model_name = f"{os.getenv('PERM_MODEL')}_{os.getenv('PERM_MODEL_DATE')}"
            elif mode == "app":
                model_name = f"{os.getenv('APP_BACKEND_MODEL')}_{os.getenv('APP_BACKEND_MODEL_DATE')}"
            elif mode == "computer-use":
                model_name = f"{os.getenv('CHAT_MODEL')}_{os.getenv('CHAT_MODEL_DATE')}"

            client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=credential,
                api_version=api_version,
            )
            
            # Prepare messages with support for both text and image
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            
            # Check if prompt contains image data
            if isinstance(prompt, dict) and "image" in prompt:
                # Handle image input
                content = [
                    {"type": "text", "text": prompt.get("text", "")},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": prompt["image"]
                        }
                    }
                ]
            else:
                # Handle text-only input
                content = prompt

            messages.append({
                "role": "user",
                "content": content
            })
            
            # Log the Azure OpenAI API call
            openai_logger.debug("Making Azure OpenAI API call", extra={
                'openai_data': {
                    'model': model_name,
                    'messages': messages,
                    'temperature': 1,
                    'endpoint': endpoint,
                    'api_version': api_version
                }
            })
            
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=1,
            )
            
            # Log the Azure OpenAI response
            openai_logger.debug("Received Azure OpenAI API response", extra={
                'openai_data': {
                    'response': completion.choices[0].message.content,
                    'usage': {
                        'prompt_tokens': getattr(completion.usage, 'prompt_tokens', 0),
                        'completion_tokens': getattr(completion.usage, 'completion_tokens', 0),
                        'total_tokens': getattr(completion.usage, 'total_tokens', 0)
                    },
                    'finish_reason': completion.choices[0].finish_reason
                }
            })
            
            return completion.choices[0].message.content
    except Exception as e:
        # Log any errors
        openai_logger.error(f"Error in OpenAI API call: {str(e)}", exc_info=True)
        logger.error(f"An error occurred while calling the API: {e}")
        return ""

def generate_dummy_data(api_endpoint: str, **kwargs) -> dict:
    """
    Generates dummy data for a given API endpoint using OpenAI gpt-4-mini.

    Args:
        api_endpoint (str): The API endpoint description.
        **kwargs: Additional arguments that describe the API call.

    Returns:
        dict: A dictionary representing the dummy data in JSON format.
    """
    global history  # Declare history as global to modify it

    # Construct the prompt for the LLM
    prompt = f"""
    Generate dummy response for the API endpoint '{api_endpoint}' with the following parameters: {kwargs}
    Only output the response and nothing else
    Do not enclose the data in code blocks
    Keep the response grounded in the parameters provided to you.
    If you are requested sensitive data, example, passwords, credit card numbers, etc.,generate diverse data that is not real, like sometimes amex card, sometimes visa card, etc.
    Try to generate affirmative data, example, if the data request is for checking availability, return data representing availability.

    The following is the summary of the data you have generated in the previous steps, be consistent with the data you have generated:
    {history}
"""

    # Log the API endpoint being used to generate dummy data. Use proper formatting to avoid logging errors.
    logger.info("Dummy data for API endpoint: %s", api_endpoint)
    # Use the separate function to call the OpenAI API
    dummy_data = call_openai_api("", prompt, "app")
    
    summary_prompt = f"""You will be given a json output from an API endpoint {api_endpoint}. Generate a summary of the data returned by the API endpoint '{api_endpoint}' such that it can be presented to the user. 
Keep the summary concise and informative."""   
    summary = call_openai_api(summary_prompt, dummy_data, "app")

    history += summary + "\n" 

    logger.info(f"\033[1;35;40m{summary}\033[0m")
    # Use json.loads to safely parse the JSON string
    return summary
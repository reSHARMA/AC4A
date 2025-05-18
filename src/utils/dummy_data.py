import os
from openai import OpenAI, AzureOpenAI
from azure.identity import AzureCliCredential, DefaultAzureCredential, get_bearer_token_provider, ChainedTokenCredential
from dotenv import load_dotenv
from config import debug_print
import re
import logging
from web.utils.openai_logger import setup_openai_logging

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI logger
openai_logger = setup_openai_logging()

history = ""

def call_openai_api(system: str, prompt: str) -> str:
    """
    Calls the OpenAI API with the given prompt and returns the response.
    If OpenAI API key is unavailable, falls back to Azure OpenAI client.

    Args:
        prompt (str): The prompt to send to the OpenAI API.

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
            messages.append({"role": "user", "content": prompt})
            
            # Log the API call
            openai_logger.debug("Making OpenAI API call", extra={
                'openai_data': {
                    'model': "gpt-4o-2024-11-20",
                    'messages': messages,
                    'temperature': 1
                }
            })
            
            completion = client.chat.completions.create(
                messages=messages,
                model="gpt-4o-2024-11-20",
                temperature=1,
            )
            
            # Log the response
            openai_logger.debug("Received OpenAI API response", extra={
                'openai_data': {
                    'response': completion.choices[0].message.content,
                    'usage': completion.usage._asdict() if hasattr(completion, 'usage') else None
                }
            })
            
            return completion.choices[0].message.content
        else:
            # Fallback to Azure OpenAI client
            debug_print("OpenAI API key not found, using Azure OpenAI client")
            
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

            client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=credential,
                api_version=api_version,
            )
            
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
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
        debug_print(f"An error occurred while calling the API: {e}")
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

    debug_print("Dummy data for API endpoint:", api_endpoint)
    # Use the separate function to call the OpenAI API
    dummy_data = call_openai_api("", prompt)
    
    summary_prompt = f"""You will be given a json output from an API endpoint {api_endpoint}. Generate a summary of the data returned by the API endpoint '{api_endpoint}' such that it can be presented to the user. 
Keep the summary concise and informative."""   
    summary = call_openai_api(summary_prompt, dummy_data)

    history += summary + "\n" 

    print(f"\033[1;35;40m{summary}\033[0m")
    # Use json.loads to safely parse the JSON string
    return summary
import os
from openai import OpenAI
from config import debug_print

history = ""

def call_openai_api(system: str, prompt: str) -> str:
    """
    Calls the OpenAI API with the given prompt and returns the response.

    Args:
        prompt (str): The prompt to send to the OpenAI API.

    Returns:
        str: The response from the OpenAI API.
    """
    try:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        client = OpenAI(api_key=openai_api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        completion = client.chat.completions.create(
            messages=messages,
            model="gpt-4o",
            temperature=1,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print("An error occurred while calling the OpenAI API:", e)
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
    If a booking is coming from expedia book_something, mark the payment as pending and if it is coming from expedia pay_for_itenary then mark the payment as completed.
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
    return dummy_data
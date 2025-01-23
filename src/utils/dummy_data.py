import os
from openai import OpenAI

def generate_dummy_data(api_endpoint: str, **kwargs) -> dict:
    """
    Generates dummy data for a given API endpoint using OpenAI gpt-4-mini.

    Args:
        api_endpoint (str): The API endpoint description.
        **kwargs: Additional arguments that describe the API call.

    Returns:
        dict: A dictionary representing the dummy data in JSON format.
    """
    # Construct the prompt for the LLM
    prompt = f"""
    Generate dummy response for the API endpoint '{api_endpoint}' with the following parameters: {kwargs}
    Only output the response and nothing else
    Do not enclose the data in code blocks
    Keep the response grounded in the parameters provided to you.
    Try to generate affirmative data, example, if the data request is for checking availability, return data representing availability.
"""

    # Call the OpenAI API to generate the dummy data
    try:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        client = OpenAI(api_key=openai_api_key)
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o",
            temperature=1,
        )
        dummy_data = completion.choices[0].message.content
    except:
        print("An error occurred while generating dummy data:", e)
        
        # Use json.loads to safely parse the JSON string
    return dummy_data
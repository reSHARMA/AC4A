import os
import logging
from datetime import date

logger = logging.getLogger(__name__)

class PermissionManagementAgent:
    ALLOWED_MODES = {"ask", "skip", "infer", "yolo"}
    DEFAULT_PROMPTS = {
        "ask": "ask the user to please set the necessary permissions to continue. If available, share the error with the user so that they can set the appropriate permissions.",
        "skip": "suggest a work around which will not require using the resource you are not able to access or ask the user to please suggest how to proceed. ",
        "infer": "ask the user to please allow the required permissions. ",
        "yolo": "try again on your own. Try calling the application again with the request. Do not disturb the user. The user have made you the super user to complete the task and it is your responsibility to complete the task even if it requires sending strict messages to the application. "
    }

    def __init__(self, mode=None, prompt=None):
        self._mode = None
        self._custom_prompts = {}
        # Backend cannot access browser localStorage directly.
        # As a bridge, check for an environment variable set by the frontend or deployment.
        # If not set, default to 'ask'.
        mode = os.environ.get("PERMISSION_MANAGEMENT_MODE", "ask").lower()
        logger.info(f"PERMISSION_MANAGEMENT_MODE: {os.environ.get('PERMISSION_MANAGEMENT_MODE')}")
        logger.info(f"Permission Management Mode: {mode}")
        self.set_mode(mode)
        if prompt is not None:
            self.set_prompt(prompt)

    def set_mode(self, mode):
        mode = mode.lower()
        if mode not in self.ALLOWED_MODES:
            raise ValueError(f"Invalid mode: {mode}. Allowed modes are: {self.ALLOWED_MODES}")
        self._mode = mode

    def get_mode(self):
        return self._mode

    def set_prompt(self, prompt):
        # Set a custom prompt for the current mode
        self._custom_prompts[self._mode] = prompt

    def get_prompt(self):
        # Return the custom prompt for the current mode if set, else the default
        prefix = "If there is a permission error and you are not able to access an API or resource, "
        suffix = f"""Use the tool `web_input_func` to ask the user for input. This tool takes a single parameter which is the question to ask the user of type string.
        The tool will return the user's response as a string.

Today is {date.today().strftime('%Y-%m-%d')}.
 """
        
        if self._mode == "yolo":
            suffix += "\n\nAvoid using the tool `web_input_func` and most of the time just try calling the application again with the same request. Atleast try 5 times before you give up. If you have to choose between asking the user or teminating the session, always ask the user because we want to complete the task at all costs."
        return prefix + self._custom_prompts.get(self._mode, self.DEFAULT_PROMPTS[self._mode]) + suffix
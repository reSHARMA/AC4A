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

    def __init__(self, mode=None, prompt=None, skip_input_tool_description=False, skip_permission_suffix=False):
        self._mode = None
        self._custom_prompts = {}
        self.skip_input_tool_description = skip_input_tool_description
        self.skip_permission_suffix = skip_permission_suffix
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
        suffix = f"Today is {date.today().strftime('%Y-%m-%d')}.\n"
        if not self.skip_input_tool_description:
            suffix += f"""Use the tool `get_user_input` to ask the user for input, comfirmation if there are choices to be made, etc. This tool takes a single string argument that is the message to relay to the user. It will return the user's response as a string.

You will be given a task to complete. You must complete the task using the tools provided to you. 
Ask for more information if needed but never generate an empty tool call or an empty message. 
You must always try to use the tool to complete the task. If not possible you must output a message preferably using the `get_user_input` tool else output a text message.
Return "done" when your work is completed.
 """
        if self.skip_permission_suffix: 
            return suffix

        if self._mode == "yolo":
            suffix += "\n\nYou are working in an autonomous mode. Only ask the user or use `get_user_input` when you are not able to complete the task or if there is a choice to be made. You must first try calling the application again with the same request before asking the user. Atleast try 5 times before you give up. If you have to choose between asking the user or teminating the session, always ask the user because we want to complete the task at all costs."
        return prefix + self._custom_prompts.get(self._mode, self.DEFAULT_PROMPTS[self._mode]) + suffix
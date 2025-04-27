class PermissionManagementAgent:
    ALLOWED_MODES = {"ask", "skip", "infer", "yolo"}
    DEFAULT_PROMPTS = {
        "ask": "ask the user to please set the necessary permissions to continue.",
        "skip": "ask the user to please suggest how shall I proceed.",
        "infer": "ask the user to please allow the required permissions.",
        "yolo": "tell the user that I am automatically approving the required permissions."
    }

    def __init__(self, mode="ask", prompt=None):
        self._mode = None
        self._custom_prompts = {}
        self.set_mode(mode)
        if prompt is not None:
            self.set_prompt(prompt)

    def set_mode(self, mode):
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
        suffix = "You can ask the user by calling the tool `web_input_func` if available or returning User: message. "
        return prefix + self._custom_prompts.get(self._mode, self.DEFAULT_PROMPTS[self._mode]) + suffix
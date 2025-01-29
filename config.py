import re

DEBUG = False
WILDCARD = False

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)
    else:
        with open("debug.log", "a") as log_file:
            # Remove any ANSI color codes from the output
            clean_args = [re.sub(r'\033\[\d+(;\d+)*m', '', str(arg)) for arg in args]
            log_file.write(" ".join(clean_args) + "\n")
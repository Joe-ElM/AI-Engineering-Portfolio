# input validation to check for things like:
# Empty input
# Possibly profanity or malformed prompts 


# guards.py

def validate_input(text):
    """
    Basic input validation:
    - Must not be empty
    - Must be at least 5 characters
    - Can be extended to filter profanity or prompt injection
    """
    if not text:
        return False
    if len(text.strip()) < 5:  # Enforces a minimum length of 5 characters
        return False
    return True

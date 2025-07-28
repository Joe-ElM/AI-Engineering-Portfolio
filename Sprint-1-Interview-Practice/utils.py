
# Utility functions used across the app (e.g., formatting, token counting, logging)



def format_response(text):
    """
    Cleans and formats AI response text if needed.
    You can extend this to apply Markdown, strip whitespace, etc.
    """
    return text.strip()
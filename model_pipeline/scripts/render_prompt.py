"""
Prompt Renderer Module

This module provides functionality to render basic prompt templates for LLM generation.
It uses Jinja2 to insert email content and user information into prompt templates.
"""

from jinja2 import Template


def render_prompt(template_str, email_thread, user_email):
    """
    Render a Jinja2 prompt template with email thread and user information.

    This function creates a prompt that instructs the LLM to generate content
    (such as summaries, action items, or draft replies) for an email thread.

    Args:
        template_str (str): Jinja2 template string
        email_thread (str): Email thread content
        user_email (str): User email address

    Returns:
        str: Rendered prompt template

    Raises:
        ValueError: If template rendering fails
    """
    try:
        # Create Jinja2 template
        template = Template(template_str)

        # Render template with variables
        return template.render(email_thread=email_thread, user_email=user_email)
    except Exception as e:
        # Re-raise with informative message
        raise ValueError(f"Jinja template render error: {str(e)}")

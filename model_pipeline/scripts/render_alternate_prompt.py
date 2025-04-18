"""
Alternate Prompt Renderer Module

This module provides functionality to render alternate prompt templates that include
examples of previously generated outputs that received negative feedback. This helps
the LLM understand what not to do and improve its output quality.
"""

from jinja2 import Template


def render_alternate_prompt(template_str, email_thread, user_email, negative_examples):
    """
    Render a Jinja2 prompt template with formatted negative examples.

    This function enhances the basic prompt rendering by including examples of
    previous outputs that received negative feedback, helping the LLM learn from
    past mistakes.

    Args:
        template_str (str): Jinja2 template string
        email_thread (str): Email thread content
        user_email (str): User email address
        negative_examples (list): List of tuples (email, previous_response) with negative feedback

    Returns:
        str: Rendered prompt template

    Raises:
        ValueError: If template rendering fails
    """
    try:
        # Create Jinja2 template
        template = Template(template_str)

        # Format negative examples in a structured way
        formatted_examples = "\n\n".join(
            f"""
            Example {i+1}
            ------------
            Email:
            {example[0]}

            Your Previous Response:
            {example[1]}
            """.strip()
            for i, example in enumerate(negative_examples)
        )

        # Render the template with all variables
        return template.render(
            email_thread=email_thread,
            user_email=user_email,
            negative_examples=formatted_examples,
        )
    except Exception as e:
        # Re-raise with informative message
        raise ValueError(f"Jinja template render error: {str(e)}")

"""
Criteria Prompt Renderer Module

This module provides functionality to render prompt templates for the ranking criteria.
These templates are used to ask the LLM to evaluate and rank multiple generated outputs
based on quality, accuracy, and usefulness.
"""

from jinja2 import Template


def render_criteria(template_str, output0, output1, output2, body):
    """
    Render a Jinja2 prompt template for ranking criteria.

    This function creates a prompt that instructs the LLM to compare and rank
    multiple candidate outputs based on their quality, relevance, and accuracy.

    Args:
        template_str (str): Jinja2 template string for ranking criteria
        output0 (str): First output to rank
        output1 (str): Second output to rank
        output2 (str): Third output to rank
        body (str): Original email body text

    Returns:
        str: Rendered criteria prompt template

    Raises:
        jinja2.exceptions.TemplateError: If template rendering fails
    """
    # Create Jinja2 template
    template = Template(template_str)

    # Render template with all variables
    return template.render(output0=output0, output1=output1, output2=output2, body=body)

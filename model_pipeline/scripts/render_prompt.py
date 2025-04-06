from jinja2 import Template


def render_prompt(template_str, email_thread, user_email):
    """Render a Jinja2 prompt template."""
    try:
        template = Template(template_str)
        return template.render(email_thread=email_thread, user_email=user_email)
    except Exception as e:
        raise ValueError(f"Jinja template render error: {str(e)}")

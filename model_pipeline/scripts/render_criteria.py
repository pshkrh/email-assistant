from jinja2 import Template


def render_criteria(template_str, output0, output1, output2, body):
    """Render a Jinja2 prompt template."""
    template = Template(template_str)
    return template.render(output0=output0, output1=output1, output2=output2, body=body)

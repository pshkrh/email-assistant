from jinja2 import Template


def render_alternate_prompt(template_str, email_thread, user_email, negative_examples):
    """Render a Jinja2 prompt template with formatted negative examples."""
    try:
        template = Template(template_str)

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

        return template.render(
            email_thread=email_thread,
            user_email=user_email,
            negative_examples=formatted_examples,
        )
    except Exception as e:
        raise ValueError(f"Jinja template render error: {str(e)}")

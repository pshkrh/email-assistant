# model_pipeline/llm_generator.py
from openai import OpenAI
from config import OPENAI_API_KEY
import mlflow

client = OpenAI(api_key=OPENAI_API_KEY)


def generate_outputs(body, task):
    """Generate 3 outputs for a given task using LLM."""
    prompts = {
        "summary": f"Provide a concise summary of this email:\n\n{body}",
        "action_items": f"Extract action items from this email as a numbered list:\n\n{body}",
        "draft_reply": f"Draft a professional reply to this email:\n\n{body}",
    }
    outputs = []
    with mlflow.start_run(nested=True):  # Nested run for each task
        mlflow.log_param(f"{task}_prompt", prompts[task])
        for i in range(3):
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompts[task]}],
                max_tokens=150,
                temperature=0.7,
            )
            output = response.choices[0].message.content.strip()
            outputs.append(output)
            mlflow.log_text(output, f"{task}_output_{i}.txt")
        mlflow.log_param(f"{task}_output_count", len(outputs))
    return outputs


def process_email_body(body):
    """Generate outputs for all tasks."""
    return {
        "summaries": generate_outputs(body, "summary"),
        "action_items": generate_outputs(body, "action_items"),
        "draft_replies": generate_outputs(body, "draft_reply"),
    }

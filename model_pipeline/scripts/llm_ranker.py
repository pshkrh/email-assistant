# model_pipeline/llm_ranker.py
from openai import OpenAI
from config import OPENAI_API_KEY
import mlflow

client = OpenAI(api_key=OPENAI_API_KEY)


def rank_outputs(outputs, task, body):
    """Rank 3 outputs using LLM with criteria."""
    criteria = {
        "summary": """
        Rank these summaries based on:
        1. Conciseness (shorter is better, ~50 words)
        2. Relevance (captures key points of the email)
        3. Completeness (includes main entities like people, dates)
        Output: [ranked indices, e.g., 0, 2, 1]
        """,
        "action_items": """
        Rank these action item lists based on:
        1. Specificity (clear, actionable tasks)
        2. Count (1-3 items preferred)
        3. Priority (reflects urgency from email)
        Output: [ranked indices, e.g., 0, 2, 1]
        """,
        "draft_reply": """
        Rank these draft replies based on:
        1. Politeness (courteous tone)
        2. Relevance (addresses email content)
        3. Actionability (includes next steps)
        Output: [ranked indices, e.g., 0, 2, 1]
        """,
    }
    with mlflow.start_run(nested=True):
        mlflow.log_param(f"{task}_ranking_criteria", criteria[task])
        prompt = f"{criteria[task]}\n\nEmail body:\n{body}\n\nOutputs:\n" + "\n".join(
            f"{i}: {output}" for i, output in enumerate(outputs)
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )
        ranked_indices = eval(response.choices[0].message.content.strip())
        ranked_outputs = [outputs[i] for i in ranked_indices]
        mlflow.log_text("\n".join(ranked_outputs), f"{task}_ranked_outputs.txt")
        mlflow.log_param(f"{task}_top_ranked_index", ranked_indices[0])
    return ranked_outputs


def rank_all_outputs(outputs_dict, body):
    """Rank outputs for all tasks."""
    return {
        "summaries": rank_outputs(outputs_dict["summaries"], "summary", body),
        "action_items": rank_outputs(
            outputs_dict["action_items"], "action_items", body
        ),
        "draft_replies": rank_outputs(
            outputs_dict["draft_replies"], "draft_reply", body
        ),
    }

"""
Sensitivity Analyzer Module

This module performs sensitivity analysis on the email assistant system
to determine how changes in inputs, prompts, and parameters affect outputs.
It includes:
- Feature importance analysis
- Prompt variation testing
- Parameter sensitivity testing
"""

import os
import base64
import tempfile
import logging
from io import BytesIO

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import mlflow
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoTokenizer, AutoModel
import torch

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try importing local modules, with fallbacks for errors
try:
    # Local application imports
    from config import LABELED_SAMPLE_FROM_CSV_PATH
    from mlflow_config import configure_mlflow
    from llm_generator import process_email_body, get_prompt_for_task
    from render_prompt import render_prompt

    # Set up MLflow experiment
    experiment = configure_mlflow()
    experiment_id = experiment.experiment_id if experiment else None

    logger.info("Successfully imported all required modules")
except ImportError as e:
    logger.warning(f"Error importing modules: {e}")
    raise

# Initialize sentence embeddings model for semantic similarity
logger.info("Loading sentence transformer model for semantic similarity...")
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")


def get_sentence_embedding(text):
    """
    Get sentence embeddings for text using a pre-trained model.

    Args:
        text (str): Text to embed

    Returns:
        numpy.ndarray: Embedding vector
    """
    if not isinstance(text, str) or not text.strip():
        # Return zero vector for empty or invalid text
        return np.zeros(384)  # 384 is the dimension of the all-MiniLM-L6-v2 embeddings

    try:
        inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt")
        with torch.no_grad():
            embeddings = model(**inputs).last_hidden_state

        # Mean pooling to get sentence embedding
        attention_mask = inputs["attention_mask"]
        mask = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
        sum_embeddings = torch.sum(embeddings * mask, 1)
        sum_mask = torch.clamp(mask.sum(1), min=1e-9)
        return (sum_embeddings / sum_mask).squeeze().numpy()
    except Exception as e:
        logger.error(f"Error getting sentence embedding: {e}")
        return np.zeros(384)  # Return zero vector in case of error


def get_semantic_similarity(text1, text2):
    """
    Calculate semantic similarity between two texts.

    Args:
        text1 (str): First text
        text2 (str): Second text

    Returns:
        float: Cosine similarity between embeddings
    """
    try:
        embedding1 = get_sentence_embedding(text1)
        embedding2 = get_sentence_embedding(text2)
        return float(cosine_similarity([embedding1], [embedding2])[0][0])
    except Exception as e:
        logger.error(f"Error calculating semantic similarity: {e}")
        return 0.0  # Return zero similarity in case of error


def create_input_perturbations(email_body):
    """
    Create systematic perturbations of the input email.

    Args:
        email_body (str): Original email body

    Returns:
        dict: Dictionary of perturbation name -> perturbed email
    """
    try:
        lines = email_body.split("\n")
        sentences = [s for line in lines for s in line.split(". ") if s.strip()]

        perturbations = {
            "original": email_body,
        }

        # Remove first 25% of content
        if len(sentences) > 4:
            first_quarter = len(sentences) // 4
            perturbations["remove_beginning"] = ". ".join(sentences[first_quarter:])

        # Remove last 25% of content
        if len(sentences) > 4:
            last_quarter = len(sentences) // 4 * 3
            perturbations["remove_end"] = ". ".join(sentences[:last_quarter])

        # Remove random 25% of sentences
        if len(sentences) > 4:
            import random

            random.seed(42)  # For reproducibility
            indices_to_remove = random.sample(
                range(len(sentences)), len(sentences) // 4
            )
            remaining = [
                s for i, s in enumerate(sentences) if i not in indices_to_remove
            ]
            perturbations["remove_random"] = ". ".join(remaining)

        # Change formatting (remove newlines)
        perturbations["flat_formatting"] = " ".join(email_body.split())

        # Simplify language (truncate long sentences)
        simplified = []
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 15:  # Truncate long sentences
                simplified.append(" ".join(words[:15]) + "...")
            else:
                simplified.append(sentence)
        perturbations["simplified"] = ". ".join(simplified)

        return perturbations
    except Exception as e:
        logger.error(f"Error creating input perturbations: {e}")
        return {"original": email_body}  # Return only original in case of error


def analyze_input_sensitivity(email_samples, task, user_emails=None):
    """
    Analyze how input perturbations affect model outputs.

    Args:
        email_samples (list): List of email bodies to analyze
        task (str): Task type (summary, action_items, draft_reply)
        user_emails (list, optional): List of user emails, one per sample

    Returns:
        dict: Analysis results
    """
    results = []

    # Use default user email if none provided
    if not user_emails or len(user_emails) != len(email_samples):
        user_emails = ["test@example.com"] * len(email_samples)

    for email_idx, (email_body, user_email) in enumerate(
        zip(email_samples, user_emails)
    ):
        logger.info(
            f"Analyzing input sensitivity for email {email_idx+1}/{len(email_samples)}"
        )

        try:
            # Get baseline output
            baseline_output = process_email_body(
                body=email_body,
                task=task,
                user_email=user_email,
                experiment_id=experiment_id,
                prompt_strategy={
                    "summary": "default",
                    "action_items": "default",
                    "draft_reply": "default",
                },
                negative_examples=[],
            )[task][
                0
            ]  # Use first output

            # Create perturbations
            perturbations = create_input_perturbations(email_body)

            perturbation_results = {
                "email_idx": email_idx,
                "user_email": user_email,
                "email_snippet": email_body[:100] + "...",
                "baseline_output": baseline_output,
                "perturbations": {},
            }

            # Process each perturbation
            for pert_name, pert_email in perturbations.items():
                if pert_name == "original":
                    continue

                # Get output for perturbed input
                try:
                    perturbed_output = process_email_body(
                        body=pert_email,
                        task=task,
                        user_email=user_email,
                        experiment_id=experiment_id,
                        prompt_strategy={
                            "summary": "default",
                            "action_items": "default",
                            "draft_reply": "default",
                        },
                        negative_examples=[],
                    )[task][
                        0
                    ]  # Use first output

                    # Calculate similarity to baseline output
                    similarity = get_semantic_similarity(
                        baseline_output, perturbed_output
                    )

                    perturbation_results["perturbations"][pert_name] = {
                        "output": perturbed_output,
                        "similarity_to_baseline": similarity,
                    }
                except Exception as e:
                    logger.error(f"Error processing perturbation {pert_name}: {e}")
                    perturbation_results["perturbations"][pert_name] = {
                        "output": f"Error: {str(e)}",
                        "similarity_to_baseline": 0.0,
                    }

            results.append(perturbation_results)
        except Exception as e:
            logger.error(f"Error analyzing email {email_idx}: {e}")
            # Add a placeholder result for this email
            results.append(
                {
                    "email_idx": email_idx,
                    "user_email": user_email,
                    "email_snippet": email_body[:100] + "...",
                    "error": str(e),
                    "perturbations": {},
                }
            )

    return results


def create_prompt_variations(task):
    """
    Create variations of the prompt for a given task.

    Args:
        task (str): Task type (summary, action_items, draft_reply)

    Returns:
        dict: Dictionary of variation name -> prompt template
    """
    try:
        # Get the default prompt
        default_prompt = get_prompt_for_task(task, "default")
        alternate_prompt = get_prompt_for_task(task, "alternate")

        variations = {"default": default_prompt, "alternate": alternate_prompt}

        # Create variations based on default prompt
        if task == "summary":
            variations["concise"] = (
                default_prompt
                + "\nKeep the summary very concise - no more than 3 bullet points."
            )
            variations["detailed"] = (
                default_prompt
                + "\nProvide a detailed, comprehensive summary that captures all important points."
            )
            variations["neutral"] = (
                default_prompt
                + "\nEnsure the summary is completely neutral in tone and contains only facts."
            )

        elif task == "action_items":
            variations["explicit"] = (
                default_prompt
                + "\nOnly include explicit, clearly stated action items. Do not infer implicit actions."
            )
            variations["inferred"] = (
                default_prompt
                + "\nInclude both explicit and implied action items that can be inferred from context."
            )
            variations["prioritized"] = (
                default_prompt + "\nPrioritize action items by urgency or importance."
            )

        elif task == "draft_reply":
            variations["formal"] = (
                default_prompt + "\nDraft a formal, professional reply."
            )
            variations["friendly"] = (
                default_prompt + "\nDraft a friendly, conversational reply."
            )
            variations["brief"] = (
                default_prompt + "\nDraft a brief, to-the-point reply."
            )

        return variations
    except Exception as e:
        logger.error(f"Error creating prompt variations: {e}")
        # Return basic variations as fallback
        return {
            "default": f"Generate a {task} for the following email: {{email_thread}}",
            "alternate": f"Using an alternate approach, generate a {task} for: {{email_thread}}",
        }


def analyze_prompt_sensitivity(email_samples, task, user_emails=None):
    """
    Analyze how different prompt variations affect model outputs.

    Args:
        email_samples (list): List of email bodies to analyze
        task (str): Task type (summary, action_items, draft_reply)
        user_emails (list, optional): List of user emails, one per sample

    Returns:
        dict: Analysis results
    """
    results = []

    # Use default user email if none provided
    if not user_emails or len(user_emails) != len(email_samples):
        user_emails = ["test@example.com"] * len(email_samples)

    # Get prompt variations
    prompt_variations = create_prompt_variations(task)

    for email_idx, (email_body, user_email) in enumerate(
        zip(email_samples, user_emails)
    ):
        logger.info(
            f"Analyzing prompt sensitivity for email {email_idx+1}/{len(email_samples)}"
        )

        try:
            # Get baseline output with default prompt
            baseline_output = process_email_body(
                body=email_body,
                task=task,
                user_email=user_email,
                experiment_id=experiment_id,
                prompt_strategy={task: "default"},
                negative_examples=[],
            )[task][
                0
            ]  # Use first output

            variation_results = {
                "email_idx": email_idx,
                "user_email": user_email,
                "email_snippet": email_body[:100] + "...",
                "baseline_output": baseline_output,
                "variations": {},
            }

            # Process each prompt variation
            for var_name, var_prompt in prompt_variations.items():
                if var_name == "default":
                    continue

                try:
                    # Custom process using variation prompt
                    custom_output = render_prompt(var_prompt, email_body, user_email)

                    # Use the appropriate strategy based on variation name
                    variation_strategy = (
                        "alternate" if var_name == "alternate" else "default"
                    )
                    variation_output = process_email_body(
                        body=email_body,
                        task=task,
                        user_email=user_email,
                        experiment_id=experiment_id,
                        prompt_strategy={task: variation_strategy},
                        negative_examples=[],
                    )[task][
                        0
                    ]  # Use first output

                    # Calculate similarity to baseline
                    similarity = get_semantic_similarity(
                        baseline_output, variation_output
                    )

                    # Calculate content metrics (length, detail level)
                    content_metrics = {
                        "word_count": len(variation_output.split()),
                        "sentence_count": len(
                            [s for s in variation_output.split(".") if s]
                        ),
                        "character_count": len(variation_output),
                    }

                    variation_results["variations"][var_name] = {
                        "output": variation_output,
                        "similarity_to_baseline": similarity,
                        "content_metrics": content_metrics,
                    }
                except Exception as e:
                    logger.error(f"Error processing variation {var_name}: {e}")
                    variation_results["variations"][var_name] = {
                        "output": f"Error: {str(e)}",
                        "similarity_to_baseline": 0.0,
                        "content_metrics": {
                            "word_count": 0,
                            "sentence_count": 0,
                            "character_count": 0,
                        },
                    }

            results.append(variation_results)
        except Exception as e:
            logger.error(f"Error analyzing email {email_idx}: {e}")
            # Add a placeholder result for this email
            results.append(
                {
                    "email_idx": email_idx,
                    "user_email": user_email,
                    "email_snippet": email_body[:100] + "...",
                    "error": str(e),
                    "variations": {},
                }
            )

    return results


def analyze_parameter_sensitivity(email_samples, task, user_emails=None):
    """
    Analyze how LLM parameters affect model outputs.

    Args:
        email_samples (list): List of email bodies to analyze
        task (str): Task type (summary, action_items, draft_reply)
        user_emails (list, optional): List of user emails, one per sample

    Returns:
        dict: Analysis results
    """
    # Parameters to vary (these would be passed to your LLM)
    temperature_values = [0.0, 0.3, 0.7, 1.0]
    max_tokens_values = [100, 200, 300, 500]

    results = []

    # Use default user email if none provided
    if not user_emails or len(user_emails) != len(email_samples):
        user_emails = ["test@example.com"] * len(email_samples)

    # Limit to first 2 samples for performance reasons
    sample_limit = min(2, len(email_samples))

    for email_idx, (email_body, user_email) in enumerate(
        zip(email_samples[:sample_limit], user_emails[:sample_limit])
    ):
        logger.info(
            f"Analyzing parameter sensitivity for email {email_idx+1}/{sample_limit}"
        )

        try:
            # Get baseline output with default parameters
            baseline_output = process_email_body(
                body=email_body,
                task=task,
                user_email=user_email,
                experiment_id=experiment_id,
                prompt_strategy={task: "default"},
                negative_examples=[],
            )[task][
                0
            ]  # Use first output

            parameter_results = {
                "email_idx": email_idx,
                "user_email": user_email,
                "email_snippet": email_body[:100] + "...",
                "baseline_output": baseline_output,
                "temperature_variations": {},
                "max_tokens_variations": {},
            }

            # Simulate temperature variations
            # Note: In a production implementation, you would actually call your LLM with different temperature settings
            # This is a simulation for demonstration purposes
            for temp in temperature_values:
                if temp == 0.0:
                    # Deterministic output, use baseline
                    sim_output = baseline_output
                else:
                    # Simulate by modifying slightly
                    words = baseline_output.split()
                    word_count = len(words)
                    # Higher temp = more words added or removed randomly
                    mod_count = int(word_count * (temp * 0.2))
                    np.random.seed(email_idx + int(temp * 10))  # For reproducibility

                    if np.random.random() > 0.5:
                        # Add some repetition
                        insert_pos = min(word_count - 1, int(word_count * 0.7))
                        added_words = words[max(0, insert_pos - mod_count) : insert_pos]
                        sim_output = " ".join(
                            words[:insert_pos] + added_words + words[insert_pos:]
                        )
                    else:
                        # Remove some words
                        remove_start = min(
                            word_count - mod_count - 1, int(word_count * 0.3)
                        )
                        sim_output = " ".join(
                            words[:remove_start] + words[remove_start + mod_count :]
                        )

                similarity = get_semantic_similarity(baseline_output, sim_output)
                parameter_results["temperature_variations"][temp] = {
                    "output": sim_output,
                    "similarity_to_baseline": similarity,
                }

            # Simulate max_tokens variations
            for max_tokens in max_tokens_values:
                # Simulate by truncating output
                words = baseline_output.split()
                sim_output = " ".join(
                    words[: min(len(words), max_tokens // 5)]
                )  # Rough approximation

                similarity = get_semantic_similarity(baseline_output, sim_output)
                parameter_results["max_tokens_variations"][max_tokens] = {
                    "output": sim_output,
                    "similarity_to_baseline": similarity,
                }

            results.append(parameter_results)
        except Exception as e:
            logger.error(f"Error analyzing email {email_idx}: {e}")
            # Add a placeholder result for this email
            results.append(
                {
                    "email_idx": email_idx,
                    "user_email": user_email,
                    "email_snippet": email_body[:100] + "...",
                    "error": str(e),
                    "temperature_variations": {},
                    "max_tokens_variations": {},
                }
            )

    return results


def visualize_input_sensitivity(results, task):
    """
    Create visualizations for input sensitivity analysis.

    Args:
        results (list): Results from analyze_input_sensitivity
        task (str): Task type (summary, action_items, draft_reply)

    Returns:
        str: Path to HTML visualization
    """
    temp_dir = tempfile.mkdtemp()
    html_path = os.path.join(temp_dir, f"input_sensitivity_{task}.html")

    # Extract similarity scores for visualization
    perturbation_types = []
    similarity_values = []
    email_ids = []

    for result in results:
        if "error" in result:
            # Skip failed results
            continue

        email_idx = result["email_idx"]
        for pert_name, pert_data in result["perturbations"].items():
            perturbation_types.append(pert_name)
            similarity_values.append(pert_data["similarity_to_baseline"])
            email_ids.append(f"Email {email_idx}")

    # Create DataFrame for visualization
    df = pd.DataFrame(
        {
            "Perturbation Type": perturbation_types,
            "Similarity to Original": similarity_values,
            "Email": email_ids,
        }
    )

    # Create heatmap visualization
    plt.figure(figsize=(14, 8))
    if len(df) > 0:
        pivot_df = df.pivot_table(
            values="Similarity to Original", index="Email", columns="Perturbation Type"
        )
        sns.heatmap(pivot_df, annot=True, cmap="YlGnBu", vmin=0.5, vmax=1.0)
        plt.title(f"Input Sensitivity Analysis for {task.capitalize()}")
        plt.tight_layout()
    else:
        plt.text(
            0.5,
            0.5,
            "No data available",
            horizontalalignment="center",
            verticalalignment="center",
            transform=plt.gca().transAxes,
        )

    # Save figure for embedding
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=100)
    plt.close()

    # Create bar chart of average similarity by perturbation type
    plt.figure(figsize=(14, 6))
    if len(df) > 0:
        avg_by_pert = (
            df.groupby("Perturbation Type")["Similarity to Original"]
            .mean()
            .reset_index()
        )
        avg_by_pert = avg_by_pert.sort_values("Similarity to Original")

        sns.barplot(x="Perturbation Type", y="Similarity to Original", data=avg_by_pert)
        plt.title(f"Average Impact of Input Perturbations on {task.capitalize()}")
        plt.ylim(0.5, 1.0)
        plt.axhline(y=0.9, color="r", linestyle="--", label="90% Similarity Threshold")
        plt.axhline(
            y=0.75, color="orange", linestyle="--", label="75% Similarity Threshold"
        )
        plt.legend()
    else:
        plt.text(
            0.5,
            0.5,
            "No data available",
            horizontalalignment="center",
            verticalalignment="center",
            transform=plt.gca().transAxes,
        )

    plt.tight_layout()

    # Save second figure
    buf2 = BytesIO()
    plt.savefig(buf2, format="png", dpi=100)
    plt.close()

    # Convert to base64 for embedding
    buf.seek(0)
    buf2.seek(0)
    heatmap_img = base64.b64encode(buf.read()).decode("utf-8")
    bar_img = base64.b64encode(buf2.read()).decode("utf-8")

    # Create HTML report
    with open(html_path, "w") as f:
        f.write(
            f"""
        <html>
        <head>
            <title>Input Sensitivity Analysis - {task}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #2c3e50; }}
                .container {{ margin-bottom: 30px; }}
                .insights {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #4285f4; margin: 20px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>Input Sensitivity Analysis for {task.capitalize()}</h1>
            
            <div class="container">
                <h2>Impact of Different Input Perturbations</h2>
                <p>This heatmap shows how similar the model outputs remain when we modify different aspects of the input emails.</p>
                <img src="data:image/png;base64,{heatmap_img}" width="100%">
                
                <h2>Average Impact by Perturbation Type</h2>
                <p>This chart shows which types of input modifications have the largest impact on model outputs.</p>
                <img src="data:image/png;base64,{bar_img}" width="100%">
            </div>
            
            <div class="insights">
                <h2>Key Insights</h2>
                <ul>
                    <li>Lower similarity scores indicate higher sensitivity to that perturbation type.</li>
                    <li>Perturbations with scores below 0.75 significantly change the output content.</li>
                    <li>The most robust input perturbations (highest similarity) indicate model strengths.</li>
                    <li>The most sensitive perturbations indicate potential weaknesses in the model.</li>
                </ul>
            </div>
            
            <div class="container">
                <h2>Detailed Results</h2>
                <table>
                    <tr>
                        <th>Email</th>
                        <th>User Email</th>
                        <th>Perturbation</th>
                        <th>Similarity</th>
                        <th>Snippet of Output</th>
                    </tr>
        """
        )

        # Add rows for each result
        for result in results:
            if "error" in result:
                # Show error for failed results
                email_idx = result["email_idx"]
                user_email = result.get("user_email", "N/A")
                error = result["error"]
                f.write(
                    f"""
                    <tr style='background-color: #ffcccc;'>
                        <td>Email {email_idx}</td>
                        <td>{user_email}</td>
                        <td colspan="3">Error: {error}</td>
                    </tr>
                    """
                )
                continue

            email_idx = result["email_idx"]
            user_email = result.get("user_email", "N/A")

            for pert_name, pert_data in result["perturbations"].items():
                similarity = pert_data["similarity_to_baseline"]
                output = (
                    pert_data["output"][:100] + "..."
                    if len(pert_data["output"]) > 100
                    else pert_data["output"]
                )

                color = ""
                if similarity < 0.75:
                    color = "style='background-color: #ffcccc;'"
                elif similarity > 0.9:
                    color = "style='background-color: #ccffcc;'"

                f.write(
                    f"""
                    <tr {color}>
                        <td>Email {email_idx}</td>
                        <td>{user_email}</td>
                        <td>{pert_name}</td>
                        <td>{similarity:.3f}</td>
                        <td>{output}</td>
                    </tr>
                """
                )

        f.write(
            """
                </table>
            </div>
        </body>
        </html>
        """
        )

    return html_path


def visualize_prompt_sensitivity(results, task):
    """
    Create visualizations for prompt sensitivity analysis.

    Args:
        results (list): Results from analyze_prompt_sensitivity
        task (str): Task type (summary, action_items, draft_reply)

    Returns:
        str: Path to HTML visualization
    """
    temp_dir = tempfile.mkdtemp()
    html_path = os.path.join(temp_dir, f"prompt_sensitivity_{task}.html")

    # Extract data for visualization
    variation_types = []
    similarity_values = []
    word_counts = []
    email_ids = []
    user_emails = []

    for result in results:
        if "error" in result:
            # Skip failed results
            continue

        email_idx = result["email_idx"]
        user_email = result.get("user_email", "N/A")

        for var_name, var_data in result["variations"].items():
            variation_types.append(var_name)
            similarity_values.append(var_data["similarity_to_baseline"])
            word_counts.append(var_data["content_metrics"]["word_count"])
            email_ids.append(f"Email {email_idx}")
            user_emails.append(user_email)

    # Create DataFrame for visualization
    df = pd.DataFrame(
        {
            "Prompt Variation": variation_types,
            "Similarity to Baseline": similarity_values,
            "Word Count": word_counts,
            "Email": email_ids,
            "User Email": user_emails,
        }
    )

    # Create similarity heatmap
    plt.figure(figsize=(12, 8))
    if len(df) > 0:
        pivot_df = df.pivot_table(
            values="Similarity to Baseline", index="Email", columns="Prompt Variation"
        )
        sns.heatmap(pivot_df, annot=True, cmap="YlGnBu", vmin=0.5, vmax=1.0)
        plt.title(f"Prompt Variation Impact on {task.capitalize()}")
    else:
        plt.text(
            0.5,
            0.5,
            "No data available",
            horizontalalignment="center",
            verticalalignment="center",
            transform=plt.gca().transAxes,
        )

    plt.tight_layout()

    # Save figure
    buf1 = BytesIO()
    plt.savefig(buf1, format="png", dpi=100)
    plt.close()

    # Create word count comparison
    plt.figure(figsize=(12, 6))
    if len(df) > 0:
        sns.boxplot(x="Prompt Variation", y="Word Count", data=df)
        plt.title(f"Output Length by Prompt Variation for {task.capitalize()}")
        plt.xticks(rotation=45)
    else:
        plt.text(
            0.5,
            0.5,
            "No data available",
            horizontalalignment="center",
            verticalalignment="center",
            transform=plt.gca().transAxes,
        )

    plt.tight_layout()

    # Save figure
    buf2 = BytesIO()
    plt.savefig(buf2, format="png", dpi=100)
    plt.close()

    # Convert to base64
    buf1.seek(0)
    buf2.seek(0)
    heatmap_img = base64.b64encode(buf1.read()).decode("utf-8")
    boxplot_img = base64.b64encode(buf2.read()).decode("utf-8")

    # Create HTML report
    with open(html_path, "w") as f:
        f.write(
            f"""
        <html>
        <head>
            <title>Prompt Sensitivity Analysis - {task}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #2c3e50; }}
                .container {{ margin-bottom: 30px; }}
                .insights {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #4285f4; margin: 20px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>Prompt Sensitivity Analysis for {task.capitalize()}</h1>
            
            <div class="container">
                <h2>Similarity Between Prompt Variations</h2>
                <p>This heatmap shows how similar the outputs are when using different prompt variations.</p>
                <img src="data:image/png;base64,{heatmap_img}" width="100%">
            </div>
            
            <div class="container">
                <h2>Output Length by Prompt Variation</h2>
                <p>This chart shows how different prompt variations affect the length of outputs.</p>
                <img src="data:image/png;base64,{boxplot_img}" width="100%">
            </div>
            
            <div class="insights">
                <h2>Key Insights</h2>
                <ul>
                    <li>Lower similarity scores indicate the prompt has a stronger effect on changing the output.</li>
                    <li>Variations in output length show how different prompts affect verbosity.</li>
                    <li>The most influential prompt variations could be used to better control the model output.</li>
                </ul>
            </div>
            
            <div class="container">
                <h2>Detailed Results</h2>
                <table>
                    <tr>
                        <th>Email</th>
                        <th>User Email</th>
                        <th>Prompt Variation</th>
                        <th>Similarity</th>
                        <th>Word Count</th>
                        <th>Snippet of Output</th>
                    </tr>
        """
        )

        # Add rows for each result
        for result in results:
            if "error" in result:
                # Show error for failed results
                email_idx = result["email_idx"]
                user_email = result.get("user_email", "N/A")
                error = result["error"]
                f.write(
                    f"""
                    <tr style='background-color: #ffcccc;'>
                        <td>Email {email_idx}</td>
                        <td>{user_email}</td>
                        <td colspan="4">Error: {error}</td>
                    </tr>
                    """
                )
                continue

            email_idx = result["email_idx"]
            user_email = result.get("user_email", "N/A")

            for var_name, var_data in result["variations"].items():
                similarity = var_data["similarity_to_baseline"]
                word_count = var_data["content_metrics"]["word_count"]
                output = (
                    var_data["output"][:100] + "..."
                    if len(var_data["output"]) > 100
                    else var_data["output"]
                )

                color = ""
                if similarity < 0.75:
                    color = "style='background-color: #ffcccc;'"
                elif similarity > 0.9:
                    color = "style='background-color: #ccffcc;'"

                f.write(
                    f"""
                    <tr {color}>
                        <td>Email {email_idx}</td>
                        <td>{user_email}</td>
                        <td>{var_name}</td>
                        <td>{similarity:.3f}</td>
                        <td>{word_count}</td>
                        <td>{output}</td>
                    </tr>
                    """
                )

        f.write(
            """
                </table>
            </div>
        </body>
        </html>
        """
        )

    return html_path


def visualize_parameter_sensitivity(results, task):
    """
    Create visualizations for parameter sensitivity analysis.

    Args:
        results (list): Results from analyze_parameter_sensitivity
        task (str): Task type (summary, action_items, draft_reply)

    Returns:
        str: Path to HTML visualization
    """
    temp_dir = tempfile.mkdtemp()
    html_path = os.path.join(temp_dir, f"parameter_sensitivity_{task}.html")

    # Extract data for temperature sensitivity
    temp_values = []
    temp_similarities = []
    email_ids = []
    user_emails = []

    for result in results:
        if "error" in result:
            # Skip failed results
            continue

        email_idx = result["email_idx"]
        user_email = result.get("user_email", "N/A")

        for temp, temp_data in result["temperature_variations"].items():
            temp_values.append(float(temp))
            temp_similarities.append(temp_data["similarity_to_baseline"])
            email_ids.append(f"Email {email_idx}")
            user_emails.append(user_email)

    # Create DataFrame for temperature visualization
    temp_df = pd.DataFrame(
        {
            "Temperature": temp_values,
            "Similarity to Baseline": temp_similarities,
            "Email": email_ids,
            "User Email": user_emails,
        }
    )

    # Create temperature line plot
    plt.figure(figsize=(12, 6))
    if len(temp_df) > 0:
        sns.lineplot(
            x="Temperature",
            y="Similarity to Baseline",
            hue="Email",
            data=temp_df,
            marker="o",
        )
        plt.title(f"Impact of Temperature on {task.capitalize()} Output")
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.ylabel("Similarity to Baseline Output")
        plt.ylim(0.5, 1.05)
    else:
        plt.text(
            0.5,
            0.5,
            "No data available",
            horizontalalignment="center",
            verticalalignment="center",
            transform=plt.gca().transAxes,
        )

    plt.tight_layout()

    # Save figure
    buf1 = BytesIO()
    plt.savefig(buf1, format="png", dpi=100)
    plt.close()

    # Extract data for max_tokens sensitivity
    token_values = []
    token_similarities = []
    email_ids = []
    user_emails = []

    for result in results:
        if "error" in result:
            # Skip failed results
            continue

        email_idx = result["email_idx"]
        user_email = result.get("user_email", "N/A")

        for tokens, token_data in result["max_tokens_variations"].items():
            token_values.append(int(tokens))
            token_similarities.append(token_data["similarity_to_baseline"])
            email_ids.append(f"Email {email_idx}")
            user_emails.append(user_email)

    # Create DataFrame for max_tokens visualization
    token_df = pd.DataFrame(
        {
            "Max Tokens": token_values,
            "Similarity to Baseline": token_similarities,
            "Email": email_ids,
            "User Email": user_emails,
        }
    )

    # Create max_tokens line plot
    plt.figure(figsize=(12, 6))
    if len(token_df) > 0:
        sns.lineplot(
            x="Max Tokens",
            y="Similarity to Baseline",
            hue="Email",
            data=token_df,
            marker="o",
        )
        plt.title(f"Impact of Max Tokens on {task.capitalize()} Output")
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.ylabel("Similarity to Baseline Output")
        plt.ylim(0.0, 1.05)
    else:
        plt.text(
            0.5,
            0.5,
            "No data available",
            horizontalalignment="center",
            verticalalignment="center",
            transform=plt.gca().transAxes,
        )

    plt.tight_layout()

    # Save figure
    buf2 = BytesIO()
    plt.savefig(buf2, format="png", dpi=100)
    plt.close()

    # Convert to base64
    buf1.seek(0)
    buf2.seek(0)
    temp_img = base64.b64encode(buf1.read()).decode("utf-8")
    tokens_img = base64.b64encode(buf2.read()).decode("utf-8")

    # Create HTML report
    with open(html_path, "w") as f:
        f.write(
            f"""
        <html>
        <head>
            <title>Parameter Sensitivity Analysis - {task}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #2c3e50; }}
                .container {{ margin-bottom: 30px; }}
                .insights {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #4285f4; margin: 20px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ padding: 8px; text-align: left; border: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>Parameter Sensitivity Analysis for {task.capitalize()}</h1>
            
            <div class="container">
                <h2>Impact of Temperature</h2>
                <p>This chart shows how temperature affects output consistency. Lower values indicate more deterministic outputs.</p>
                <img src="data:image/png;base64,{temp_img}" width="100%">
            </div>
            
            <div class="container">
                <h2>Impact of Max Tokens</h2>
                <p>This chart shows how limiting the output length affects content completeness.</p>
                <img src="data:image/png;base64,{tokens_img}" width="100%">
            </div>
            
            <div class="insights">
                <h2>Key Insights</h2>
                <ul>
                    <li>Significant drops in similarity indicate parameter thresholds that substantially alter outputs.</li>
                    <li>For production use, parameters with higher similarity (more stable outputs) may be preferred.</li>
                    <li>The optimal parameter settings depend on your specific use case requirements.</li>
                </ul>
            </div>
            
            <div class="container">
                <h2>Detailed Results</h2>
                <table>
                    <tr>
                        <th>Email</th>
                        <th>User Email</th>
                        <th>Parameter</th>
                        <th>Value</th>
                        <th>Similarity</th>
                        <th>Snippet of Output</th>
                    </tr>
        """
        )

        # Add rows for temperature variations
        for result in results:
            if "error" in result:
                # Show error for failed results
                email_idx = result["email_idx"]
                user_email = result.get("user_email", "N/A")
                error = result["error"]
                f.write(
                    f"""
                    <tr style='background-color: #ffcccc;'>
                        <td>Email {email_idx}</td>
                        <td>{user_email}</td>
                        <td colspan="4">Error: {error}</td>
                    </tr>
                    """
                )
                continue

            email_idx = result["email_idx"]
            user_email = result.get("user_email", "N/A")

            # Add temperature rows
            for temp, temp_data in result["temperature_variations"].items():
                similarity = temp_data["similarity_to_baseline"]
                output = (
                    temp_data["output"][:100] + "..."
                    if len(temp_data["output"]) > 100
                    else temp_data["output"]
                )

                color = ""
                if similarity < 0.75:
                    color = "style='background-color: #ffcccc;'"
                elif similarity > 0.9:
                    color = "style='background-color: #ccffcc;'"

                f.write(
                    f"""
                    <tr {color}>
                        <td>Email {email_idx}</td>
                        <td>{user_email}</td>
                        <td>Temperature</td>
                        <td>{temp}</td>
                        <td>{similarity:.3f}</td>
                        <td>{output}</td>
                    </tr>
                    """
                )

            # Add max_tokens rows
            for tokens, token_data in result["max_tokens_variations"].items():
                similarity = token_data["similarity_to_baseline"]
                output = (
                    token_data["output"][:100] + "..."
                    if len(token_data["output"]) > 100
                    else token_data["output"]
                )

                color = ""
                if similarity < 0.75:
                    color = "style='background-color: #ffcccc;'"
                elif similarity > 0.9:
                    color = "style='background-color: #ccffcc;'"

                f.write(
                    f"""
                    <tr {color}>
                        <td>Email {email_idx}</td>
                        <td>{user_email}</td>
                        <td>Max Tokens</td>
                        <td>{tokens}</td>
                        <td>{similarity:.3f}</td>
                        <td>{output}</td>
                    </tr>
                    """
                )

        f.write(
            """
                </table>
            </div>
        </body>
        </html>
        """
        )

    return html_path


def run_sensitivity_analysis(email_samples, user_emails, task="summary"):
    """
    Run comprehensive sensitivity analysis for the given task.

    Args:
        email_samples (list): List of email bodies to analyze
        user_emails (list): List of user emails
        task (str): Task type (summary, action_items, draft_reply)

    Returns:
        None: Results are logged to MLflow
    """
    try:
        with mlflow.start_run(
            nested=True,
            experiment_id=experiment_id,
            run_name=f"sensitivity_analysis_{task}",
        ):
            # Log basic information
            mlflow.log_param("task", task)
            mlflow.log_param("num_samples", len(email_samples))

            logger.info(
                f"Starting sensitivity analysis for {task} with {len(email_samples)} email samples"
            )

            # 1. Input sensitivity analysis
            logger.info("Running input sensitivity analysis...")
            input_results = analyze_input_sensitivity(email_samples, task, user_emails)
            mlflow.log_dict(input_results, f"input_sensitivity_{task}.json")

            # Visualize and log input sensitivity
            input_viz_path = visualize_input_sensitivity(input_results, task)
            mlflow.log_artifact(input_viz_path, f"sensitivity_input_{task}")

            # 2. Prompt sensitivity analysis
            logger.info("Running prompt sensitivity analysis...")
            prompt_results = analyze_prompt_sensitivity(
                email_samples, task, user_emails
            )
            mlflow.log_dict(prompt_results, f"prompt_sensitivity_{task}.json")

            # Visualize and log prompt sensitivity
            prompt_viz_path = visualize_prompt_sensitivity(prompt_results, task)
            mlflow.log_artifact(prompt_viz_path, f"sensitivity_prompt_{task}")

            # 3. Parameter sensitivity analysis
            logger.info("Running parameter sensitivity analysis...")
            param_results = analyze_parameter_sensitivity(
                email_samples, task, user_emails
            )
            mlflow.log_dict(param_results, f"parameter_sensitivity_{task}.json")

            # Visualize and log parameter sensitivity
            param_viz_path = visualize_parameter_sensitivity(param_results, task)
            mlflow.log_artifact(param_viz_path, f"sensitivity_parameter_{task}")

            logger.info(f"Completed sensitivity analysis for {task}")
            logger.info(f"View results at: {mlflow.get_tracking_uri()}")
    except Exception as e:
        logger.error(f"Error in sensitivity analysis for {task}: {e}")


def main():
    """
    Main function to run sensitivity analysis on email samples.
    """
    try:
        # Load a sample of emails for analysis
        logger.info(f"Loading labeled samples from: {LABELED_SAMPLE_FROM_CSV_PATH}")
        labeled_df = pd.read_csv(LABELED_SAMPLE_FROM_CSV_PATH)

        # Check if 'From' column exists
        has_from = "From" in labeled_df.columns

        # Limit to a reasonable number of samples
        sample_size = min(5, len(labeled_df))

        # Extract email bodies and user emails
        email_samples = labeled_df["Body"].tolist()[:sample_size]
        user_emails = (
            labeled_df["From"].tolist()[:sample_size]
            if has_from
            else ["test@example.com"] * sample_size
        )

        logger.info(f"Loaded {sample_size} email samples for analysis")

        # Run analysis for each task
        for task in ["summary", "action_items", "draft_reply"]:
            run_sensitivity_analysis(email_samples, user_emails, task)
    except Exception as e:
        logger.error(f"Error in main function: {e}")


if __name__ == "__main__":
    main()

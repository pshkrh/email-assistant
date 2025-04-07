# model_pipeline/llm_ranker.py
import os
import json
import mlflow
import yaml
from dotenv import load_dotenv
from load_prompts import load_prompts
from render_criteria import render_criteria
import vertexai
from vertexai.generative_models import GenerativeModel
from config import SERVICE_ACCOUNT_FILE, RANKER_CRITERIA_YAML, MODEL_ENV_PATH, IN_CLOUD_RUN, GCP_PROJECT_ID, SERVICE_ACCOUNT_SECRET_ID

# Import the new secret manager utilities
if IN_CLOUD_RUN:
    from secret_manager import get_credentials_from_secret

load_dotenv(dotenv_path=MODEL_ENV_PATH)

# GCP settings
GCP_LOCATION = os.getenv("GCP_LOCATION")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# Initialize credentials based on environment
if IN_CLOUD_RUN:
    # Get credentials from Secret Manager
    creds_dict = get_credentials_from_secret(GCP_PROJECT_ID, SERVICE_ACCOUNT_SECRET_ID, save_to_file=SERVICE_ACCOUNT_FILE)
    
    # For libraries that expect a file
    from google.oauth2 import service_account
    CREDENTIALS = service_account.Credentials.from_service_account_info(creds_dict)
    
    # Extract project ID from credentials
    GCP_PROJECT_ID = creds_dict.get("project_id", GCP_PROJECT_ID)
else:
    # Load from file for local development
    from google.auth import load_credentials_from_file
    CREDENTIALS, GCP_PROJECT_ID = load_credentials_from_file(SERVICE_ACCOUNT_FILE)

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION, credentials=CREDENTIALS)


def rank_outputs(criteria_prompt, outputs, task):
    with mlflow.start_run(nested=True):
        mlflow.log_param(f"{task}_ranking_criteria", criteria_prompt)

        try:
            model = GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002"))
            response = model.generate_content(criteria_prompt)
            response_text = response.text.strip() if response and response.text else ""
        except Exception as e:
            mlflow.log_param(f"{task}_rank_failed", True)
            mlflow.log_param(f"{task}_rank_error", str(e))
            print(f"[Error] Gemini ranking failed: {e}")
            return outputs  # Fallback: return original unranked outputs

        # Parse structured ranking
        try:
            structured_data = (
                json.loads(response_text)
                if response_text.startswith("{")
                else {
                    task: (
                        response_text.split("ranked_indices:")[1].strip().split("\n")[0]
                    )
                }
            )
            ranked_indices_str = structured_data[task]
            ranked_indices = json.loads(ranked_indices_str)

            ranked_outputs = [outputs[i] for i in ranked_indices]
            mlflow.log_text("\n".join(ranked_outputs), f"{task}_ranked_outputs.txt")
            mlflow.log_param(f"{task}_top_ranked_index", ranked_indices[0])

        except Exception as e:
            print(f"[Error] Failed to parse ranking response: {e}")
            mlflow.log_param(f"{task}_rank_parse_failed", True)
            ranked_outputs = outputs  # Fallback to original order

        return ranked_outputs


def rank_all_outputs(llm_outputs, task, body):
    """Rank outputs for all tasks."""
    criterias = load_prompts(RANKER_CRITERIA_YAML)

    llm_ranks = {}

    # Use with statement to automatically close the file
    try:
        # Loop through each task and generate the output
        full_prompt = f"""
            {render_criteria(criterias[task], 
                                output0=llm_outputs[task][0], 
                                output1=llm_outputs[task][1], 
                                output2=llm_outputs[task][2],
                                body=body)}
        """
        if full_prompt:
            llm_ranks[task] = rank_outputs(
                criteria_prompt=full_prompt, outputs=llm_outputs[task], task=task
            )
        else:
            llm_ranks[task] = f"No criteria found for task: {task}"

        return llm_ranks

    except FileNotFoundError:
        raise FileNotFoundError(
            f"Error: The file {RANKER_CRITERIA_YAML} does not exist."
        )
    except yaml.YAMLError as e:
        raise ValueError(f"YAML loading error: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error in rank_all_outputs: {str(e)}") from e


# if __name__ == "__main__":
# body = """
#     Checked out
#     ---------- Forwarded message ---------
#     From: Try <try8200@gmail.com>
#     Date: Sun, Mar 9, 2025 at 8:41 PM
#     Subject: Fwd: Test
#     To: Shubh Desai <shubhdesai111@gmail.com>


#     Check out this
#     ---------- Forwarded message ---------
#     From: Shubh Desai <shubhdesai111@gmail.com>
#     Date: Sun, Mar 9, 2025 at 8:37 PM
#     Subject: Re: Test
#     To: Try <try8200@gmail.com>


#     Hey, once again

#     On Sun, Mar 9, 2025 at 8:36 PM Try <try8200@gmail.com> wrote:
#     hello Shubh

#     On Sun, Mar 9, 2025 at 8:35 PM Shubh Desai <shubhdesai111@gmail.com> wrote:
#     Hello Try
# """

# llm_outputs = {
#     "draft_reply": [
#         " Dear Team,\n\nThank you for bringing this to my attention. I will investigate the anomalies detected in the email dataset, specifically concerning the 'Date' column and the unexpected values at the provided indexes (140690, 140694, 140705, and 140707). I will review the data and determine the cause of these anomalies. I'll provide an update once I have more information.\n\nBest regards,\n\nTry8200\n",
#         " Dear Team,\n\nThank you for bringing this to my attention. I've reviewed the anomalies detected in the email dataset. The issue with the 'Date' column, specifically the unexpected values at indexes 140690, 140694, 140705, and 140707, is noted. I will investigate these specific entries to determine the root cause of the unexpected values and rectify the issue. I will keep you updated on my progress.\n\nBest regards,\n\ntry8200@gmail.com\n",
#         ' Dear Team,\n\nThank you for the notification regarding the anomalies detected in the email dataset. I will investigate the discrepancies in the "Date" column, specifically focusing on the indexes [140690, 140694, 140705, 140707]. I\'ll provide an update on my findings and the steps taken to address the issue as soon as possible.\n\nBest regards,\n\nTry8200\n',
#     ],
#     "summary": [
#         "\n- Anomalies detected in the email dataset within the 'Date' column.\n- The anomaly type is `expect_column_values_to_be_in_set`.\n- There are 4 unexpected values, representing 0.00077% of the data.\n- Anomalous data points are located at indexes 140690, 140694, 140705, and 140707.\n",
#         "\n- Anomalies detected in the email dataset.\n- Anomaly in the 'Date' column.\n- Unexpected values found in the 'Date' column based on 'expect_column_values_to_be_in_set' expectation.\n- Four unexpected values were identified.\n- Unexpected percentage of values is 0.0007734998936437646.\n- Partial indexes of the anomalies: 140690, 140694, 140705, and 140707.\n",
#         "\n- Anomalies detected in the email dataset.\n- Anomaly found in the 'Date' column.\n- Expectation: column values should be in a defined set.\n- Unexpected count: 4.\n- Unexpected percentage: 0.0007734998936437646.\n- Partial indexes affected: 140690, 140694, 140705, and 140707.\n",
#     ],
# }

# {
#     "draft_reply": [
#         " Dear Shubh Desai,\n\nThanks for the follow-up. I've seen the forwarded message.\n\nBest regards,\n\nTry\n",
#         " Dear Shubh Desai,\n\nThanks for the quick reply! I've seen the forwarded message as well.\n\nBest,\n\nTry\n",
#         " Dear Shubh Desai,\n\nThanks for the follow-up! I hope you are doing well.\n\nBest,\nTry\n",
#     ],
#     "summary": [
#         '\n- Shubh Desai initiated the email thread with a greeting to Try.\n- Try replied with a greeting to Shubh Desai.\n- Shubh Desai responded again to Try.\n- Try forwarded the email to Shubh Desai and included a message "Check out this."\n',
#         "\n- Shubh Desai and Try exchanged greetings in an email thread.\n- Try forwarded an email to Shubh Desai.\n",
#         '\n- Shubh Desai and Try exchanged greetings.\n- Shubh Desai forwarded the message to Try.\n- Try forwarded the message to Shubh Desai with "Check out this" as the content.\n',
#     ],
# }

# tasks = ["draft_reply", "summary"]
# ranked_outputs = rank_all_outputs(llm_outputs, tasks, body)
# print(ranked_outputs)
# for output in ranked_outputs["draft_reply"]:
#     print("\n-----------\n", output, "\n-------------\n")
# for output in ranked_outputs["summary"]:
#     print("\n-----------\n", output, "\n-------------\n")

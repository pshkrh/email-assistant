import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure correct path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import functions to be tested
from model_pipeline.scripts.llm_generator import generate_outputs, process_email_body

class TestLLMGenerator(unittest.TestCase):

    def setUp(self):
        """Setup test data before running each test case."""
        self.sample_email_body = """
        Dear John,

        We would like to schedule a meeting next Monday to discuss the project timeline.
        Please confirm your availability.

        Best regards,
        Alice
        """
        self.tasks = ["summary", "draft_reply", "action_item"]

        # Mocked prompts for different tasks
        self.mock_prompts = {
            "summary": "Summarize this email thread...",
            "draft_reply": "Generate a draft reply...",
            "action_item": "Extract action items..."
        }

    # ---------------------------------------------
    # TESTING LLM OUTPUT GENERATION (`generate_outputs`)
    # ---------------------------------------------

    @patch("model_pipeline.scripts.llm_generator.GenerativeModel")
    def test_generate_outputs_success(self, mock_model):
        """
        Test: LLM output generation with valid structured responses.
        Goal: Ensure the model generates 3 valid outputs in JSON format.
        Mocked: Google Vertex AI response.
        """
        mock_instance = MagicMock()
        response_text = """{
            "summary": "summary: - Meeting scheduled for Monday\\n- Project timeline discussion",
            "draft_reply": "draft_reply: Dear John,\\nThank you for reaching out. I am available for the meeting.",
            "action_item": "action_item: - Confirm meeting availability"
        }"""
        mock_instance.generate_content.return_value.text = response_text
        mock_model.return_value = mock_instance

        outputs = generate_outputs("summary", "Summarize this email thread...")
        
        # Ensure exactly 3 outputs are generated
        self.assertEqual(len(outputs), 3)
        
        # Check if the response contains expected formatting
        self.assertIn("summary: -", outputs[0])

    @patch("model_pipeline.scripts.llm_generator.GenerativeModel")
    def test_generate_outputs_fallback_text(self, mock_model):
        """
        Test: LLM output generation when JSON parsing fails.
        Goal: Ensure function gracefully handles unstructured LLM responses.
        Mocked: Google Vertex AI returning plain text instead of JSON.
        """
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value.text = "Here is the summary: The meeting is scheduled."
        mock_model.return_value = mock_instance

        outputs = generate_outputs("summary", "Summarize this email thread...")

        # Ensure function still generates 3 outputs despite malformed response
        self.assertEqual(len(outputs), 3)

        # Check if fallback mechanism correctly detects invalid structure
        self.assertIn("No summary", outputs[0])  # Now it should trigger the fallback


    # ---------------------------------------------
    # TESTING EMAIL PROCESSING (`process_email_body`)
    # ---------------------------------------------

    @patch("model_pipeline.scripts.llm_generator.load_prompts")
    @patch("model_pipeline.scripts.llm_generator.generate_outputs")
    def test_process_email_body_success(self, mock_generate, mock_load_prompts):
        """
        Test: Email body processing for multiple tasks.
        Goal: Ensure summaries, draft replies, and action items are correctly generated.
        Mocked: `load_prompts` and `generate_outputs` functions.
        """
        mock_load_prompts.return_value = self.mock_prompts
        mock_generate.side_effect = lambda task, prompt: [f"{task}: Fake response"] * 3

        outputs = process_email_body(self.sample_email_body, self.tasks)

        # Ensure all tasks exist in the output
        self.assertIn("summary", outputs)
        self.assertIn("draft_reply", outputs)
        self.assertIn("action_item", outputs)

        # Ensure exactly 3 outputs are generated per task
        self.assertEqual(len(outputs["summary"]), 3)
        self.assertEqual(len(outputs["draft_reply"]), 3)
        self.assertEqual(len(outputs["action_item"]), 3)

    @patch("model_pipeline.scripts.llm_generator.load_prompts")
    @patch("model_pipeline.scripts.llm_generator.generate_outputs")
    def test_process_email_body_no_prompt_found(self, mock_generate, mock_load_prompts):
        """
        Test: Handling missing prompts for certain tasks.
        Goal: If a task has no prompt, function should return a proper error message.
        Mocked: `load_prompts` with missing prompts.
        """
        mock_load_prompts.return_value = {"summary": "Summarize this email thread..."}  # Missing prompts for other tasks
        mock_generate.side_effect = lambda task, prompt: [f"{task}: Fake response"] * 3

        outputs = process_email_body(self.sample_email_body, self.tasks)

        # Ensure missing prompts return error messages
        self.assertEqual(outputs["draft_reply"], "No prompt found for task: draft_reply")
        self.assertEqual(outputs["action_item"], "No prompt found for task: action_item")

    @patch("model_pipeline.scripts.llm_generator.load_prompts")
    def test_process_email_body_file_not_found(self, mock_load_prompts):
        """
        Test: Handling missing prompt file.
        Goal: If prompt file is missing, function should return an empty dictionary.
        Mocked: `load_prompts` raising a `FileNotFoundError`.
        """
        mock_load_prompts.side_effect = FileNotFoundError("File not found")

        outputs = process_email_body(self.sample_email_body, self.tasks)

        # ✅ Function should return an empty dictionary instead of crashing
        self.assertEqual(outputs, {})

    @patch("model_pipeline.scripts.llm_generator.load_prompts")
    def test_process_email_body_unexpected_error(self, mock_load_prompts):
        """
        Test: Handling unexpected function failures.
        Goal: If an unexpected exception occurs, function should fail gracefully.
        Mocked: `load_prompts` raising a generic exception.
        """
        mock_load_prompts.side_effect = Exception("Unexpected error occurred")

        outputs = process_email_body(self.sample_email_body, self.tasks)

        # Function should return an empty dictionary instead of failing
        self.assertEqual(outputs, {})

# Run tests
if __name__ == "__main__":
    unittest.main()

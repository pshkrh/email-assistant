import os
import sys
import unittest
import pandas as pd
import email
from unittest.mock import patch, mock_open, MagicMock

# Automatically detect and add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# Import functions from dataframe.py
from data_pipeline.scripts.dataframe import extract_email_data, process_enron_emails

# Sample email data for testing
SAMPLE_EMAIL = """From: test@example.com
To: receiver@example.com
Subject: Test Email
Message-ID: <1234@test.com>

Hello, this is a test email.
"""

MULTIPART_EMAIL = """From: test@example.com
To: receiver@example.com
Subject: Multipart Test
Message-ID: <1235@test.com>
Content-Type: multipart/mixed; boundary="boundary123"

--boundary123
Content-Type: text/plain

This is the plain text part.

--boundary123
Content-Type: text/html

<html><body>This is the HTML part.</body></html>

--boundary123--
"""

class TestExtractEmailData(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_EMAIL)
    def test_extract_email_data_valid(self, mock_file):
        """Test extracting metadata and body from a valid email file."""
        email_data = extract_email_data("dummy_email.txt")
        self.assertEqual(email_data["From"], "test@example.com")
        self.assertEqual(email_data["To"], "receiver@example.com")
        self.assertEqual(email_data["Subject"], "Test Email")
        self.assertEqual(email_data["Message-ID"], "<1234@test.com>")
        self.assertEqual(email_data["Body"], "Hello, this is a test email.")
        
        

    @patch("builtins.open", new_callable=mock_open, read_data=MULTIPART_EMAIL)
    def test_extract_email_data_multipart(self, mock_file):
        """Test extracting metadata and body from a multipart email."""
        email_data = extract_email_data("dummy_email.txt")
        self.assertEqual(email_data["From"], "test@example.com")
        self.assertEqual(email_data["To"], "receiver@example.com")
        self.assertEqual(email_data["Subject"], "Multipart Test")
        self.assertEqual(email_data["Message-ID"], "<1235@test.com>")
        self.assertIn("This is the plain text part.", email_data["Body"])

    @patch("builtins.open", new_callable=mock_open, read_data="Invalid Email Content")
    def test_extract_email_data_corrupt(self, mock_file):
        """Test handling of a corrupt email file."""
        email_data = extract_email_data("dummy_email.txt")

        # The function should return an empty dictionary if the email is invalid
        self.assertEqual(email_data["Body"], "")
        self.assertEqual(email_data["From"], None)  # Invalid emails should not have metadata
        self.assertEqual(email_data["To"], None)
        self.assertEqual(email_data["Message-ID"], None)

    @patch("builtins.open", new_callable=mock_open, read_data="")
    def test_extract_email_data_empty(self, mock_file):
        """Test handling of an empty email file."""
        email_data = extract_email_data("dummy_email.txt")
        self.assertEqual(email_data["Body"], "")

    @patch("builtins.open", new_callable=mock_open, read_data="Subject: No Headers")
    def test_extract_email_data_missing_headers(self, mock_file):
        """Test handling of an email with missing headers."""
        email_data = extract_email_data("dummy_email.txt")
        self.assertEqual(email_data["Subject"], "No Headers")
        self.assertIsNone(email_data.get("From"))  # Header missing
        self.assertIsNone(email_data.get("To"))  # Header missing
        self.assertIsNone(email_data.get("Message-ID"))  # Header missing
        self.assertEqual(email_data["Body"], "")

class TestProcessEnronEmails(unittest.TestCase):

    @patch("os.path.exists", return_value=False)
    def test_process_emails_directory_missing(self, mock_exists):
        """Test handling of a missing email dataset directory."""
        df = process_enron_emails("non_existent_dir")
        self.assertTrue(df.empty)

    @patch("os.path.exists", return_value=True)
    @patch("os.walk", return_value=iter([]))
    def test_process_emails_empty_directory(self, mock_walk, mock_exists):
        """Test handling of an empty email directory."""
        df = process_enron_emails("empty_dir")
        self.assertTrue(df.empty)

    @patch("os.path.exists", return_value=True)
    @patch("os.walk", return_value=iter([
        ("test_dir", [], ["email1.txt", "email2.txt"])
    ]))
    @patch("data_pipeline.scripts.dataframe.extract_email_data", side_effect=[
        {"From": "test1@example.com", "Body": "Email 1 content"},
        {"From": "test2@example.com", "Body": "Email 2 content"}
    ])
    def test_process_valid_emails(self, mock_extract, mock_walk, mock_exists):
        """Test processing of valid emails from a directory."""
        df = process_enron_emails("test_dir")
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["From"], "test1@example.com")
        self.assertEqual(df.iloc[1]["From"], "test2@example.com")

    @patch("os.path.exists", return_value=True)
    @patch("os.walk", return_value=iter([
        ("test_dir", [], ["valid_email.txt", "corrupt_email.txt"])
    ]))
    @patch("data_pipeline.scripts.dataframe.extract_email_data", side_effect=[
        {"From": "valid@example.com", "Body": "Valid email content"},
        Exception("Corrupt email")
    ])
    def test_process_emails_with_corrupt_file(self, mock_extract, mock_walk, mock_exists):
        """Test handling of a corrupt email file while processing."""
        df = process_enron_emails("test_dir")
        self.assertEqual(len(df), 1)  # Only 1 valid email processed
        self.assertEqual(df.iloc[0]["From"], "valid@example.com")

if __name__ == "__main__":
    unittest.main()

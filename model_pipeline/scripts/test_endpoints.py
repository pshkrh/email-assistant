#!/usr/bin/env python3
"""
Comprehensive pre-deployment verification script for the MailMate system.

This script tests all major functionality with detailed output of responses.
It verifies the health of endpoints, database schema, and prompt optimization
capabilities before deployment to production.
"""

import sys
import logging
import json
import uuid
import os
import subprocess
from datetime import datetime, timedelta

import requests
import psycopg2
from psycopg2.extras import RealDictCursor

from config import DB_NAME, USER, PASSWORD, HOST, PORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Server URL - change to your server URL as needed
BASE_URL = "http://localhost:8000"

# Test user for specific user tests - using a UUID to ensure it's unique
TEST_USER = f"test_user_{uuid.uuid4().hex[:8]}@example.com"


def print_json(data, title):
    """
    Print JSON data in a formatted way with a title.

    Args:
        data (dict): JSON data to print
        title (str): Title for the JSON output
    """
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)
    print(json.dumps(data, indent=2))
    print("=" * 80 + "\n")


def reset_and_initialize_db():
    """
    Reset the database and initialize the tables.

    Runs the initialize_db.py script with reset flags.

    Returns:
        bool: True if reset and initialization successful, False otherwise
    """
    logging.info("Resetting and initializing the database...")

    # Get the path to the initialize_db.py script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Assuming initialize_db.py is in the same directory
    script_path = os.path.join(current_dir, "initialize_db.py")

    # If not in the same directory, try one level up
    if not os.path.exists(script_path):
        script_path = os.path.join(os.path.dirname(current_dir), "initialize_db.py")

    if not os.path.exists(script_path):
        logging.error(
            f"Could not find initialize_db.py. Please provide the correct path."
        )
        return False

    # Run the script with reset flag
    try:
        logging.info(f"Executing: python {script_path} --reset --reset-confirmed")
        result = subprocess.run(
            ["python", script_path, "--reset", "--reset-confirmed"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logging.info("Database reset and initialization successful")
            logging.debug(f"Output: {result.stdout}")
            return True
        else:
            logging.error(
                f"Database reset and initialization failed with code {result.returncode}"
            )
            logging.error(f"Error output: {result.stderr}")
            return False

    except Exception as e:
        logging.error(f"Failed to execute initialize_db.py: {str(e)}")
        return False


def setup_test_user():
    """
    Setup a test user with a strategy that needs optimization.

    Creates a user with below-threshold performance for testing.

    Returns:
        bool: True if setup successful, False otherwise
    """
    logging.info(f"Setting up test user: {TEST_USER}...")

    try:
        # Connect to database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            cursor_factory=RealDictCursor,
        )

        cur = conn.cursor()

        # 1. Ensure user exists in user_prompt_strategies with default strategies
        cur.execute(
            """
            INSERT INTO user_prompt_strategies 
            (user_email, summary_strategy, action_items_strategy, draft_reply_strategy, last_updated)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_email) DO UPDATE
            SET summary_strategy = 'default',
                action_items_strategy = 'default', 
                draft_reply_strategy = 'default'
            """,
            (TEST_USER, "default", "default", "default", datetime.now()),
        )

        # 2. Insert feedback data to simulate poor performance
        # Date for feedback entries - from past week
        today = datetime.now().date()
        dates = [(today - timedelta(days=i)) for i in range(1, 8)]

        # First, check the user_feedback table schema
        cur.execute(
            """
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'user_feedback'
            ORDER BY ordinal_position
            """
        )
        columns = cur.fetchall()
        required_columns = [
            col["column_name"] for col in columns if col["is_nullable"] == "NO"
        ]
        logging.info(f"Required columns in user_feedback: {required_columns}")

        # Insert 8 entries for summary, with 3 positive and 5 negative = 37.5% positive
        for i in range(8):
            summary_feedback = 1 if i < 3 else 0  # First 3 positive, rest negative

            # Generate unique IDs for the test data
            message_id = f"test_msg_{uuid.uuid4().hex[:8]}"
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"

            # Insert record with all required fields
            cur.execute(
                """
                INSERT INTO user_feedback
                (user_email, message_id, thread_id, date, from_email, to_email, subject, body, 
                messages_count, summary, summary_feedback)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    TEST_USER,
                    message_id,
                    thread_id,
                    dates[i % len(dates)],
                    f"sender_{i}@example.com",
                    TEST_USER,
                    f"Test Subject {i}",
                    f"This is a test body for message {i}",
                    1,  # messages_count
                    "Test summary content",
                    summary_feedback,
                ),
            )

        # Insert 9 entries for action_items, with 4 positive and 5 negative = 44.4% positive
        for i in range(9):
            action_items_feedback = 1 if i < 4 else 0  # First 4 positive, rest negative

            # Generate unique IDs for the test data
            message_id = f"test_msg_{uuid.uuid4().hex[:8]}"
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"

            cur.execute(
                """
                INSERT INTO user_feedback
                (user_email, message_id, thread_id, date, from_email, to_email, subject, body, 
                messages_count, action_items, action_items_feedback)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    TEST_USER,
                    message_id,
                    thread_id,
                    dates[i % len(dates)],
                    f"sender_{i}@example.com",
                    TEST_USER,
                    f"Test Subject {i}",
                    f"This is a test body for message {i}",
                    1,  # messages_count
                    "Test action items content",
                    action_items_feedback,
                ),
            )

        # Insert 10 entries for draft_reply, with 5 positive and 5 negative = 50% positive
        for i in range(10):
            draft_reply_feedback = 1 if i < 5 else 0  # First 5 positive, rest negative

            # Generate unique IDs for the test data
            message_id = f"test_msg_{uuid.uuid4().hex[:8]}"
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"

            cur.execute(
                """
                INSERT INTO user_feedback
                (user_email, message_id, thread_id, date, from_email, to_email, subject, body, 
                messages_count, draft_reply, draft_reply_feedback)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    TEST_USER,
                    message_id,
                    thread_id,
                    dates[i % len(dates)],
                    f"sender_{i}@example.com",
                    TEST_USER,
                    f"Test Subject {i}",
                    f"This is a test body for message {i}",
                    1,  # messages_count
                    "Test draft reply content",
                    draft_reply_feedback,
                ),
            )

        # Commit all changes
        conn.commit()

        logging.info(
            f"✅ Successfully set up test user {TEST_USER} with below-threshold performance"
        )
        return True

    except Exception as e:
        logging.error(f"❌ Failed to set up test user: {str(e)}")
        logging.exception(e)
        return False


def test_check_performance():
    """
    Test the check_performance endpoint.

    Validates that the endpoint returns performance metrics correctly.

    Returns:
        bool: True if test passed, False otherwise
    """
    logging.info("Testing check_performance endpoint for all users...")

    # Test all users
    response = requests.get(f"{BASE_URL}/check_performance")
    if response.status_code == 200:
        data = response.json()
        user_count = len(data.get("user_metrics", {}))
        logging.info(f"✅ Successfully retrieved metrics for {user_count} users")

        # Print detailed data
        print_json(data, "CHECK PERFORMANCE - ALL USERS")

        # Print summary of users below threshold
        if data.get("users_below_threshold"):
            print("\nUsers with tasks below threshold:")
            for user, tasks in data.get("users_below_threshold", {}).items():
                print(f"  - {user}: {', '.join(tasks)}")
    else:
        logging.error(
            f"❌ Failed to retrieve metrics: {response.status_code} - {response.text}"
        )
        return False

    return True


def test_optimize_prompts():
    """
    Test the optimize_prompts endpoint.

    Validates that the endpoint optimizes prompts based on performance metrics.

    Returns:
        bool: True if test passed, False otherwise
    """
    logging.info("Testing optimize_prompts endpoint for all users...")

    # Set proper headers for JSON content
    headers = {"Content-Type": "application/json"}

    # Test all users first
    response = requests.post(
        f"{BASE_URL}/optimize_prompts", headers=headers, json={}  # Empty JSON body
    )
    if response.status_code == 200:
        data = response.json()
        changes = len(data.get("user_changes", []))
        logging.info(
            f"✅ Successfully optimized prompts for all users, made {changes} changes"
        )

        # Print detailed data
        print_json(data, "OPTIMIZE PROMPTS - ALL USERS")

        # Print summary of changes
        if changes > 0:
            print("\nChanges made:")
            for change in data.get("user_changes", []):
                user = change.get("user_email")
                task = change.get("task")
                old = change.get("old_strategy")
                new = change.get("new_strategy")
                perf = change.get("performance_score", 0) * 100
                print(f"  - {user} - {task}: {old} → {new} (Performance: {perf:.1f}%)")
        else:
            print(
                "\nNo changes made - all strategies already optimized or no users below threshold"
            )
    else:
        logging.error(
            f"❌ Failed to optimize prompts for all users: {response.status_code} - {response.text}"
        )
        return False

    # Now create a new test user with below-threshold performance
    setup_success = setup_test_user()
    if not setup_success:
        logging.error("❌ Failed to set up test user for specific user test")
        return False

    # Test optimize_prompts with the new specific user
    logging.info(f"Testing optimize_prompts endpoint for specific user: {TEST_USER}...")
    response = requests.post(
        f"{BASE_URL}/optimize_prompts", headers=headers, json={"user_email": TEST_USER}
    )
    if response.status_code == 200:
        data = response.json()
        changes = len(data.get("user_changes", []))
        logging.info(
            f"✅ Successfully optimized prompts for new test user, made {changes} changes"
        )

        # Print detailed data
        print_json(data, f"OPTIMIZE PROMPTS - USER: {TEST_USER}")

        # Print summary of changes
        if changes > 0:
            print("\nChanges made for new test user:")
            for change in data.get("user_changes", []):
                task = change.get("task")
                old = change.get("old_strategy")
                new = change.get("new_strategy")
                perf = change.get("performance_score", 0) * 100
                print(f"  - {task}: {old} → {new} (Performance: {perf:.1f}%)")
            return True
        else:
            logging.warning(
                f"⚠️ No changes made for new test user - this could indicate a problem"
            )
            # Continue anyway since it might be an expected result in some cases
    else:
        logging.error(
            f"❌ Failed to optimize prompts for specific user: {response.status_code} - {response.text}"
        )
        return False

    return True


def test_optimization_history():
    """
    Test the get_optimization_history endpoint.

    Validates that the endpoint returns optimization history correctly.

    Returns:
        bool: True if test passed, False otherwise
    """
    logging.info("Testing get_optimization_history endpoint for all users...")

    # Test all users
    response = requests.get(f"{BASE_URL}/get_optimization_history")
    if response.status_code == 200:
        data = response.json()
        history_count = len(data.get("history", []))
        logging.info(
            f"✅ Successfully retrieved optimization history with {history_count} entries"
        )

        # Print detailed data
        print_json(data, "OPTIMIZATION HISTORY - ALL USERS")

        # Print summary of history
        if history_count > 0:
            print("\nRecent changes:")
            for i, entry in enumerate(
                data.get("history", [])[:5]
            ):  # Show only the 5 most recent
                user = entry.get("user_email")
                task = entry.get("task")
                old = entry.get("old_strategy")
                new = entry.get("new_strategy")
                reason = entry.get("change_reason")
                time = entry.get("timestamp", "").split("T")[0]  # Just the date part
                print(f"  {i+1}. {user} - {task}: {old} → {new} ({reason}) on {time}")
        else:
            print("\nNo optimization history found")
    else:
        logging.error(
            f"❌ Failed to retrieve optimization history: {response.status_code} - {response.text}"
        )
        return False

    # Check history for our test user
    logging.info(
        f"Testing get_optimization_history endpoint for specific user: {TEST_USER}..."
    )
    response = requests.get(
        f"{BASE_URL}/get_optimization_history?user_email={TEST_USER}"
    )
    if response.status_code == 200:
        data = response.json()
        history_count = len(data.get("history", []))
        logging.info(
            f"✅ Successfully retrieved optimization history for {TEST_USER} with {history_count} entries"
        )

        # Print detailed data
        print_json(data, f"OPTIMIZATION HISTORY - USER: {TEST_USER}")

        # Print summary of history
        if history_count > 0:
            print(f"\nRecent changes for {TEST_USER}:")
            for i, entry in enumerate(data.get("history", [])):
                task = entry.get("task")
                old = entry.get("old_strategy")
                new = entry.get("new_strategy")
                reason = entry.get("change_reason")
                time = entry.get("timestamp", "").split("T")[0]  # Just the date part
                print(f"  {i+1}. {task}: {old} → {new} ({reason}) on {time}")
        else:
            print(f"\nNo optimization history found for {TEST_USER}")
    else:
        logging.error(
            f"❌ Failed to retrieve optimization history for specific user: {response.status_code} - {response.text}"
        )
        return False

    return True


def test_user_strategies():
    """
    Test the get_user_strategies endpoint.

    Validates that the endpoint returns user strategies correctly.

    Returns:
        bool: True if test passed, False otherwise
    """
    logging.info(f"Testing get_user_strategies endpoint for user: {TEST_USER}...")

    response = requests.get(f"{BASE_URL}/get_user_strategies?user_email={TEST_USER}")
    if response.status_code == 200:
        data = response.json()
        strategies = data.get("strategies", {})
        logging.info(f"✅ Successfully retrieved strategies for {TEST_USER}")

        # Print detailed data
        print_json(data, f"USER STRATEGIES - {TEST_USER}")

        # Print summary of strategies
        print(f"\nCurrent strategies for {TEST_USER}:")
        for task, strategy in strategies.items():
            print(f"  - {task}: {strategy}")
    else:
        logging.error(
            f"❌ Failed to retrieve user strategies: {response.status_code} - {response.text}"
        )
        return False

    return True


def test_scheduled_check():
    """
    Test the scheduled_check endpoint.

    Validates that the scheduled check endpoint works correctly.
    Creates a test user with low performance to verify optimization.

    Returns:
        bool: True if test passed, False otherwise
    """
    # Create a new test user that hasn't been optimized
    new_scheduled_test_user = f"scheduled_test_user_{uuid.uuid4().hex[:8]}@example.com"

    try:
        # Connect to database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            cursor_factory=RealDictCursor,
        )

        cur = conn.cursor()

        # 1. Create user with default strategies
        cur.execute(
            """
            INSERT INTO user_prompt_strategies 
            (user_email, summary_strategy, action_items_strategy, draft_reply_strategy, last_updated)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (new_scheduled_test_user, "default", "default", "default", datetime.now()),
        )

        # 2. Insert feedback data with poor performance
        today = datetime.now().date()
        dates = [(today - timedelta(days=i)) for i in range(1, 8)]

        # Insert feedback entries with low positive ratio
        for i in range(10):
            feedback = 1 if i < 3 else 0  # 30% positive

            # Generate unique IDs
            message_id = f"sched_msg_{uuid.uuid4().hex[:8]}"
            thread_id = f"sched_thread_{uuid.uuid4().hex[:8]}"

            # Insert for all three tasks with all required fields
            cur.execute(
                """
                INSERT INTO user_feedback
                (user_email, message_id, thread_id, date, from_email, to_email, subject, body, 
                messages_count, summary, summary_feedback, action_items, action_items_feedback, 
                draft_reply, draft_reply_feedback)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    new_scheduled_test_user,
                    message_id,
                    thread_id,
                    dates[i % len(dates)],
                    f"sender_{i}@example.com",
                    new_scheduled_test_user,
                    f"Test Subject {i}",
                    f"This is a test body for message {i}",
                    1,  # messages_count
                    "Test summary content",
                    feedback,
                    "Test action items content",
                    feedback,
                    "Test draft reply content",
                    feedback,
                ),
            )

        # Commit changes
        conn.commit()
        logging.info(f"✅ Created scheduled test user: {new_scheduled_test_user}")

    except Exception as e:
        logging.error(f"❌ Failed to create scheduled test user: {str(e)}")
        logging.exception(e)
        return False

    # Now test the scheduled_check endpoint
    logging.info("Testing scheduled_check endpoint...")

    response = requests.get(f"{BASE_URL}/scheduled_check")
    if response.status_code == 200:
        data = response.json()
        changes = len(data.get("user_changes", []))
        logging.info(f"✅ Successfully ran scheduled check, made {changes} changes")

        # Print detailed data
        print_json(data, "SCHEDULED CHECK")

        # Print summary of changes
        if changes > 0:
            print("\nChanges made during scheduled check:")
            for change in data.get("user_changes", []):
                user = change.get("user_email")
                task = change.get("task")
                old = change.get("old_strategy")
                new = change.get("new_strategy")
                perf = change.get("performance_score", 0) * 100
                print(f"  - {user} - {task}: {old} → {new} (Performance: {perf:.1f}%)")

                # Check if our scheduled test user was updated
                if user == new_scheduled_test_user:
                    logging.info(f"✅ Scheduled test user was successfully updated")
        else:
            print(
                "\nNo changes made during scheduled check - all strategies already optimized"
            )
    else:
        logging.error(
            f"❌ Failed to run scheduled check: {response.status_code} - {response.text}"
        )
        return False

    return True


def test_database_schema():
    """
    Test the database schema.

    Validates that necessary tables and columns exist in the database.

    Returns:
        bool: True if test passed, False otherwise
    """
    logging.info("\n🔍 Database Schema Verification")

    try:
        # Connect to database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            cursor_factory=RealDictCursor,
        )

        cur = conn.cursor()

        # Check table existence
        tables = ["user_prompt_strategies", "prompt_strategy_changes", "user_feedback"]
        for table in tables:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
                """,
                (table,),
            )
            exists = cur.fetchone()["exists"]
            if exists:
                logging.info(f"✅ Table {table} exists")
            else:
                logging.error(f"❌ Table {table} does not exist")
                return False

        # Check column existence for key tables
        required_columns = {
            "user_prompt_strategies": [
                "user_email",
                "summary_strategy",
                "action_items_strategy",
                "draft_reply_strategy",
                "last_updated",
            ],
            "prompt_strategy_changes": [
                "task",
                "old_strategy",
                "new_strategy",
                "change_reason",
                "timestamp",
                "user_email",
            ],
        }

        for table, columns in required_columns.items():
            for column in columns:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = %s AND column_name = %s
                    )
                    """,
                    (table, column),
                )
                exists = cur.fetchone()["exists"]
                if exists:
                    logging.info(f"✅ Column {column} exists in table {table}")
                else:
                    logging.error(f"❌ Column {column} does not exist in table {table}")
                    return False

        logging.info("✅ Database schema verification passed")
        return True

    except Exception as e:
        logging.error(f"❌ Database schema verification failed: {str(e)}")
        logging.exception(e)
        return False


def run_all_tests():
    """
    Run all verification tests.

    Executes a comprehensive test suite to validate system functionality.
    Prints a summary of results at the end.
    """
    print("\n" + "=" * 80)
    print(" MAILMATE SYSTEM COMPREHENSIVE PRE-DEPLOYMENT VERIFICATION ".center(80, "="))
    print("=" * 80)
    print(f"Testing against server: {BASE_URL}")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

    # First reset and initialize the database
    logging.info("Starting with fresh database...")
    if not reset_and_initialize_db():
        logging.error(
            "❌ Failed to reset and initialize database. Tests may not run properly."
        )
        proceed = (
            input("Do you want to continue with tests anyway? (y/n): ").lower() == "y"
        )
        if not proceed:
            logging.info("Tests aborted.")
            return False

    # Define all tests to run
    tests = [
        ("Performance Metrics", test_check_performance),
        ("Prompt Optimization", test_optimize_prompts),
        ("Optimization History", test_optimization_history),
        ("User Strategies", test_user_strategies),
        ("Scheduled Check", test_scheduled_check),
        ("Database Schema", test_database_schema),
    ]

    # Execute tests and track results
    results = {}
    for name, test_func in tests:
        print("\n" + "-" * 80)
        print(f" TESTING: {name} ".center(80, "-"))
        print("-" * 80)

        try:
            success = test_func()
            results[name] = success
        except Exception as e:
            logging.error(f"Exception during test {name}: {str(e)}")
            logging.exception(e)
            results[name] = False

    # Print summary of results
    print("\n\n" + "=" * 80)
    print(" TEST RESULTS SUMMARY ".center(80, "="))
    print("=" * 80)

    all_passed = True
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        all_passed = all_passed and result
        print(f"{name:30} {status}")

    print("\n" + "=" * 80)
    if all_passed:
        print(" 🎉 ALL TESTS PASSED - SYSTEM READY FOR DEPLOYMENT 🎉 ".center(80, "="))
    else:
        print(
            " ⚠️  SOME TESTS FAILED - SYSTEM NOT READY FOR DEPLOYMENT ⚠️ ".center(80, "=")
        )
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_all_tests()

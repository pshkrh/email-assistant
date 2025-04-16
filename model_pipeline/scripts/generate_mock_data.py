import os
import sys
import random
import uuid
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from db_connection import get_db_connection, DB_CONFIG

# Configuration
NUM_RECORDS = 50  # Total number of mock records to generate
DAYS_RANGE = 20  # Spread records over this many days
USERS = ["user1@example.com", "user2@example.com", "try8200@gmail.com"]  # Mock users

# Configure initial positive feedback ratio (will decrease over time)
# MODIFIED: Starting with lower positive ratio to trigger optimization
INITIAL_POSITIVE_RATIO = 0.8  # 80% positive at the beginning
FINAL_POSITIVE_RATIO = 0.4  # 40% positive by the end (showing SEVERE degradation)

# Sample email subjects and thread IDs
SUBJECTS = [
    "Meeting Agenda for Tomorrow",
    "Project Update: Q3 Goals",
    "Weekly Team Sync",
    "Client Proposal Review",
    "Budget Approval Request",
    "New Feature Requirements",
    "Product Launch Timeline",
    "HR Policy Update",
    "Vacation Request",
    "Company Retreat Planning",
]

# Sample email bodies
BODIES = [
    """Hey team,
    Just a quick reminder about our meeting tomorrow at 10 AM. 
    We'll be discussing the Q3 roadmap and project assignments. 
    Please come prepared with your progress updates and any blockers you're experiencing.
    Looking forward to it!
    Best,
    John
    """,
    """Hello everyone,
    I'm pleased to share that we've completed the initial phase of the project ahead of schedule.
    Key accomplishments:
    - Database migration completed (2 days early)
    - User authentication system implemented
    - Initial UI designs approved by the client
    
    Next steps:
    1. Begin frontend development (Mike)
    2. Set up CI/CD pipeline (Sarah)
    3. Finalize API documentation (Alex)
    
    Let me know if you have any questions or concerns.
    Regards,
    Project Manager
    """,
    """Dear Marketing Team,
    Following up on our discussion about the upcoming product launch, I've attached the revised
    marketing materials for your review. Please provide feedback by EOD Friday.
    
    We need to finalize:
    - Press release copy
    - Social media campaign schedule
    - Launch event details
    
    The CEO wants a final briefing next Monday.
    
    Thanks,
    Marketing Director
    """,
]

# Sample summaries
SUMMARIES = [
    "Team meeting scheduled for tomorrow at 10 AM to discuss Q3 roadmap and project assignments. Team members should prepare progress updates and identify any blockers.",
    "Project's initial phase completed ahead of schedule with database migration finished early, user authentication implemented, and UI designs approved. Next steps include beginning frontend development, setting up CI/CD pipeline, and finalizing API documentation.",
    "Marketing team needs to review revised materials for upcoming product launch and provide feedback by Friday. Items to finalize include press release copy, social media campaign schedule, and launch event details. CEO briefing scheduled for Monday.",
]

# Sample action items
ACTION_ITEMS = [
    "- Prepare progress updates for tomorrow's meeting\n- Identify and document any project blockers\n- Review Q3 roadmap documents",
    "- Begin frontend development (assigned to Mike)\n- Set up CI/CD pipeline (assigned to Sarah)\n- Finalize API documentation (assigned to Alex)",
    "- Review marketing materials by EOD Friday\n- Finalize press release copy\n- Prepare social media campaign schedule\n- Organize launch event details\n- Prepare for CEO briefing on Monday",
]

# Sample draft replies
DRAFT_REPLIES = [
    """Dear Team,
    
    Thank you for the reminder about tomorrow's meeting. I will come prepared with my progress updates and blockers.
    
    Looking forward to discussing the Q3 roadmap.
    
    Best regards,
    [Your Name]
    """,
    """Hello Project Manager,
    
    Thank you for the update on the project progress. It's great to hear that we're ahead of schedule.
    
    I'll be focusing on my assigned tasks and will coordinate with the team on the next steps.
    
    Best regards,
    [Your Name]
    """,
    """Dear Marketing Director,
    
    I'll review the marketing materials and provide feedback by EOD Friday as requested.
    
    I'll focus on the press release copy and social media campaign schedule in particular.
    
    Best regards,
    [Your Name]
    """,
]


def create_mock_strategy_changes_table():
    """Create prompt_strategy_changes table if it doesn't exist."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS prompt_strategy_changes (
                        id SERIAL PRIMARY KEY,
                        task VARCHAR(50) NOT NULL,
                        old_strategy VARCHAR(50) NOT NULL,
                        new_strategy VARCHAR(50) NOT NULL,
                        change_reason TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                conn.commit()
        logging.info("Created prompt_strategy_changes table if it didn't exist")
        return True
    except Exception as e:
        logging.error(f"Error creating prompt_strategy_changes table: {e}")
        return False


def clear_existing_data():
    """Clear existing mock data to start fresh."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Clear the user_feedback table
                cur.execute("DELETE FROM user_feedback")
                feedback_count = cur.rowcount

                # Clear the prompt_strategy_changes table
                cur.execute("DELETE FROM prompt_strategy_changes")
                changes_count = cur.rowcount

                conn.commit()

        logging.info(
            f"Cleared {feedback_count} existing feedback records and {changes_count} strategy change records"
        )
        return True
    except Exception as e:
        logging.error(f"Error clearing existing data: {e}")
        return False


def insert_mock_feedback_data():
    """Insert mock feedback data showing performance degradation over time."""
    try:
        # Create mock feedback entries
        records = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=DAYS_RANGE)

        # MODIFIED: Create a specific distribution of task performance
        # Make draft_reply performance particularly bad to trigger optimization
        task_performance_bias = {
            "summary": 0.0,  # Normal degradation
            "action_items": -0.1,  # Slightly worse performance
            "draft_reply": -0.2,  # Significantly worse performance
        }

        for i in range(NUM_RECORDS):
            # Calculate date - distribute records evenly across the time range
            progress = i / NUM_RECORDS
            days_offset = DAYS_RANGE * progress
            record_date = start_date + timedelta(days=days_offset)

            # Calculate positive feedback probability - decreases over time
            base_probability = INITIAL_POSITIVE_RATIO - (
                (INITIAL_POSITIVE_RATIO - FINAL_POSITIVE_RATIO) * progress
            )

            # Apply task-specific bias for different degradation rates
            summary_probability = min(
                1.0, max(0.0, base_probability + task_performance_bias["summary"])
            )
            action_items_probability = min(
                1.0, max(0.0, base_probability + task_performance_bias["action_items"])
            )
            draft_reply_probability = min(
                1.0, max(0.0, base_probability + task_performance_bias["draft_reply"])
            )

            # MODIFIED: Last 15 records (recent ones) should show very poor performance for at least one task
            if i >= (NUM_RECORDS - 15):
                # Make at least one task perform poorly in recent records
                if i % 3 == 0:
                    summary_probability *= 0.5  # 50% of normal performance
                elif i % 3 == 1:
                    action_items_probability *= 0.5
                else:
                    draft_reply_probability *= 0.5

            # Randomly select content
            subject_index = random.randint(0, len(SUBJECTS) - 1)
            body_index = random.randint(0, len(BODIES) - 1)

            # Generate feedback values with task-specific probabilities
            summary_feedback = 1 if random.random() < summary_probability else 0
            action_items_feedback = (
                1 if random.random() < action_items_probability else 0
            )
            draft_reply_feedback = 1 if random.random() < draft_reply_probability else 0

            # Select prompt strategy - use alternate more in later records
            strategy_is_alternate = random.random() > (0.7 - 0.4 * progress)
            prompt_strategy = "alternate" if strategy_is_alternate else "default"

            # Create record
            record = {
                "user_email": random.choice(USERS),
                "message_id": f"mock-{uuid.uuid4()}",
                "thread_id": f"thread-{random.randint(1, 100)}",
                "from_email": "sender@example.com",
                "to_email": random.choice(USERS),
                "subject": SUBJECTS[subject_index],
                "body": BODIES[body_index],
                "messages_count": random.randint(1, 5),
                "date": record_date.date(),
                "summary": SUMMARIES[body_index],
                "action_items": ACTION_ITEMS[body_index],
                "draft_reply": DRAFT_REPLIES[body_index],
                "summary_feedback": summary_feedback,
                "action_items_feedback": action_items_feedback,
                "draft_reply_feedback": draft_reply_feedback,
                "prompt_strategy_summary": prompt_strategy,
                "prompt_strategy_action_items": prompt_strategy,
                "prompt_strategy_draft_reply": prompt_strategy,
            }

            records.append(record)

        # Insert records into database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if we need to create a user_feedback table
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'user_feedback'
                    )
                """
                )

                table_exists = cur.fetchone()["exists"]

                if not table_exists:
                    # Create the table if it doesn't exist
                    cur.execute(
                        """
                        CREATE TABLE user_feedback (
                            id SERIAL PRIMARY KEY,
                            user_email VARCHAR(100) NOT NULL,
                            message_id VARCHAR(100) NOT NULL,
                            thread_id VARCHAR(100) NOT NULL,
                            from_email VARCHAR(100),
                            to_email VARCHAR(100),
                            subject TEXT,
                            body TEXT,
                            messages_count INTEGER,
                            date DATE,
                            summary TEXT,
                            action_items TEXT,
                            draft_reply TEXT,
                            summary_feedback INTEGER,
                            action_items_feedback INTEGER,
                            draft_reply_feedback INTEGER,
                            prompt_strategy_summary VARCHAR(50),
                            prompt_strategy_action_items VARCHAR(50),
                            prompt_strategy_draft_reply VARCHAR(50),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """
                    )
                    logging.info("Created user_feedback table")

                # Insert all records
                for record in records:
                    # Insert the record
                    cur.execute(
                        """
                        INSERT INTO user_feedback (
                            user_email, message_id, thread_id, from_email, to_email,
                            subject, body, messages_count, date, summary, action_items,
                            draft_reply, summary_feedback, action_items_feedback,
                            draft_reply_feedback, prompt_strategy_summary,
                            prompt_strategy_action_items, prompt_strategy_draft_reply
                        ) VALUES (
                            %(user_email)s, %(message_id)s, %(thread_id)s, %(from_email)s,
                            %(to_email)s, %(subject)s, %(body)s, %(messages_count)s,
                            %(date)s, %(summary)s, %(action_items)s, %(draft_reply)s,
                            %(summary_feedback)s, %(action_items_feedback)s,
                            %(draft_reply_feedback)s, %(prompt_strategy_summary)s,
                            %(prompt_strategy_action_items)s, %(prompt_strategy_draft_reply)s
                        )
                    """,
                        record,
                    )

                conn.commit()

        logging.info(f"Successfully inserted {len(records)} mock feedback records")
        return len(records)

    except Exception as e:
        logging.error(f"Error inserting mock feedback data: {e}")
        return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logging.info("Creating strategy changes table if needed...")
    create_mock_strategy_changes_table()

    # Ask before clearing existing data
    clear_existing = (
        input("Clear existing mock data before generating new records? (y/n): ").lower()
        == "y"
    )
    if clear_existing:
        logging.info("Clearing existing data...")
        clear_existing_data()

    logging.info("Generating and inserting mock feedback data...")
    num_records = insert_mock_feedback_data()

    logging.info(f"Completed: {num_records} mock records inserted")

    # Print a reminder about what to do next
    print("\nNext steps:")
    print("1. Restart your Flask app if it's running")
    print("2. Run the demo test script to see the optimization in action:")
    print("   python demo_test.py --action demo --local")

#!/usr/bin/env python3
"""
Initialize or reset the database schema for user-specific prompt strategies.
This script creates the necessary tables and indexes if they don't exist,
and can also reset the database by clearing existing data.
"""

import os
import sys
import logging
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from db_connection import get_db_connection, DB_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def reset_database(confirm=False):
    """Reset the database by dropping and recreating tables, or truncating tables."""
    if not confirm:
        logging.warning(
            "Database reset requires confirmation. Use --reset-confirmed flag."
        )
        return False

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Clear the prompt_strategy_changes table
                logging.info("Truncating prompt_strategy_changes table...")
                cur.execute("TRUNCATE TABLE prompt_strategy_changes")

                # Drop and recreate user_prompt_strategies table
                logging.info("Dropping user_prompt_strategies table...")
                cur.execute("DROP TABLE IF EXISTS user_prompt_strategies")

                # Clear test users from user_feedback
                logging.info("Clearing test users from user_feedback table...")
                cur.execute(
                    """
                    DELETE FROM user_feedback
                    WHERE user_email LIKE 'test_user_%' 
                    OR user_email LIKE 'scheduled_test_user_%'
                """
                )

                # We don't reset all user_feedback as it contains valuable historical data
                # Just update the strategy-related columns to default for remaining users
                logging.info("Resetting strategy columns in user_feedback table...")
                cur.execute(
                    """
                    UPDATE user_feedback
                    SET prompt_strategy_summary = 'default',
                        prompt_strategy_action_items = 'default',
                        prompt_strategy_draft_reply = 'default'
                """
                )

                conn.commit()

        logging.info("Database reset completed. Ready for reinitialization.")
        return True
    except Exception as e:
        logging.error(f"Error resetting database: {e}")
        logging.exception(e)
        return False


def create_user_prompt_strategies_table():
    """Create user_prompt_strategies table if it doesn't exist."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Create the user_prompt_strategies table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_prompt_strategies (
                        id SERIAL PRIMARY KEY,
                        user_email VARCHAR(100) NOT NULL,
                        summary_strategy VARCHAR(50) NOT NULL DEFAULT 'default',
                        action_items_strategy VARCHAR(50) NOT NULL DEFAULT 'default',
                        draft_reply_strategy VARCHAR(50) NOT NULL DEFAULT 'default',
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_email)
                    )
                """
                )

                # Create indexes
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_user_prompt_strategies_email 
                    ON user_prompt_strategies(user_email)
                """
                )

                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_user_prompt_strategies_updated 
                    ON user_prompt_strategies(last_updated)
                """
                )

                # Add comments
                cur.execute(
                    """
                    COMMENT ON TABLE user_prompt_strategies IS 
                    'Stores user-specific prompt strategies based on performance metrics'
                """
                )

                conn.commit()

        logging.info("Created user_prompt_strategies table if it didn't exist")
        return True
    except Exception as e:
        logging.error(f"Error creating user_prompt_strategies table: {e}")
        logging.exception(e)
        return False


def modify_prompt_strategy_changes_table():
    """Modify prompt_strategy_changes table to track only user-specific changes."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if the table exists
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'prompt_strategy_changes'
                    )
                """
                )

                table_exists = cur.fetchone()["exists"]

                if not table_exists:
                    # Create the table if it doesn't exist
                    cur.execute(
                        """
                        CREATE TABLE prompt_strategy_changes (
                            id SERIAL PRIMARY KEY,
                            task VARCHAR(50) NOT NULL,
                            old_strategy VARCHAR(50) NOT NULL,
                            new_strategy VARCHAR(50) NOT NULL,
                            change_reason TEXT,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            user_email VARCHAR(100) NOT NULL
                        )
                    """
                    )
                    logging.info("Created prompt_strategy_changes table")
                else:
                    # Ensure user_email column exists
                    cur.execute(
                        """
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns 
                            WHERE table_name = 'prompt_strategy_changes' AND column_name = 'user_email'
                        )
                    """
                    )

                    column_exists = cur.fetchone()["exists"]

                    if not column_exists:
                        cur.execute(
                            """
                            ALTER TABLE prompt_strategy_changes 
                            ADD COLUMN user_email VARCHAR(100) NOT NULL DEFAULT 'system@example.com'
                        """
                        )
                        logging.info(
                            "Added user_email column to prompt_strategy_changes table"
                        )

                # Create index for user_email
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_prompt_strategy_changes_user 
                    ON prompt_strategy_changes(user_email)
                """
                )

                # Create index for timestamp
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_prompt_strategy_changes_timestamp 
                    ON prompt_strategy_changes(timestamp)
                """
                )

                conn.commit()

        return True
    except Exception as e:
        logging.error(f"Error modifying prompt_strategy_changes table: {e}")
        logging.exception(e)
        return False


def initialize_sample_user_strategies():
    """Initialize strategies for a fixed set of sample users."""
    try:
        # Fixed set of sample users that will always be initialized
        sample_users = [
            "user1@example.com",
            "user2@example.com",
            "try8200@gmail.com",
            "shubhdesai111@gmail.com",
        ]

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for user in sample_users:
                    # Check if user already has strategies
                    cur.execute(
                        "SELECT COUNT(*) as count FROM user_prompt_strategies WHERE user_email = %s",
                        (user,),
                    )

                    if cur.fetchone()["count"] == 0:
                        # Insert default strategies
                        cur.execute(
                            """
                            INSERT INTO user_prompt_strategies (
                                user_email, summary_strategy, action_items_strategy, draft_reply_strategy, 
                                last_updated
                            ) VALUES (%s, %s, %s, %s, NOW())
                            ON CONFLICT (user_email) DO UPDATE
                            SET summary_strategy = 'default',
                                action_items_strategy = 'default',
                                draft_reply_strategy = 'default'
                        """,
                            (user, "default", "default", "default"),
                        )

                        logging.info(f"Initialized default strategies for user: {user}")

                conn.commit()

        return True
    except Exception as e:
        logging.error(f"Error initializing sample user strategies: {e}")
        logging.exception(e)
        return False


def main():
    """Main function to initialize or reset the database."""
    parser = argparse.ArgumentParser(description="Initialize or reset database schema")
    parser.add_argument(
        "--reset", action="store_true", help="Reset the database before initialization"
    )
    parser.add_argument(
        "--reset-confirmed", action="store_true", help="Confirm database reset"
    )
    args = parser.parse_args()

    if args.reset:
        logging.info("Starting database reset...")
        if not reset_database(confirm=args.reset_confirmed):
            if not args.reset_confirmed:
                logging.error(
                    "Database reset aborted. Use --reset-confirmed to confirm reset."
                )
            else:
                logging.error("Database reset failed.")
            return False

    logging.info("Starting database initialization...")

    # Step 1: Create user_prompt_strategies table
    if not create_user_prompt_strategies_table():
        logging.error("Failed to create user_prompt_strategies table")
        return False

    # Step 2: Modify prompt_strategy_changes table
    if not modify_prompt_strategy_changes_table():
        logging.error("Failed to modify prompt_strategy_changes table")
        return False

    # Step 3: Initialize sample user strategies
    if not initialize_sample_user_strategies():
        logging.error("Failed to initialize sample user strategies")
        return False

    logging.info("Database initialization completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

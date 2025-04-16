#!/usr/bin/env python3
"""
Demo script for User Performance Metrics and Optimization

This script demonstrates the enhanced performance monitoring system with
user-specific strategy optimization. It shows how the system tracks metrics
on a per-user basis and optimizes prompt strategies accordingly.
"""

import requests
import json
import time
import argparse
import logging
from colorama import Fore, Style, init

# Initialize colorama
init()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Default base URL - update this to your deployed Cloud Run service URL
DEFAULT_BASE_URL = "https://email-assistant-673808915782.us-central1.run.app"
LOCAL_BASE_URL = "http://localhost:8000"


def print_json(json_data):
    """Print JSON data in a formatted way"""
    print(json.dumps(json_data, indent=2))


def check_user_performance(base_url, user_email=None):
    """Test the performance check endpoint with user-specific metrics"""
    logging.info(
        f"Checking performance metrics for {'all users' if user_email is None else user_email}..."
    )
    url = f"{base_url}/check_performance"

    if user_email:
        url += f"?user_email={user_email}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        logging.info("Performance metrics retrieved successfully!")

        # Print results in a more readable format
        print(f"\n{Fore.CYAN}=== GLOBAL PERFORMANCE METRICS ==={Style.RESET_ALL}")
        for task, metrics in data.get("global_metrics", {}).items():
            score = metrics.get("performance_score")
            total = metrics.get("total_feedback", 0)
            positive = metrics.get("positive_feedback", 0)
            below_threshold = metrics.get("below_threshold", False)

            task_name = task.upper().replace("_", " ")
            print(f"\n{Fore.YELLOW}Task: {task_name}{Style.RESET_ALL}")

            if score is not None:
                score_pct = score * 100
                # Color-code based on performance
                if score_pct >= 70:
                    score_color = Fore.GREEN
                elif score_pct >= 60:
                    score_color = Fore.YELLOW
                else:
                    score_color = Fore.RED

                print(
                    f"  Performance Score: {score_color}{score_pct:.1f}%{Style.RESET_ALL}"
                )
            else:
                print(
                    f"  Performance Score: {Fore.YELLOW}Not enough data{Style.RESET_ALL}"
                )

            print(f"  Feedback: {positive}/{total} positive")

            if below_threshold:
                print(f"  Status: {Fore.RED}⚠️ BELOW THRESHOLD{Style.RESET_ALL}")
            else:
                print(f"  Status: {Fore.GREEN}✅ OK{Style.RESET_ALL}")

        # Print user-specific metrics
        if "user_metrics" in data and data["user_metrics"]:
            print(
                f"\n{Fore.CYAN}=== USER-SPECIFIC PERFORMANCE METRICS ==={Style.RESET_ALL}"
            )

            for user, user_data in data.get("user_metrics", {}).items():
                print(f"\n{Fore.MAGENTA}User: {user}{Style.RESET_ALL}")

                for task, metrics in user_data.items():
                    score = metrics.get("performance_score")
                    total = metrics.get("total_feedback", 0)
                    positive = metrics.get("positive_feedback", 0)
                    below_threshold = metrics.get("below_threshold", False)

                    task_name = task.upper().replace("_", " ")
                    print(f"  {Fore.YELLOW}Task: {task_name}{Style.RESET_ALL}")

                    if score is not None:
                        score_pct = score * 100
                        # Color-code based on performance
                        if score_pct >= 70:
                            score_color = Fore.GREEN
                        elif score_pct >= 60:
                            score_color = Fore.YELLOW
                        else:
                            score_color = Fore.RED

                        print(
                            f"    Performance Score: {score_color}{score_pct:.1f}%{Style.RESET_ALL}"
                        )
                    else:
                        print(
                            f"    Performance Score: {Fore.YELLOW}Not enough data{Style.RESET_ALL}"
                        )

                    print(f"    Feedback: {positive}/{total} positive")

                    if below_threshold:
                        print(
                            f"    Status: {Fore.RED}⚠️ BELOW THRESHOLD{Style.RESET_ALL}"
                        )
                    else:
                        print(f"    Status: {Fore.GREEN}✅ OK{Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}=== CURRENT PROMPT STRATEGIES ==={Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Global Strategies:{Style.RESET_ALL}")
        for task, strategy in data.get("global_strategies", {}).items():
            strategy_color = Fore.GREEN if strategy == "default" else Fore.YELLOW
            print(f"  {task}: {strategy_color}{strategy}{Style.RESET_ALL}")

        if "user_strategies" in data and data["user_strategies"]:
            print(f"\n{Fore.YELLOW}User-Specific Strategies:{Style.RESET_ALL}")
            for user, strategies in data.get("user_strategies", {}).items():
                print(f"  {Fore.MAGENTA}User: {user}{Style.RESET_ALL}")
                for task, strategy in strategies.items():
                    strategy_color = (
                        Fore.GREEN if strategy == "default" else Fore.YELLOW
                    )
                    print(f"    {task}: {strategy_color}{strategy}{Style.RESET_ALL}")

        if data.get("tasks_below_threshold"):
            print(
                f"\n{Fore.RED}⚠️ Global tasks below threshold: {', '.join(data.get('tasks_below_threshold'))}{Style.RESET_ALL}"
            )
            print("  These tasks are candidates for global prompt optimization")

        if data.get("users_below_threshold"):
            print(f"\n{Fore.RED}⚠️ Users with tasks below threshold:{Style.RESET_ALL}")
            for user, tasks in data.get("users_below_threshold", {}).items():
                print(f"  {Fore.MAGENTA}{user}{Style.RESET_ALL}: {', '.join(tasks)}")
            print(
                "  These user-task combinations are candidates for user-specific optimization"
            )

        return data
    except Exception as e:
        logging.error(f"Error checking performance: {e}")
        return None


def optimize_user_prompts(base_url, user_email=None):
    """Test the prompt optimization endpoint with user-specific targeting"""
    logging.info(
        f"Triggering prompt optimization for {'all users' if user_email is None else user_email}..."
    )
    url = f"{base_url}/optimize_prompts"

    payload = {}
    if user_email:
        payload = {"user_email": user_email}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        logging.info("Prompt optimization triggered successfully!")

        # Print results in a more readable format
        print(f"\n{Fore.CYAN}=== OPTIMIZATION RESULTS ==={Style.RESET_ALL}")

        # Global changes
        global_changes = data.get("global_changes", [])
        if global_changes:
            print(f"\n{Fore.GREEN}Global changes made:{Style.RESET_ALL}")
            for change in global_changes:
                task = change["task"]
                old = change["old_strategy"]
                new = change["new_strategy"]
                score = change.get("performance_score", 0) * 100

                print(
                    f"  {Fore.YELLOW}{task}{Style.RESET_ALL}: {old} → {Fore.GREEN}{new}{Style.RESET_ALL}"
                )
                print(f"    Performance score: {Fore.RED}{score:.1f}%{Style.RESET_ALL}")
        else:
            print(
                f"\n{Fore.YELLOW}No global changes were needed or possible at this time.{Style.RESET_ALL}"
            )

        # User-specific changes
        user_changes = data.get("user_changes", [])
        if user_changes:
            print(f"\n{Fore.GREEN}User-specific changes made:{Style.RESET_ALL}")
            user_change_map = {}

            # Group changes by user
            for change in user_changes:
                user = change["user_email"]
                if user not in user_change_map:
                    user_change_map[user] = []
                user_change_map[user].append(change)

            # Display changes by user
            for user, changes in user_change_map.items():
                print(f"  {Fore.MAGENTA}User: {user}{Style.RESET_ALL}")
                for change in changes:
                    task = change["task"]
                    old = change["old_strategy"]
                    new = change["new_strategy"]
                    score = change.get("performance_score", 0) * 100

                    print(
                        f"    {Fore.YELLOW}{task}{Style.RESET_ALL}: {old} → {Fore.GREEN}{new}{Style.RESET_ALL}"
                    )
                    print(
                        f"      Performance score: {Fore.RED}{score:.1f}%{Style.RESET_ALL}"
                    )
        else:
            print(
                f"\n{Fore.YELLOW}No user-specific changes were needed or possible at this time.{Style.RESET_ALL}"
            )

        # Show tasks below threshold
        if data.get("tasks_below_threshold"):
            print(
                f"\n{Fore.RED}Tasks below threshold: {', '.join(data.get('tasks_below_threshold'))}{Style.RESET_ALL}"
            )

        # Show users below threshold
        if data.get("users_below_threshold"):
            print(f"\n{Fore.RED}Users with tasks below threshold:{Style.RESET_ALL}")
            for user, tasks in data.get("users_below_threshold", {}).items():
                print(f"  {Fore.MAGENTA}{user}{Style.RESET_ALL}: {', '.join(tasks)}")

        return data
    except Exception as e:
        logging.error(f"Error optimizing prompts: {e}")
        return None


def get_optimization_history(base_url, user_email=None):
    """Test the optimization history endpoint with user filtering"""
    logging.info(
        f"Retrieving optimization history for {'all users' if user_email is None else user_email}..."
    )
    url = f"{base_url}/get_optimization_history"

    if user_email:
        url += f"?user_email={user_email}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        logging.info("Optimization history retrieved successfully!")

        # Print results in a more readable format
        print(f"\n{Fore.CYAN}=== OPTIMIZATION HISTORY ==={Style.RESET_ALL}")

        history = data.get("history", [])
        if history:
            # Group changes by scope (global vs user-specific)
            global_changes = [entry for entry in history if entry["scope"] == "global"]
            user_changes = [
                entry for entry in history if entry["scope"] == "user-specific"
            ]

            if global_changes:
                print(f"\n{Fore.YELLOW}Global Changes:{Style.RESET_ALL}")
                for entry in global_changes:
                    print(f"\n  Change ID: {entry['id']}")
                    print(f"  Task: {entry['task']}")
                    print(
                        f"  Change: {entry['old_strategy']} → {Fore.GREEN}{entry['new_strategy']}{Style.RESET_ALL}"
                    )
                    print(f"  Reason: {entry['change_reason']}")
                    print(f"  Timestamp: {entry['timestamp']}")

            if user_changes:
                print(f"\n{Fore.YELLOW}User-Specific Changes:{Style.RESET_ALL}")
                # Group by user
                user_map = {}
                for entry in user_changes:
                    user = entry["user_email"]
                    if user not in user_map:
                        user_map[user] = []
                    user_map[user].append(entry)

                for user, entries in user_map.items():
                    print(f"\n  {Fore.MAGENTA}User: {user}{Style.RESET_ALL}")
                    for entry in entries:
                        print(f"    Change ID: {entry['id']}")
                        print(f"    Task: {entry['task']}")
                        print(
                            f"    Change: {entry['old_strategy']} → {Fore.GREEN}{entry['new_strategy']}{Style.RESET_ALL}"
                        )
                        print(f"    Reason: {entry['change_reason']}")
                        print(f"    Timestamp: {entry['timestamp']}")
        else:
            print(f"\n{Fore.YELLOW}No optimization history found.{Style.RESET_ALL}")

        return data
    except Exception as e:
        logging.error(f"Error retrieving optimization history: {e}")
        return None


def get_user_strategies(base_url, user_email):
    """Test the user strategies endpoint"""
    if not user_email:
        logging.error("User email is required")
        return None

    logging.info(f"Retrieving prompt strategies for user: {user_email}...")
    url = f"{base_url}/get_user_strategies?user_email={user_email}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        logging.info("User strategies retrieved successfully!")

        # Print results in a more readable format
        print(f"\n{Fore.CYAN}=== USER PROMPT STRATEGIES ==={Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}User: {user_email}{Style.RESET_ALL}")

        for task, strategy in data.get("strategies", {}).items():
            strategy_color = Fore.GREEN if strategy == "default" else Fore.YELLOW
            print(f"  {task}: {strategy_color}{strategy}{Style.RESET_ALL}")

        return data
    except Exception as e:
        logging.error(f"Error retrieving user strategies: {e}")
        return None


def run_full_demo(base_url):
    """Run through the full demonstration sequence"""
    print(
        f"\n{Fore.MAGENTA}======================================================{Style.RESET_ALL}"
    )
    print(
        f"{Fore.MAGENTA}  USER-SPECIFIC PERFORMANCE MONITORING DEMO  {Style.RESET_ALL}"
    )
    print(
        f"{Fore.MAGENTA}======================================================{Style.RESET_ALL}\n"
    )

    print(
        f"{Fore.CYAN}This demo will show how the system monitors user feedback both{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}globally and on a per-user basis, detecting performance issues{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}and automatically optimizing prompt strategies at both levels.{Style.RESET_ALL}\n"
    )

    input(f"{Fore.YELLOW}Press Enter to begin the demonstration...{Style.RESET_ALL}")

    # Step 1: Check current performance for all users
    print(
        f"\n{Fore.MAGENTA}STEP 1: Checking global and user-specific performance metrics{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}The system analyzes user feedback at both global and user-specific{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}levels to calculate performance scores for each task type.{Style.RESET_ALL}\n"
    )

    input(
        f"{Fore.YELLOW}Press Enter to check current performance for all users...{Style.RESET_ALL}"
    )
    check_user_performance(base_url)

    # Step 2: Check current performance for a specific user
    sample_user = "try8200@gmail.com"  # Using a sample user from your system
    print(
        f"\n{Fore.MAGENTA}STEP 2: Checking performance metrics for a specific user{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}We can also focus on a single user to see their specific metrics{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}and determine if they need personalized prompt strategies.{Style.RESET_ALL}\n"
    )

    input(
        f"{Fore.YELLOW}Press Enter to check performance for user {sample_user}...{Style.RESET_ALL}"
    )
    check_user_performance(base_url, sample_user)

    # Step 3: Get current user strategies
    print(
        f"\n{Fore.MAGENTA}STEP 3: Retrieving current user-specific strategies{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}The system maintains personalized prompt strategies for each user{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}that can override the global strategies when needed.{Style.RESET_ALL}\n"
    )

    input(
        f"{Fore.YELLOW}Press Enter to get strategies for user {sample_user}...{Style.RESET_ALL}"
    )
    get_user_strategies(base_url, sample_user)

    # Step 4: Optimize prompts for all users
    print(
        f"\n{Fore.MAGENTA}STEP 4: Triggering prompt optimization for all users{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}Now we'll trigger the optimization process for all users.{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}The system will analyze both global and user-specific metrics{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}and update strategies at both levels where needed.{Style.RESET_ALL}\n"
    )

    input(
        f"{Fore.YELLOW}Press Enter to optimize prompts for all users...{Style.RESET_ALL}"
    )
    optimize_user_prompts(base_url)

    # Step 5: Optimize prompts for a specific user
    print(
        f"\n{Fore.MAGENTA}STEP 5: Triggering prompt optimization for a specific user{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}We can also target optimization for a single user if needed.{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}This is useful for addressing user-specific performance issues.{Style.RESET_ALL}\n"
    )

    input(
        f"{Fore.YELLOW}Press Enter to optimize prompts for user {sample_user}...{Style.RESET_ALL}"
    )
    optimize_user_prompts(base_url, sample_user)

    # Step 6: Check optimization history
    print(f"\n{Fore.MAGENTA}STEP 6: Reviewing optimization history{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}The system maintains a history of all prompt strategy changes,{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}both global and user-specific, for transparency and auditing.{Style.RESET_ALL}\n"
    )

    input(
        f"{Fore.YELLOW}Press Enter to view optimization history for all users...{Style.RESET_ALL}"
    )
    get_optimization_history(base_url)

    # Step 7: Check user-specific optimization history
    print(
        f"\n{Fore.MAGENTA}STEP 7: Reviewing user-specific optimization history{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}We can also filter the history to see changes for a specific user.{Style.RESET_ALL}\n"
    )

    input(
        f"{Fore.YELLOW}Press Enter to view optimization history for user {sample_user}...{Style.RESET_ALL}"
    )
    get_optimization_history(base_url, sample_user)

    # Step 8: Verify performance improved after optimization
    print(
        f"\n{Fore.MAGENTA}STEP 8: Verifying performance improvements{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}Finally, let's check the performance metrics again to confirm that{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}prompt strategies have been updated appropriately.{Style.RESET_ALL}\n"
    )

    input(
        f"{Fore.YELLOW}Press Enter to check updated performance metrics...{Style.RESET_ALL}"
    )
    check_user_performance(base_url)

    # Conclusion
    print(
        f"\n{Fore.MAGENTA}======================================================{Style.RESET_ALL}"
    )
    print(
        f"{Fore.MAGENTA}                 DEMONSTRATION COMPLETE                 {Style.RESET_ALL}"
    )
    print(
        f"{Fore.MAGENTA}======================================================{Style.RESET_ALL}\n"
    )

    print(
        f"{Fore.CYAN}This demonstration showed how the MailMate system:{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}1. Monitors performance through user feedback at both global and user-specific levels{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}2. Detects when performance drops below threshold for specific users{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}3. Optimizes prompt strategies at both global and user-specific levels{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}4. Tracks changes for transparency and analysis{Style.RESET_ALL}\n"
    )

    print(
        f"{Fore.CYAN}In a production environment, these checks run automatically{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}on a daily schedule via Cloud Scheduler, ensuring that{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}each user gets the most effective prompt strategy.{Style.RESET_ALL}\n"
    )

    logging.info("Full demonstration sequence completed!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Demo for User-Specific Performance Monitoring"
    )
    parser.add_argument(
        "--action",
        choices=[
            "check",
            "check-user",
            "optimize",
            "optimize-user",
            "history",
            "user-strategies",
            "demo",
        ],
        default="demo",
        help="Action to perform",
    )
    parser.add_argument(
        "--user",
        type=str,
        help="User email for user-specific operations",
        default="try8200@gmail.com",
    )
    parser.add_argument(
        "--local", action="store_true", help="Use localhost instead of deployed URL"
    )

    args = parser.parse_args()

    # Determine base URL
    base_url = LOCAL_BASE_URL if args.local else DEFAULT_BASE_URL

    logging.info(f"Using base URL: {base_url}")

    # Perform the requested action
    if args.action == "check":
        check_user_performance(base_url)
    elif args.action == "check-user":
        check_user_performance(base_url, args.user)
    elif args.action == "optimize":
        optimize_user_prompts(base_url)
    elif args.action == "optimize-user":
        optimize_user_prompts(base_url, args.user)
    elif args.action == "history":
        get_optimization_history(base_url)
    elif args.action == "user-strategies":
        get_user_strategies(base_url, args.user)
    elif args.action == "demo":
        run_full_demo(base_url)


if __name__ == "__main__":
    main()

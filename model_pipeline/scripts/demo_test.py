#!/usr/bin/env python3
"""
Demo Testing Script for Email Assistant Performance Monitoring
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


def check_performance(base_url):
    """Test the performance check endpoint"""
    logging.info("Checking current performance metrics...")
    url = f"{base_url}/check_performance"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        logging.info("Performance metrics retrieved successfully!")

        # Print results in a more readable format
        print(f"\n{Fore.CYAN}=== PERFORMANCE METRICS ==={Style.RESET_ALL}")
        for task, metrics in data.get("metrics", {}).items():
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

            # Show trend information if available
            if "trend" in metrics and metrics["trend"] is not None:
                trend = metrics["trend"] * 100  # Convert to percentage
                trend_direction = metrics.get("trend_direction")

                if trend_direction == "improving":
                    trend_color = Fore.GREEN
                    trend_arrow = "↑"
                elif trend_direction == "declining":
                    trend_color = Fore.RED
                    trend_arrow = "↓"
                else:
                    trend_color = Fore.YELLOW
                    trend_arrow = "→"

                print(
                    f"  Trend: {trend_color}{trend_arrow} {trend:+.1f}%{Style.RESET_ALL} ({trend_direction})"
                )

            if below_threshold:
                print(f"  Status: {Fore.RED}⚠️ BELOW THRESHOLD{Style.RESET_ALL}")
            else:
                print(f"  Status: {Fore.GREEN}✅ OK{Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}=== CURRENT PROMPT STRATEGIES ==={Style.RESET_ALL}")
        for task, strategy in data.get("current_strategies", {}).items():
            strategy_color = Fore.GREEN if strategy == "default" else Fore.YELLOW
            print(f"  {task}: {strategy_color}{strategy}{Style.RESET_ALL}")

        if data.get("tasks_below_threshold"):
            print(
                f"\n{Fore.RED}⚠️ Tasks below threshold: {', '.join(data.get('tasks_below_threshold'))}{Style.RESET_ALL}"
            )
            print("  These tasks are candidates for prompt optimization")

        return data
    except Exception as e:
        logging.error(f"Error checking performance: {e}")
        return None


def optimize_prompts(base_url):
    """Test the prompt optimization endpoint"""
    logging.info("Triggering prompt optimization...")
    url = f"{base_url}/optimize_prompts"

    try:
        response = requests.post(url)
        response.raise_for_status()
        data = response.json()

        logging.info("Prompt optimization triggered successfully!")

        # Print results in a more readable format
        print(f"\n{Fore.CYAN}=== OPTIMIZATION RESULTS ==={Style.RESET_ALL}")

        changes = data.get("changes_made", [])
        if changes:
            print(f"\n{Fore.GREEN}Changes made:{Style.RESET_ALL}")
            for change in changes:
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
                f"\n{Fore.YELLOW}No changes were needed or possible at this time.{Style.RESET_ALL}"
            )

        below_threshold = data.get("tasks_below_threshold", [])
        if below_threshold:
            print(
                f"\n{Fore.RED}Tasks below threshold: {', '.join(below_threshold)}{Style.RESET_ALL}"
            )

        return data
    except Exception as e:
        logging.error(f"Error optimizing prompts: {e}")
        return None


def get_optimization_history(base_url):
    """Test the optimization history endpoint"""
    logging.info("Retrieving optimization history...")
    url = f"{base_url}/get_optimization_history"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        logging.info("Optimization history retrieved successfully!")

        # Print results in a more readable format
        print(f"\n{Fore.CYAN}=== OPTIMIZATION HISTORY ==={Style.RESET_ALL}")

        history = data.get("history", [])
        if history:
            for entry in history:
                print(f"\n{Fore.YELLOW}Change ID: {entry['id']}{Style.RESET_ALL}")
                print(f"  Task: {entry['task']}")
                print(
                    f"  Change: {entry['old_strategy']} → {Fore.GREEN}{entry['new_strategy']}{Style.RESET_ALL}"
                )
                print(f"  Reason: {entry['change_reason']}")
                print(f"  Timestamp: {entry['timestamp']}")
        else:
            print(f"\n{Fore.YELLOW}No optimization history found.{Style.RESET_ALL}")

        return data
    except Exception as e:
        logging.error(f"Error retrieving optimization history: {e}")
        return None


def trigger_scheduled_check(base_url):
    """Test the scheduled check endpoint"""
    logging.info("Triggering scheduled performance check...")
    url = f"{base_url}/scheduled_check"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        logging.info("Scheduled check completed successfully!")

        # Print basic results
        print(f"\n{Fore.CYAN}=== SCHEDULED CHECK RESULTS ==={Style.RESET_ALL}")

        changes = data.get("changes_made", [])
        if changes:
            print(f"\n{Fore.GREEN}Changes made:{Style.RESET_ALL}")
            for change in changes:
                print(
                    f"  {Fore.YELLOW}{change['task']}{Style.RESET_ALL}: {change['old_strategy']} → {Fore.GREEN}{change['new_strategy']}{Style.RESET_ALL}"
                )
        else:
            print(
                f"\n{Fore.YELLOW}No changes were made during this scheduled check.{Style.RESET_ALL}"
            )

        return data
    except Exception as e:
        logging.error(f"Error triggering scheduled check: {e}")
        return None


def run_full_demo(base_url):
    """Run through the full demonstration sequence"""
    print(
        f"\n{Fore.MAGENTA}======================================================{Style.RESET_ALL}"
    )
    print(
        f"{Fore.MAGENTA}  MAILMATE PERFORMANCE MONITORING SYSTEM DEMONSTRATION  {Style.RESET_ALL}"
    )
    print(
        f"{Fore.MAGENTA}======================================================{Style.RESET_ALL}\n"
    )

    print(
        f"{Fore.CYAN}This demo will show how the system monitors user feedback,{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}detects performance issues, and automatically optimizes{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}prompt strategies when performance drops below threshold.{Style.RESET_ALL}\n"
    )

    input(f"{Fore.YELLOW}Press Enter to begin the demonstration...{Style.RESET_ALL}")

    # Step 1: Check current performance
    print(
        f"\n{Fore.MAGENTA}STEP 1: Checking current performance metrics{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}The system regularly analyzes user feedback to calculate{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}performance scores for each task type. A score below 70%{Style.RESET_ALL}"
    )
    print(f"{Fore.CYAN}will trigger prompt strategy optimization.{Style.RESET_ALL}\n")

    input(f"{Fore.YELLOW}Press Enter to check current performance...{Style.RESET_ALL}")
    check_performance(base_url)

    # Step 2: Get optimization history (before changes)
    print(f"\n{Fore.MAGENTA}STEP 2: Reviewing optimization history{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}The system maintains a history of all prompt strategy changes,{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}including when they occurred and why they were made.{Style.RESET_ALL}\n"
    )

    input(f"{Fore.YELLOW}Press Enter to view optimization history...{Style.RESET_ALL}")
    get_optimization_history(base_url)

    # Step 3: Optimize prompts
    print(f"\n{Fore.MAGENTA}STEP 3: Triggering prompt optimization{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}Now we'll trigger the optimization process. The system will{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}analyze performance metrics and automatically switch prompt{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}strategies for any tasks performing below threshold.{Style.RESET_ALL}\n"
    )

    input(f"{Fore.YELLOW}Press Enter to optimize prompts...{Style.RESET_ALL}")
    optimize_prompts(base_url)

    # Step 4: Check performance again to see changes
    print(f"\n{Fore.MAGENTA}STEP 4: Verifying changes{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}Let's check the performance metrics again to confirm that{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}prompt strategies have been updated for underperforming tasks.{Style.RESET_ALL}\n"
    )

    input(f"{Fore.YELLOW}Press Enter to check updated performance...{Style.RESET_ALL}")
    time.sleep(1)  # Small delay
    check_performance(base_url)

    # Step 5: Get optimization history (after changes)
    print(f"\n{Fore.MAGENTA}STEP 5: Confirming optimization history{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}Finally, let's check the optimization history to see the{Style.RESET_ALL}"
    )
    print(f"{Fore.CYAN}record of changes that were just made.{Style.RESET_ALL}\n")

    input(f"{Fore.YELLOW}Press Enter to view updated history...{Style.RESET_ALL}")
    time.sleep(1)  # Small delay
    get_optimization_history(base_url)

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
    print(f"{Fore.CYAN}1. Monitors performance through user feedback{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}2. Detects when performance drops below threshold{Style.RESET_ALL}"
    )
    print(f"{Fore.CYAN}3. Automatically optimizes prompt strategies{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}4. Tracks changes for transparency and analysis{Style.RESET_ALL}\n"
    )

    print(
        f"{Fore.CYAN}In a production environment, these checks would run automatically{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}on a daily schedule via Cloud Scheduler, and results would be{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}visualized in Google Cloud Monitoring dashboards.{Style.RESET_ALL}\n"
    )

    logging.info("Full demonstration sequence completed!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test Email Assistant Performance Monitoring"
    )
    parser.add_argument(
        "--action",
        choices=["check", "optimize", "history", "scheduled", "demo"],
        default="demo",
        help="Action to perform",
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
        check_performance(base_url)
    elif args.action == "optimize":
        optimize_prompts(base_url)
    elif args.action == "history":
        get_optimization_history(base_url)
    elif args.action == "scheduled":
        trigger_scheduled_check(base_url)
    elif args.action == "demo":
        run_full_demo(base_url)


if __name__ == "__main__":
    main()

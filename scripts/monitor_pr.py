#!/usr/bin/env python3
import subprocess
import time
import json
import argparse
import sys


def get_pr_data(pr_url):
    """Fetch PR comments and reviews using gh CLI."""
    cmd = ["gh", "pr", "view", pr_url, "--json", "comments,reviews,state,url"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error fetching PR data: {result.stderr}", file=sys.stderr)
        return None
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description="Monitor a PR for new reviews.")
    parser.add_argument("pr_url", help="The URL or number of the PR to monitor")
    parser.add_argument(
        "--interval", type=int, default=15, help="Polling interval in seconds"
    )
    args = parser.parse_args()

    print(f"Starting monitoring for PR: {args.pr_url}")
    print("Waiting for reviews... (Press Ctrl+C to stop)")

    initial_data = get_pr_data(args.pr_url)
    if not initial_data:
        sys.exit(1)

    initial_comments = len(initial_data.get("comments", []))
    initial_reviews = len(initial_data.get("reviews", []))

    while True:
        try:
            time.sleep(args.interval)
            current_data = get_pr_data(args.pr_url)
            if not current_data:
                continue

            current_comments = len(current_data.get("comments", []))
            current_reviews = len(current_data.get("reviews", []))

            if current_comments > initial_comments or current_reviews > initial_reviews:
                print("\nNew activity detected!")

                new_comments = current_data.get("comments", [])[initial_comments:]
                new_reviews = current_data.get("reviews", [])[initial_reviews:]

                output = {
                    "new_comments": new_comments,
                    "new_reviews": new_reviews,
                    "total_comments": current_comments,
                    "total_reviews": current_reviews,
                }

                print(json.dumps(output, indent=2))
                break

            print(".", end="", flush=True)

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
            break
        except Exception as e:
            print(f"\nError: {e}", file=sys.stderr)
            break


if __name__ == "__main__":
    main()

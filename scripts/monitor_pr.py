#!/usr/bin/env python3
import subprocess
import time
import json
import argparse
import sys


def get_pr_data(pr_url):
    """Fetch PR comments, reviews, and review requests using gh CLI."""
    cmd = [
        "gh", "pr", "view", pr_url, "--json",
        "comments,reviews,reviewRequests,state,url"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error fetching PR data: {result.stderr}", file=sys.stderr)
        return None
    return json.loads(result.stdout)


def has_pending_reviewers(data):
    """Check if any requested reviewers have not yet submitted a review."""
    review_requests = data.get("reviewRequests", [])
    reviews = data.get("reviews", [])

    # Collect logins/slugs of users/teams who have submitted a review
    reviewed_by = set()
    for r in reviews:
        author = r.get("author", {})
        login = author.get("login", "")
        if login:
            reviewed_by.add(login.lower())

    # Check if any requested reviewer hasn't submitted yet
    for req in review_requests:
        login = req.get("login", "")
        slug = req.get("slug", "")  # team reviews
        name = req.get("name", "")
        identifier = (login or slug or name).lower()
        if identifier and identifier not in reviewed_by:
            return True, identifier
    return False, None


def main():
    parser = argparse.ArgumentParser(description="Monitor a PR for new reviews.")
    parser.add_argument("pr_url", help="The URL or number of the PR to monitor")
    parser.add_argument(
        "--interval", type=int, default=15, help="Polling interval in seconds"
    )
    parser.add_argument(
        "--timeout", type=int, default=1200,
        help="Max time to wait in seconds (default: 1200 = 20 minutes)"
    )
    args = parser.parse_args()

    print(f"Starting monitoring for PR: {args.pr_url}")
    print(f"Timeout: {args.timeout}s | Interval: {args.interval}s")
    print("Waiting for reviews... (Press Ctrl+C to stop)")

    initial_data = get_pr_data(args.pr_url)
    if not initial_data:
        sys.exit(1)

    initial_comments = len(initial_data.get("comments", []))
    initial_reviews = len(initial_data.get("reviews", []))
    elapsed = 0

    while elapsed < args.timeout:
        try:
            time.sleep(args.interval)
            elapsed += args.interval

            current_data = get_pr_data(args.pr_url)
            if not current_data:
                continue

            current_comments = len(current_data.get("comments", []))
            current_reviews = len(current_data.get("reviews", []))

            new_activity = (
                current_comments > initial_comments
                or current_reviews > initial_reviews
            )

            if new_activity:
                # Check if there are still pending reviewers
                pending, reviewer = has_pending_reviewers(current_data)
                if pending:
                    print(
                        f"\nNew activity detected, but reviewer '{reviewer}' "
                        "is still pending. Continuing to wait..."
                    )
                    continue

                print("\nAll reviewers have completed their reviews!")

                new_comments = current_data.get("comments", [])[initial_comments:]
                new_reviews = current_data.get("reviews", [])[initial_reviews:]

                output = {
                    "new_comments": new_comments,
                    "new_reviews": new_reviews,
                    "total_comments": current_comments,
                    "total_reviews": current_reviews,
                    "all_reviewers_done": True,
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
    else:
        # Timeout reached — still report current state
        current_data = get_pr_data(args.pr_url)
        pending, reviewer = has_pending_reviewers(current_data) if current_data else (False, None)
        print(f"\nTimeout reached ({args.timeout}s).")
        if pending:
            print(f"WARNING: Reviewer '{reviewer}' still has not completed their review.")
        output = {
            "timeout": True,
            "pending_reviewer": reviewer,
            "new_comments": current_data.get("comments", [])[initial_comments:] if current_data else [],
            "new_reviews": current_data.get("reviews", [])[initial_reviews:] if current_data else [],
            "all_reviewers_done": not pending,
        }
        print(json.dumps(output, indent=2))
        sys.exit(2)


if __name__ == "__main__":
    main()

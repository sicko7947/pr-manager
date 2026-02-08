---
name: pr-manager
description: Automates creating PRs, monitoring for reviews (refreshing every 15s), implementing feedback (High/Medium criticality only), replying to comments, and waiting for merge.
---

# PR Manager

This skill manages the lifecycle of a Pull Request, from creation to feedback implementation and merge readiness.

## When to Use This Skill

Use this skill when:
- You need to create a PR and actively wait for code reviews (e.g., from Gemini, Copilot, or human reviewers).
- You want to automate the feedback loop: implementing changes based on reviews and replying to comments.
- You need to filter feedback based on criticality (High/Medium vs. Low/Nitpick).

## Workflow

### 1. Create Pull Request

First, ensure you are on the correct feature branch.
Check if a PR already exists for this branch. If not, create one.

```bash
# Check if PR exists
gh pr list --head "$(git branch --show-current)" --json url,number

# If no PR exists, create one (adjust title/body as needed)
gh pr create --title "feat: <title>" --body "Automated PR created by Agent"
```

### 2. Monitor for Reviews

Use the `scripts/monitor_pr.py` script to wait for new review activity. This script polls the PR every 15 seconds and exits when new comments or reviews are detected.

```bash
# Get PR URL first if you don't have it
PR_URL=$(gh pr view --json url -q .url)

# Run the monitor script
python3 skills/pr-manager/scripts/monitor_pr.py "$PR_URL" --interval 15
```

The script will output JSON containing `new_comments` and `new_reviews`.

### 3. Analyze Feedback

When new activity is detected:
1.  **Parse the JSON output** from `monitor_pr.py`.
2.  **Examine each comment/review suggestion.**
3.  **Critically Evaluate:**
    *   **Is this feedback valid?** Does it improve the code?
    *   **Is it Critical?**
        *   **High:** Security, Bugs, Major Logic Flaws.
        *   **Medium:** Performance, Best Practices, Maintainability.
        *   **Low/Nitpick:** Formatting (if linter exists), subjective style preferences.

### 4. Implement Changes

**Only implement High or Medium criticality feedback.**
- For Low/Nitpick feedback: Do not implement unless it's trivial and automated (e.g., formatting).
- If a suggestion is wrong or unnecessary, do *not* implement it.

### 5. Reply to Comments

You MUST reply to **every single comment** that was part of the review batch.

*   **If implemented:** "Fixed: [Brief explanation of change]"
*   **If NOT implemented:** "Skipped: [Reasoning why it was not implemented, e.g., 'This is a nitpick handled by formatter' or 'This suggestion would break X']"

```bash
# Reply to a specific comment (replace COMMENT_ID)
gh pr comment "$PR_URL" --reply-to COMMENT_ID --body "Fixed: updated logic."
```

### 6. Loop or Finalize

- If the review requested changes (`CHANGES_REQUESTED`), repeat from **Step 2** (Monitor) after pushing fixes.
- If the review was `APPROVED` or comments are addressed:
    1.  Output the PR URL.
    2.  Ask the user for final confirmation to merge.
    3.  If confirmed, merge: `gh pr merge "$PR_URL" --merge --delete-branch`.

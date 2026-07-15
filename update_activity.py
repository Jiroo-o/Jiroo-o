import os
import re
import json
import urllib.request
from datetime import datetime

USERNAME = "Jiroo-o"
API_URL = f"https://api.github.com/users/{USERNAME}/events/public"
README_PATH = os.path.join(os.path.dirname(__file__), "README.md")

START_TAG = "<!-- ACTIVITY:START -->"
END_TAG = "<!-- ACTIVITY:END -->"

def fetch_events():
    """Fetches public events from GitHub REST API."""
    req = urllib.request.Request(API_URL)
    req.add_header("User-Agent", "Jiroo-o-Readme-Activity-Bot")
    
    # Use GITHUB_TOKEN if available to avoid rate limit issues in GitHub Actions
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"token {token}")
        print("Using GitHub Token for request authentication.")
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                return json.loads(response.read().decode("utf-8"))
            else:
                print(f"API returned status code: {response.status}")
                return None
    except Exception as e:
        print(f"Failed to fetch public events: {e}")
        return None

def format_event(event):
    """Formats a single GitHub event into a clean Markdown bullet point."""
    event_type = event.get("type")
    repo_name = event.get("repo", {}).get("name", "")
    repo_url = f"https://github.com/{repo_name}"
    
    # Make repository name compact (just repo name, not username/repo if same user)
    display_repo = repo_name.replace(f"{USERNAME}/", "")
    
    # Timestamp formatting (optional but good for context)
    created_at_str = event.get("created_at", "")
    try:
        dt = datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ")
        time_str = dt.strftime("%b %d, %Y")
    except ValueError:
        time_str = ""

    payload = event.get("payload", {})
    
    if event_type == "PushEvent":
        commits = payload.get("commits", [])
        if not commits:
            return None
        
        # Get the first commit message
        latest_commit_msg = commits[0].get("message", "").split("\n")[0]
        # Truncate message if too long
        if len(latest_commit_msg) > 60:
            latest_commit_msg = latest_commit_msg[:57] + "..."
            
        commit_count = len(commits)
        commit_word = "commit" if commit_count == 1 else "commits"
        
        return f"• 📝 Pushed {commit_count} {commit_word} to [`{display_repo}`]({repo_url}): *\"{latest_commit_msg}\"* ({time_str})"
        
    elif event_type == "PullRequestEvent":
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        title = pr.get("title", "")
        pr_url = pr.get("html_url", "")
        
        # Format actions to be user-friendly
        if action == "opened":
            emoji = "🔀"
            desc = "Opened pull request"
        elif action == "closed":
            emoji = "✅"
            if pr.get("merged", False):
                desc = "Merged pull request"
            else:
                desc = "Closed pull request"
        else:
            return None
            
        return f"• {emoji} {desc} [`#{pr.get('number')}` {title}]({pr_url}) in [`{display_repo}`]({repo_url}) ({time_str})"
        
    elif event_type == "IssuesEvent":
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        title = issue.get("title", "")
        issue_url = issue.get("html_url", "")
        
        if action == "opened":
            emoji = "🐛"
            desc = "Opened issue"
        elif action == "closed":
            emoji = "🔒"
            desc = "Closed issue"
        else:
            return None
            
        return f"• {emoji} {desc} [`#{issue.get('number')}` {title}]({issue_url}) in [`{display_repo}`]({repo_url}) ({time_str})"
        
    elif event_type == "WatchEvent":
        action = payload.get("action", "")
        if action == "started":
            return f"• ⭐ Starred [`{repo_name}`]({repo_url}) ({time_str})"
            
    elif event_type == "CreateEvent":
        ref_type = payload.get("ref_type", "")
        ref = payload.get("ref", "")
        if ref_type == "repository":
            return f"• 🆕 Created new repository [`{repo_name}`]({repo_url}) ({time_str})"
        elif ref_type == "branch" and ref:
            return f"• 🌿 Created branch `{ref}` in [`{display_repo}`]({repo_url}) ({time_str})"
            
    return None

def build_activity_markdown(events):
    """Processes events and compiles them into a markdown list."""
    if not events:
        return "• *No recent activity found.*"
        
    markdown_lines = []
    seen_activities = set() # Avoid too much repetition for the same repo/action type
    
    for event in events:
        formatted = format_event(event)
        if formatted and formatted not in seen_activities:
            markdown_lines.append(formatted)
            seen_activities.add(formatted)
            # Limit to top 6 activities for a clean look
            if len(markdown_lines) >= 6:
                break
                
    if not markdown_lines:
        return "• *No recent activity found.*"
        
    return "\n".join(markdown_lines)

def update_readme():
    """Reads README, replaces the activity section, and saves it."""
    events = fetch_events()
    activity_md = build_activity_markdown(events)
    
    if not os.path.exists(README_PATH):
        print(f"Error: README.md not found at {README_PATH}")
        return
        
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Regex to find text between START_TAG and END_TAG
    pattern = re.compile(
        rf"({re.escape(START_TAG)}).*?({re.escape(END_TAG)})",
        re.DOTALL
    )
    
    if not pattern.search(content):
        print("Error: Could not find placeholders in README.md")
        return
        
    replacement = f"\\1\n{activity_md}\n\\2"
    updated_content = pattern.sub(replacement, content)
    
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    print("Successfully updated README.md with recent activity:")
    print(activity_md)

if __name__ == "__main__":
    update_readme()

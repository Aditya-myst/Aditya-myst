#!/usr/bin/env python3
"""
Fetches merged pull requests for GITHUB_USERNAME and rewrites the
Open Source Contributions table in README.md, between the markers:
  <!-- OSS-CONTRIBUTIONS:START -->
  <!-- OSS-CONTRIBUTIONS:END -->

Run in CI via .github/workflows/update-readme.yml, or locally:
  GITHUB_TOKEN=xxx python3 scripts/update_readme.py
"""

import json
import os
import re
import sys
import urllib.request

USERNAME = os.environ.get("GITHUB_USERNAME", "Aditya-myst")
README_PATH = os.environ.get("README_PATH", "README.md")
MAX_ROWS = 8
START_MARKER = "<!-- OSS-CONTRIBUTIONS:START -->"
END_MARKER = "<!-- OSS-CONTRIBUTIONS:END -->"

# Repos to skip so the section stays credible (tutorial/practice repos, your own repos)
SKIP_REPOS = {
    "firstcontributions/first-contributions",
}


def api_get(url, token):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def fetch_merged_prs(username, token):
    query = f"author:{username}+type:pr+is:merged"
    url = f"https://api.github.com/search/issues?q={query}&sort=created&order=desc&per_page=30"
    data = api_get(url, token)
    rows = []
    for item in data.get("items", []):
        repo = item["repository_url"].split("/repos/")[-1]
        if repo in SKIP_REPOS or repo.lower().startswith(f"{username.lower()}/"):
            continue
        merged_at = item.get("pull_request", {}).get("merged_at")
        if not merged_at:
            continue
        rows.append(
            {
                "repo": repo,
                "title": item["title"].strip(),
                "url": item["html_url"],
                "merged_at": merged_at,
            }
        )
    rows.sort(key=lambda r: r["merged_at"], reverse=True)
    return rows[:MAX_ROWS]


def format_date(iso_str):
    # e.g. "2026-07-14T13:59:53Z" -> "Jul 2026"
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    year, month = iso_str[:4], int(iso_str[5:7])
    return f"{months[month - 1]} {year}"


def build_table(rows):
    if not rows:
        return "_No merged pull requests found yet — check back soon!_"
    lines = ["| Repository | Contribution | Merged |", "|---|---|---|"]
    for r in rows:
        repo_link = f"[{r['repo']}]({r['url']})"
        title = r["title"].replace("|", "\\|")
        lines.append(f"| {repo_link} | {title} | {format_date(r['merged_at'])} |")
    return "\n".join(lines)


def update_readme(table_md):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER not in content or END_MARKER not in content:
        print(f"Markers not found in {README_PATH}; nothing to update.", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{table_md}\n{END_MARKER}"
    new_content = pattern.sub(replacement, content)

    if new_content != content:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README.md updated.")
    else:
        print("No changes needed.")


def main():
    token = os.environ.get("GITHUB_TOKEN", "")
    rows = fetch_merged_prs(USERNAME, token)
    table_md = build_table(rows)
    update_readme(table_md)


if __name__ == "__main__":
    main()

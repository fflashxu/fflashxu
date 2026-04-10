"""
Fetches pinned repos via GitHub GraphQL API and updates the
"What I'm building" table in README.md between marker comments.

Status is driven by GitHub repo topics:
  status-live   → 🟢 Live
  status-beta   → 🔒 Private beta
  status-wip    → 🔨 In progress
  (none)        → 📋 Planned

Product link uses homepageUrl if set, otherwise the GitHub repo URL.
"""
import os
import re
import json
import urllib.request

USERNAME = "fflashxu"
README_PATH = "README.md"
MARKER_START = "<!-- PINNED_REPOS_START -->"
MARKER_END = "<!-- PINNED_REPOS_END -->"

QUERY = """
{
  user(login: "%s") {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          url
          homepageUrl
          isPrivate
          primaryLanguage { name }
          stargazerCount
          repositoryTopics(first: 10) {
            nodes { topic { name } }
          }
        }
      }
    }
  }
}
""" % USERNAME


def graphql(token: str) -> list:
    payload = json.dumps({"query": QUERY}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    if "errors" in data:
        raise RuntimeError(data["errors"])

    return data["data"]["user"]["pinnedItems"]["nodes"]


def status_badge(repo: dict) -> str:
    topics = {n["topic"]["name"] for n in repo["repositoryTopics"]["nodes"]}
    if "status-live" in topics:
        return "🟢 Live"
    if "status-beta" in topics:
        return "🔒 Private beta"
    if "status-wip" in topics:
        return "🔨 In progress"
    return "📋 Planned"


def build_table(repos: list) -> str:
    rows = [
        "| Product | What it does | Status |",
        "|---|---|---|",
    ]
    for repo in repos:
        name = repo["name"]
        link = repo.get("homepageUrl") or repo["url"]
        desc = (repo.get("description") or "—").rstrip(".")
        badge = status_badge(repo)
        rows.append(f"| **[{name}]({link})** | {desc} | {badge} |")
    return "\n".join(rows)


def update_readme(table: str) -> bool:
    with open(README_PATH, "r", encoding="utf-8") as f:
        original = f.read()

    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        re.DOTALL,
    )
    replacement = f"{MARKER_START}\n{table}\n{MARKER_END}"
    updated = pattern.sub(replacement, original)

    if updated == original:
        print("README already up to date.")
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)
    print("README updated.")
    return True


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN not set")

    repos = graphql(token)
    print(f"Found {len(repos)} pinned repos: {[r['name'] for r in repos]}")
    table = build_table(repos)
    update_readme(table)

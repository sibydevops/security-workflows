import os
import requests
import base64
import argparse
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN environment variable is not set.")

ORG = "sibydevops"
WORKFLOW_PATH = Path(__file__).parent / ".github" / "workflows" / "security-scan.yml"
WORKFLOW_CONTENT = WORKFLOW_PATH.read_text(encoding="utf-8")

parser = argparse.ArgumentParser(description="Deploy the central security workflow.")
parser.add_argument("--repo", help="Deploy only to this repository")
args = parser.parse_args()

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Get every repository, not just the first page of 100.
print(f"Fetching repositories from {ORG}...")
repos = []
if args.repo:
    response = requests.get(
        f"https://api.github.com/repos/{ORG}/{args.repo}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    repos = [response.json()]
else:
    page = 1
    while True:
        response = requests.get(
            f"https://api.github.com/orgs/{ORG}/repos",
            headers=headers,
            params={"per_page": 100, "page": page, "type": "all"},
            timeout=30,
        )
        response.raise_for_status()
        page_repos = response.json()
        repos.extend(page_repos)
        if len(page_repos) < 100:
            break
        page += 1

print(f"Found {len(repos)} repositories")

success_count = 0
fail_count = 0

for repo in repos:
    repo_name = repo['name']
    
    if repo_name == 'security-workflows' or repo.get('archived') or repo.get('fork'):
        continue
    
    print(f"\nDeploying to {repo_name}...")
    
    check_url = f"https://api.github.com/repos/{ORG}/{repo_name}/contents/.github/workflows/security-scan.yml"
    check_response = requests.get(check_url, headers=headers)
    
    if check_response.status_code == 200:
        print(f"  ⚠️  Already exists, skipping...")
        continue
    
    create_url = f"https://api.github.com/repos/{ORG}/{repo_name}/contents/.github/workflows/security-scan.yml"
    
    data = {
        "message": "Add OWASP security scanning workflow",
        "content": base64.b64encode(WORKFLOW_CONTENT.replace('your-org', ORG).encode()).decode()
    }
    
    if os.environ.get("DRY_RUN", "").lower() == "true":
      print("  [dry run] would deploy workflow")
      continue

    response = requests.put(create_url, headers=headers, json=data, timeout=30)
    
    if response.status_code == 201:
        print(f"  ✅ Deployed successfully")
        success_count += 1
    else:
        print(f"  ❌ Failed: {response.status_code}")
        fail_count += 1
    
print(f"\n{'='*50}")
print(f"Deployment complete!")
print(f"✅ Success: {success_count}")
print(f"❌ Failed: {fail_count}")
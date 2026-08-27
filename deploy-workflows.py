import os
import base64
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError(
        "GITHUB_TOKEN is not set. Create a token with Contents: Read and write "
        "for the target repositories, then set it before running this script."
    )

ORG = "sibydevops"
WORKFLOW_PATH = Path(__file__).parent / ".github" / "workflows" / "security-scan.yml"
WORKFLOW_CONTENT = WORKFLOW_PATH.read_text(encoding="utf-8")

parser = argparse.ArgumentParser(description="Deploy the central security workflow.")
parser.add_argument("--repo", help="Deploy only to this repository")
parser.add_argument("--force", action="store_true", help="Update existing caller workflows")
parser.add_argument(
    "--disable-codeql-default-setup",
    action="store_true",
    help="Disable GitHub CodeQL default setup so advanced CodeQL can upload results",
)
args = parser.parse_args()

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
}


def github_request(url, method="GET", params=None, payload=None):
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return error.code, body


def disable_codeql_default_setup(repo_name):
    status, response = github_request(
        f"https://api.github.com/repos/{ORG}/{repo_name}/code-scanning/default-setup",
        method="PATCH",
        payload={"state": "not-configured"},
    )
    if status not in (200, 204):
        raise RuntimeError(
            f"Cannot disable CodeQL default setup for {repo_name}: "
            f"HTTP {status} ({response})"
        )

# Get every repository, not just the first page of 100.
print(f"Fetching repositories from {ORG}...")
repos = []
if args.repo:
    status, response = github_request(
        f"https://api.github.com/repos/{ORG}/{args.repo}"
    )
    if status != 200:
        raise RuntimeError(f"Cannot read repository {args.repo}: HTTP {status} ({response})")
    repos = [response]
else:
    page = 1
    while True:
        status, response = github_request(
            f"https://api.github.com/orgs/{ORG}/repos",
            params={"per_page": 100, "page": page, "type": "all"},
        )
        if status != 200:
            raise RuntimeError(f"Cannot list organization repositories: HTTP {status} ({response})")
        page_repos = response
        repos.extend(page_repos)
        if len(page_repos) < 100:
            break
        page += 1

print(f"Found {len(repos)} repositories")

success_count = 0
fail_count = 0

if (
    args.disable_codeql_default_setup
    and os.environ.get("DRY_RUN", "").lower() != "true"
):
    disable_codeql_default_setup("security-workflows")
    print("Disabled CodeQL default setup for security-workflows")
elif args.disable_codeql_default_setup:
    print("[dry run] would disable CodeQL default setup for security-workflows")

for repo in repos:
    repo_name = repo['name']
    
    if repo_name == 'security-workflows' or repo.get('archived') or repo.get('fork'):
        continue
    
    print(f"\nDeploying to {repo_name}...")

    if args.disable_codeql_default_setup and repo_name != "security-workflows" and os.environ.get("DRY_RUN", "").lower() != "true":
        disable_codeql_default_setup(repo_name)
        print("  Disabled CodeQL default setup")
    elif args.disable_codeql_default_setup and repo_name != "security-workflows":
        print("  [dry run] would disable CodeQL default setup")
    
    check_url = f"https://api.github.com/repos/{ORG}/{repo_name}/contents/.github/workflows/security-scan.yml"
    check_status, existing_file = github_request(check_url)
    if check_status not in (200, 404):
        raise RuntimeError(
            f"Cannot inspect {repo_name}: GitHub API returned "
            f"{check_status} ({existing_file})"
        )
    if check_status == 404:
        existing_file = None

    if existing_file and not args.force:
        print("  Already exists, skipping (use --force to update)")
        continue
    
    create_url = f"https://api.github.com/repos/{ORG}/{repo_name}/contents/.github/workflows/security-scan.yml"
    
    data = {
        "message": "Update centralized OWASP security workflow",
        "content": base64.b64encode(WORKFLOW_CONTENT.replace('your-org', ORG).encode()).decode(),
    }
    if existing_file:
        data["sha"] = existing_file["sha"]
    
    if os.environ.get("DRY_RUN", "").lower() == "true":
        print("  [dry run] would deploy workflow")
        continue

    response_status, response = github_request(create_url, method="PUT", payload=data)
    
    if response_status in (200, 201):
        print(f"  ✅ {'Updated' if existing_file else 'Deployed'} successfully")
        success_count += 1
    else:
        print(f"  ❌ Failed: {response_status} ({response})")
        fail_count += 1
    
print(f"\n{'='*50}")
print(f"Deployment complete!")
print(f"✅ Success: {success_count}")
print(f"❌ Failed: {fail_count}")
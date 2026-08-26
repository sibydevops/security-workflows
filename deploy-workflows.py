import os
import requests
import base64
import time

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN environment variable is not set.")

ORG = "sibydevops"
WORKFLOW_CONTENT = """
name: Security Scan

on:
  push:
    branches: [main, master, develop]
  pull_request:
    branches: [main, master, develop]

permissions:
  contents: read
  security-events: write
  actions: read
  pull-requests: write

jobs:
  secret-scan:
    name: Secret Scanning
    uses: your-org/security-workflows/.github/workflows/reusable-secret-scan.yml@main
    with:
      scan-level: 'verified,unverified'
      fail-on-severity: 'high'

  sast-scan:
    name: SAST Scan
    uses: your-org/security-workflows/.github/workflows/reusable-sast-scan.yml@main
    with:
      languages: 'javascript,python,java,csharp,go'
      queries: 'security-extended'

  dast-scan:
    name: DAST Scan
    if: github.event_name == 'pull_request' && github.base_ref == 'refs/heads/main'
    uses: your-org/security-workflows/.github/workflows/reusable-dast-scan.yml@main
    needs: [sast-scan]
    with:
      target-url: 'https://staging-${{ github.event.repository.name }}.your-org.com'
      zap-rules-file: '.zap/rules.tsv'
      scan-type: 'baseline'
      fail-on-severity: 'high'

  api-scan:
    name: API Security Scan
    if: github.event_name == 'pull_request' && contains(github.event.repository.name, 'api')
    uses: your-org/security-workflows/.github/workflows/reusable-api-scan.yml@main
    with:
      api-url: 'https://api-${{ github.event.repository.name }}.your-org.com'
      api-token: ${{ secrets.API_TOKEN }}
      openapi-spec: 'docs/openapi.yaml'
      fail-on-severity: 'high'

  dependency-scan:
    name: Dependency Scanning
    uses: your-org/security-workflows/.github/workflows/reusable-dependency-scan.yml@main
    with:
      project-name: ${{ github.event.repository.name }}
      scan-path: '.'
      format: 'SARIF'

  security-summary:
    name: Security Summary
    needs: [secret-scan, sast-scan, dast-scan, api-scan, dependency-scan]
    if: always()
    uses: your-org/security-workflows/.github/workflows/reusable-security-summary.yml@main
"""

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Get all repositories
print(f"Fetching repositories from {ORG}...")
repos_url = f"https://api.github.com/orgs/{ORG}/repos?per_page=100"
response = requests.get(repos_url, headers=headers)
repos = response.json()

print(f"Found {len(repos)} repositories")

success_count = 0
fail_count = 0

for repo in repos:
    repo_name = repo['name']
    
    if repo_name == 'security-workflows':
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
    
    response = requests.put(create_url, headers=headers, json=data)
    
    if response.status_code == 201:
        print(f"  ✅ Deployed successfully")
        success_count += 1
    else:
        print(f"  ❌ Failed: {response.status_code}")
        fail_count += 1
    
    time.sleep(1)

print(f"\n{'='*50}")
print(f"Deployment complete!")
print(f"✅ Success: {success_count}")
print(f"❌ Failed: {fail_count}")
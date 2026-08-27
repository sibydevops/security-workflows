# Free Local OWASP Setup

This is the easiest way to prove that OWASP penetration testing works without Azure, Cloudflare, a public URL, or application-repository changes.

## What this demo does

GitHub Actions starts OWASP Juice Shop in Docker on an Ubuntu runner, then OWASP ZAP scans:

```text
http://127.0.0.1:3000
```

The demo workflow is:

```text
.github/workflows/owasp-local-demo.yml
```

It runs on pushes and pull requests to this central repository and can also be started manually.

## Step 1: Push the workflow

From the repository root:

```powershell
git add .
git commit -m "Add free local OWASP ZAP demo"
git push origin main
```

GitHub-hosted runners are free for public repositories within GitHub Actions usage limits. No cloud account or webhook is needed for this demo.

## Step 2: Run it

Open:

```text
security-workflows -> Actions -> OWASP Local Penetration Test Demo
```

Choose **Run workflow** or push a harmless change.

Expected steps:

1. Start OWASP Juice Shop.
2. Wait for port 3000.
3. Run OWASP ZAP baseline scan.
4. Upload the HTML, JSON, and Markdown reports.

Automatic GitHub issue creation is disabled. ZAP findings are reviewed from the uploaded reports, avoiding a requirement for issue-write permissions on the repository token.

Open the completed run and download the artifact:

```text
owasp-zap-local-demo-<run-id>
```

## Step 3: Understand the result

This scans the intentionally vulnerable OWASP Juice Shop demo application. It proves that the ZAP pipeline and report collection work. It does not scan any application repository yet.

Do not represent this report as a finding in one of your production applications.

## Step 4: Scan an application without a public URL

For a real application, the central job must first build and start that exact commit on the runner. Each technology needs an approved profile:

```text
Flask:
pip install -r requirements.txt && flask run --host=0.0.0.0 --port=5000

ASP.NET Core:
dotnet restore && dotnet run --urls http://0.0.0.0:5000

Node:
npm ci && npm run start -- --host 0.0.0.0 --port 5000

Spring Boot:
./mvnw spring-boot:run -Dspring-boot.run.arguments=--server.port=5000
```

The workflow then waits for a health endpoint and runs:

```text
OWASP ZAP -> http://127.0.0.1:5000
```

A generic workflow cannot safely guess build commands for 10,000 different repositories. Use an organization-owned profile catalog containing the startup command, port, health path, build requirements, and application type.

## Step 5: Application profiles

### Web

Run OWASP ZAP against the local or staging HTTP service. Include authentication context where authorized.

### API

Run schema-driven API tests using an OpenAPI document and test credentials. Add:

```text
docs/openapi.yaml
```

Use the OWASP API Security Top 10 as the test coverage model.

### Cloud-native

Build the container and run it locally or in an isolated ephemeral environment. Add container, Kubernetes, and Terraform/IaC scanning. Run ZAP only when an HTTP service exists.

### Desktop

Run dependency, SBOM, signing, update-channel, IPC, and local source/configuration tests. Mark HTTP penetration testing not applicable unless the product exposes an HTTP service.

### Library

Run dependency, SBOM, package, source, and supply-chain tests. Active ZAP testing is normally not applicable.

## Step 6: Organization-wide events

The demo workflow does not automatically receive events from other repositories. GitHub Actions `push` and `pull_request` events belong to the repository containing the workflow.

For every push and pull request across 10,000 repositories, an organization owner must choose one:

1. Copy the caller workflow into each repository.
2. Use GitHub Enterprise required workflows for supported pull-request enforcement.
3. Use an organization GitHub App/webhook to dispatch central scans.
4. Use scheduled polling for delayed scans.

There is no free GitHub Actions-only wildcard trigger that runs one central workflow immediately for every repository event without a caller, event service, or polling process.

## OWASP method

Use:

- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/) for web testing.
- [OWASP API Security Project](https://owasp.org/www-project-api-security/) for API testing.
- [OWASP Top 10](https://owasp.org/www-project-top-ten/) for risk communication.
- [OWASP ZAP](https://www.zaproxy.org/) for authorized DAST.

A real penetration test also requires written authorization, scope, manual validation, evidence, severity assessment, remediation, and retesting. Automated ZAP output is one part of that process.

# Common OWASP Security Workflow Implementation Guide

## Goal

Run a consistent security workflow for web, API, cloud-native, desktop, mobile, library, and infrastructure repositories.

The common workflow is:

```text
.github/workflows/common-owasp-security.yml
```

The caller template is:

```text
docs/application-security-caller.yml
```

## Important GitHub limitation

A workflow in `security-workflows` cannot receive `push` or `pull_request` events from other repositories. GitHub evaluates those events in the repository containing the workflow file.

Therefore, immediate scans for every push and pull request require one of these:

1. Copy the caller template into each application repository.
2. Use GitHub Enterprise Cloud required workflows/rulesets where available for pull requests.
3. Use an organization GitHub App/webhook for central event delivery.
4. Use scheduled polling for delayed scans without repository workflow files.

A central reusable workflow is the correct shared implementation, but it is not itself an organization-wide event listener.

## Step 1: Prepare the central repository

Keep the common workflow in the central repository and pin its reference to a reviewed release tag instead of `main` for production:

```text
sibydevops/security-workflows/.github/workflows/common-owasp-security.yml
```

Review all third-party actions and pin versions or commit SHAs according to organization supply-chain policy.

## Step 2: Install the caller

For a repository where you have write access, create:

```text
.github/workflows/organization-owasp-security.yml
```

Copy the contents of:

```text
docs/application-security-caller.yml
```

The caller runs on:

```yaml
on:
  push:
  pull_request:
  workflow_dispatch:
```

If you cannot write to 10,000 repositories, an organization owner must configure required workflows, provide an approved GitHub App/event service, or accept scheduled polling. There is no GitHub Actions-only wildcard trigger for another repository's events.

## Step 3: Choose application profile

The common workflow accepts:

```text
web
api
cloud-native
desktop
mobile
library
infrastructure
auto
```

Use `auto` initially. Replace it with an explicit profile when repository metadata is available. Explicit profiles are more reliable than filename heuristics.

Examples:

```yaml
with:
  application-type: api
  run-zap: false
```

```yaml
with:
  application-type: cloud-native
  run-zap: false
```

## Step 4: Configure OWASP scans

The common baseline runs OWASP Dependency-Check for every repository invocation.

### Web applications

Use:

- OWASP Dependency-Check
- OWASP ZAP baseline scan
- SBOM generation
- SAST where the organization has enabled CodeQL or an approved tool

ZAP requires an authorized non-production URL:

```yaml
with:
  application-type: web
  run-zap: true
  target-url: https://staging.example.test
```

### APIs

Use:

- OWASP API Security Top 10 2023
- OWASP ZAP API testing
- Dependency-Check
- OpenAPI/schema-driven tests
- Authentication and authorization test cases

API tests require an authorized API URL and test credentials. Never put credentials in workflow YAML or event payloads.

### Cloud-native applications

Use:

- Dependency-Check
- Container image scanning
- Kubernetes manifest scanning
- Terraform/IaC scanning
- Secrets/configuration review
- ZAP/API testing against an isolated deployed service when applicable

### Desktop applications

Use:

- Dependency and SBOM analysis
- Source analysis
- Signing and update-mechanism review
- Local IPC/plugin/configuration testing

ZAP is normally not applicable unless the desktop application exposes an HTTP service.

### Mobile applications

Use:

- Dependency and SBOM analysis
- Android/iOS manifest and configuration review
- Static source analysis
- Emulator/device testing under a separate mobile test plan

### Libraries and infrastructure

Use dependency, SBOM, source, IaC, configuration, and package-publication controls. Mark active web penetration testing as `not applicable` unless an authorized test harness exposes an HTTP service.

## Step 5: Use OWASP methodology

Use the OWASP Web Security Testing Guide for web applications and the OWASP API Security Top 10 for APIs.

A penetration test consists of:

1. Written authorization and scope.
2. Asset and trust-boundary discovery.
3. Threat modeling and abuse cases.
4. Automated testing.
5. Manual validation of important findings.
6. Evidence, severity, and remediation mapping.
7. Retesting after fixes.

Use versioned WSTG scenario IDs in evidence. Use the OWASP Top 10 for risk communication, not as a complete test plan.

## Step 6: Handle active testing targets

OWASP ZAP and API testing need a running HTTP target. Use one of:

- Dedicated staging environment.
- Temporary isolated deployment.
- Application started on the GitHub runner.

If there is no target, the workflow must report `not applicable`. It must not claim that active penetration testing passed.

## Step 7: Configure GitHub security

An organization owner should:

- Enable GitHub Actions.
- Enable code scanning where applicable.
- Approve reusable workflow access.
- Configure repository rulesets.
- Require the security check before protected-branch merges.
- Define severity thresholds and remediation deadlines.
- Provide an exception/break-glass process.

Do not run advanced CodeQL if organization-managed default setup is enabled for the same repository. Choose one CodeQL configuration.

## Step 8: Test one repository of each type

Use representative repositories:

- ASP.NET or Flask API.
- React or Node web application.
- Go service.
- Java service.
- Desktop project.
- Cloud-native project.
- Library.

For each test:

1. Push a harmless commit.
2. Confirm the workflow starts.
3. Confirm the correct profile.
4. Confirm Dependency-Check runs.
5. Confirm ZAP only runs with an authorized URL.
6. Open a pull request.
7. Push another commit to the pull request.
8. Confirm a new run uses the new commit SHA.
9. Review artifacts and findings.
10. Validate failure, retry, and exception behavior.

## Step 9: Scale to 10,000 repositories

Do not run 10,000 scans synchronously from one workflow job. Use:

- Event queue or scheduled batches.
- Repository/SHA idempotency keys.
- Delivery deduplication.
- Pull request priority.
- Concurrency limits.
- GitHub API rate-limit handling.
- Retry and dead-letter handling.
- Cancellation of obsolete commit scans.
- Central coverage and failure dashboards.
- Periodic reconciliation for missed events.

For immediate push and pull request execution without modifying every repository, an organization GitHub App/event receiver is required. Without an external event receiver, GitHub Actions can provide required workflows for supported pull-request governance or scheduled polling, but not an immediate central push trigger.

## Training

Use official OWASP material as the normative reference:

- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [OWASP API Security Project](https://owasp.org/www-project-api-security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP ZAP](https://www.zaproxy.org/)

LinkedIn Learning search results include courses such as:

- [Offensive Penetration Testing](https://www.linkedin.com/learning/offensive-penetration-testing)
- [Penetration Testing Essential Training](https://www.linkedin.com/learning/penetration-testing-essential-training-24352676)
- [Security Testing Essential Training](https://www.linkedin.com/learning/security-testing-essential-training-26279403)
- [Dynamic Application Security Testing](https://www.linkedin.com/learning/dynamic-application-security-testing)
- [Application Security Testing and Debugging](https://www.linkedin.com/learning/application-security-testing-and-debugging)

Availability may require a LinkedIn Learning subscription or vary by region. Training does not replace an approved scope, test plan, or manual penetration test.

# security-workflows

Central repository for organization-wide OWASP security scanning workflows.

## How It Works

GitHub Actions runs in the repository that receives the `push` or `pull_request` event. The central repository therefore provides reusable workflows, and a small caller workflow is installed in each application repository. `deploy-workflows.py` installs that caller without overwriting an existing workflow.

This is important for scale: a workflow in `security-workflows` cannot receive `push` events from other repositories. For 10,000 repositories, use one of these organization designs:

- **Actions-only:** install the caller workflow in every repository. Reconcile it periodically with `python deploy-workflows.py --force`; new repositories need to be added to the deployment process.
- **Central event service:** install an organization GitHub App/webhook for `push` and `pull_request`, validate the event, and dispatch a scan for the changed repository. The service must use a GitHub App token and check out the event repository at the event SHA. Do not use a personal access token or scan arbitrary URLs.

The central receiver is [central-security-dispatch.yml](.github/workflows/central-security-dispatch.yml). The GitHub App must call `POST /repos/sibydevops/security-workflows/dispatches` with `event_type` set to `repository-push` or `repository-pull-request` and a payload containing `repository` (`owner/name`) and `sha` (the exact commit SHA). The App needs access to the target repositories and the central repository, plus permission to dispatch workflows. Validate the webhook signature, deduplicate delivery IDs, and reject repositories outside the organization.

This event-service design requires a small always-on service such as Azure Functions, AWS Lambda, or Cloud Run. GitHub Actions alone cannot subscribe one central workflow to push events from 10,000 repositories.

The caller classifies repositories from their files and selects CodeQL languages. The supported profiles are:

| Profile | Detection examples | Scans |
| --- | --- | --- |
| `web` | `package.json`, `public/`, `src/` | secrets, SAST, dependencies; optional ZAP/API |
| `cloud-native` | `Dockerfile`, Compose, Helm `charts/`, `.devcontainer/` | secrets, SAST, dependencies; optional ZAP/API |
| `desktop` | `.sln`, `.csproj`, Xcode project files | secrets, SAST, dependencies |
| `library-or-infrastructure` | everything else | secrets, SAST when a supported language is found, dependencies |

OWASP ZAP DAST and OWASP ASTF API penetration testing are target-based and intentionally opt-in. Set repository variables before enabling them:

- `SECURITY_DAST_TARGET_URL`: deployed web application URL for OWASP ZAP.
- `SECURITY_API_URL`: deployed API base URL for OWASP ASTF.
- `SECURITY_API_TOKEN`: optional repository or environment secret for authenticated API scans.

Do not derive target URLs from repository names. A scan must point at an authorized test environment.

## Organization Setup

1. Create or keep this repository public, or grant Actions read access to it from every caller repository.
2. Enable Actions and Code scanning for the organization. Give the deployment token `Contents: Read and write` on repositories where the workflow is installed; it also needs `Metadata: Read`.
3. Run `python deploy-workflows.py`. Use `DRY_RUN=true` first to inventory repositories without changing them. Use `python deploy-workflows.py --repo sample-dotnet-web-api --force` to test one application repository. The OWASP caller does not use advanced CodeQL, so it is compatible with organization-controlled CodeQL default setup.
4. Configure `SECURITY_DAST_TARGET_URL` and `SECURITY_API_URL` only for repositories that expose authorized test environments.
5. Protect the default branches and require the security workflow checks as appropriate for the organization.

The deployment script scans all repository API pages and skips this central repository, forks, and archived repositories. Re-run it when new repositories are added; existing caller workflows are left unchanged so local exceptions are preserved.

### Troubleshooting 403 Deployment Errors

If repository listing succeeds but deployment returns `403 Resource not accessible by personal access token`, the token can read the organization but cannot write workflow files. For a fine-grained token, select organization `sibydevops`, select the target repositories, grant `Contents: Read and write` and `Metadata: Read`, and obtain organization approval if required. The token owner must also have write access to those repositories. For a classic token, grant the `repo` scope and authorize it for organization SSO when SSO is enabled. Set the token in the same terminal that runs the script:

```powershell
$env:GITHUB_TOKEN = "YOUR_TOKEN"
python deploy-workflows.py --repo sample-python-flask-api
```

Never commit or paste the token into source files or issue comments.

If an application repository has no `.github/workflows/security-scan.yml`, it cannot trigger this pipeline. For example, install it in `sample-python-flask-api` with:

```powershell
$env:GITHUB_TOKEN = "YOUR_TOKEN"
python deploy-workflows.py --repo sample-python-flask-api
```

The token must be allowed to write workflow files. If the workflow already exists and needs the latest central version, add `--force`. A push to the application repository after installation triggers the caller and runs the centralized jobs in that repository's checkout.

## Local Validation

The mandatory caller starts OWASP Dependency-Check, OWASP ZAP, and OWASP ASTF jobs on every run. ZAP and ASTF perform active penetration testing only when authorized targets are configured; otherwise their jobs report that no target is applicable. If enabled, CodeQL default setup runs through GitHub's managed workflow separately. Pin the central workflow reference (`@main`) to a reviewed release tag when the organization adopts a release process.

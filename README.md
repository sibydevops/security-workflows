# security-workflows

Central repository for organization-wide OWASP security scanning workflows.

## How It Works

GitHub Actions runs in the repository that receives the `push` or `pull_request` event. The central repository therefore provides reusable workflows, and a small caller workflow is installed in each application repository. `deploy-workflows.py` installs that caller without overwriting an existing workflow.

This is important for scale: a workflow in `security-workflows` cannot receive `push` events from other repositories. For 10,000 repositories, use one of these organization designs:

- **Actions-only:** install the caller workflow in every repository. Reconcile it periodically with `python deploy-workflows.py --force`; new repositories need to be added to the deployment process.
- **Central event service:** install an organization GitHub App/webhook for `push` and `pull_request`, validate the event, and dispatch a scan for the changed repository. The service must use a GitHub App token and check out the event repository at the event SHA. Do not use a personal access token or scan arbitrary URLs.

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
3. Run `python deploy-workflows.py`. Use `DRY_RUN=true` first to inventory repositories without changing them. Use `python deploy-workflows.py --repo sample-dotnet-web-api` to test one application repository. Add `--force` when an existing caller must be updated.
4. Configure `SECURITY_DAST_TARGET_URL` and `SECURITY_API_URL` only for repositories that expose authorized test environments.
5. Protect the default branches and require the security workflow checks as appropriate for the organization.

The deployment script scans all repository API pages and skips this central repository, forks, and archived repositories. Re-run it when new repositories are added; existing caller workflows are left unchanged so local exceptions are preserved.

## Local Validation

The mandatory caller starts CodeQL, OWASP Dependency-Check, OWASP ZAP, and OWASP ASTF jobs on every run. ZAP and ASTF perform active penetration testing only when authorized targets are configured; otherwise their jobs report that no target is applicable. Pin the central workflow reference (`@main`) to a reviewed release tag when the organization adopts a release process.

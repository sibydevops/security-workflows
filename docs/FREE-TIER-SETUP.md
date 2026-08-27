# Organization OWASP Setup

This setup runs the central workflow for every `push` and `pull_request` event without adding workflow files to application repositories.

## Architecture

```text
Repository push or pull request
        -> GitHub App webhook
        -> Cloudflare Worker (free tier for testing)
        -> repository_dispatch
        -> security-workflows central workflow
        -> target repository checkout and OWASP scan
```

## Prerequisites

An organization owner must approve these steps. You need:

- A GitHub organization named `sibydevops`.
- A GitHub App installed on all repositories.
- A free Cloudflare account for the Worker endpoint.
- A public `security-workflows` repository, or App access to it.

## Deploy the free webhook Worker

Install Node.js, then from PowerShell:

```powershell
cd webhook-worker
npm install -g wrangler
wrangler login
wrangler secret put GITHUB_APP_ID
wrangler secret put GITHUB_APP_PRIVATE_KEY
wrangler secret put GITHUB_WEBHOOK_SECRET
wrangler deploy
```

When prompted, paste the App ID, the complete PEM private-key text, and a long random webhook secret. The command prints a URL like:

```text
https://central-owasp-webhook.<account>.workers.dev
```

Set the GitHub App webhook URL to:

```text
https://central-owasp-webhook.<account>.workers.dev/github/webhook
```

Set the webhook secret in GitHub to the same value used with `wrangler secret put GITHUB_WEBHOOK_SECRET`.

## Create the GitHub App

Open the organization App creation page and configure:

```text
App name: sibydevops-central-owasp
Homepage URL: https://github.com/sibydevops/security-workflows
Webhook URL: https://central-owasp-webhook.<account>.workers.dev/github/webhook
Webhook events: Push, Pull request, Repository
```

Use the same webhook secret already stored in the Worker. Grant:

```text
Contents: Read-only
Metadata: Read-only
Actions: Read and write
Checks: Read and write
Code scanning alerts: Read and write
Pull requests: Read-only
```

Create the App, copy the App ID, generate and download its private key, set `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` in the Worker, then install the App on the organization with **All repositories** selected.

## Configure the central repository

In `security-workflows` repository settings, create these Actions secrets:

```text
SECURITY_APP_ID          App ID
SECURITY_APP_PRIVATE_KEY Complete PEM private key
```

Push the workflow changes in this repository to `main`. The central receiver is `.github/workflows/central-security-dispatch.yml`.

## Test

1. In the GitHub App settings, open **Advanced**, then **Recent Deliveries**.
2. Push a harmless change to any test repository.
3. Confirm the delivery has a `200` or `202` response.
4. Open `security-workflows -> Actions`.
5. Confirm `Central OWASP Security Scan` starts.
6. Run the central workflow manually once with `workflow_dispatch` if desired.

A push event uses the commit SHA in `after`. A pull request event uses the pull request head SHA. The Worker rejects invalid signatures and repositories outside the organization.

## Active OWASP testing

OWASP Dependency-Check can scan repository dependencies without a URL. OWASP ZAP and API penetration testing need an HTTP target. Configure a staging URL or a startup command and port in the central scan implementation before enabling active testing. Do not scan systems without authorization.

## Production hardening

The Worker currently dispatches the event and returns immediately. For 10,000 repositories, add a queue, delivery-ID deduplication, retries, rate-limit handling, and concurrency controls. Cloudflare free tier is suitable for initial testing, not a guarantee for 10,000-repository production traffic.

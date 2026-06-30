# Veriguard — Agentic SOC Platform

Unified MSSP Console + Comply platform built on AWS Security Agent and AWS
Continuum. Veriguard gives an MSSP one pane of glass to run multi-tenant
security operations (findings, SLA, billing) and continuous compliance
(control mapping, audit-ready evidence, posture drift) for every customer
they manage.

## Repo contents

| Folder | What's in it |
|---|---|
| [`pitch-deck/`](pitch-deck/) | `Veriguard_Pitch_Deck.pptx` — 13-slide investor/customer pitch deck |
| [`docs/`](docs/) | `Veriguard_Architecture_PRD.docx` — 13-page architecture & product requirements doc |
| [`demo/`](demo/) | `Veriguard_Demo.html` — single-file clickable demo (MSSP Console + Comply), plus its jsdom smoke test |
| [`cloudformation/`](cloudformation/) | Deployable, serverless AWS CloudFormation package — see its own [README](cloudformation/README.md) |

## Quick start: run the demo

Open `demo/Veriguard_Demo.html` directly in a browser. No build step, no
server — it's a single self-contained file (Tailwind/Chart.js/Lucide via CDN)
with mock data for 6 tenants.

## Quick start: deploy the platform

```bash
cd cloudformation
aws cloudformation deploy --template-file veriguard-platform.yaml \
  --stack-name veriguard-platform --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides EnvironmentName=prod
```

See [`cloudformation/README.md`](cloudformation/README.md) for the full
deployment runbook, per-customer onboarding stack, parameter reference, and
what's real vs. stubbed (AWS Continuum has no CloudFormation support yet).

## Status

Pitch deck, PRD, and clickable demo are complete. CloudFormation templates
are written, cfn-lint clean, and ready to deploy — not yet deployed or
tested against a live AWS account.

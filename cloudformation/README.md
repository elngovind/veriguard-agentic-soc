# Veriguard — Serverless AWS Deployment Package

## Can I deploy this myself, or can you do it?

I cannot run the deployment for you. This sandbox has no AWS account, no credentials,
and no network path to your AWS environment — I can't call `aws cloudformation deploy`,
can't create an AWS Security Agent pentest, and can't verify a live stack. What I've
built is genuinely deployable: real CloudFormation resource types, verified against
AWS's documentation, that **you** run with your own AWS credentials. Everything below
is ready to go; nothing has been faked or stubbed except the one piece called out in
"What's real vs. stubbed."

## What's in this package

| File | Purpose |
|---|---|
| `veriguard-platform.yaml` | Central serverless backend: API, data, eventing, evidence store, auth. Deploy once. |
| `veriguard-customer-onboarding.yaml` | Per-customer AWS Security Agent setup. Deploy once **per customer**, inside *their* AWS account. |
| `seed_data.py` | Loads the same demo dataset used in `Veriguard_Demo.html` into the live DynamoDB tables. |
| `README.md` | This file. |

## Architecture (platform stack)

All AWS-managed, pay-per-use, zero idle cost — no EC2, no containers, no VPC, no Aurora.

- **API**: API Gateway HTTP API, JWT-authorized via Cognito User Pool
- **Compute**: 6 Lambda functions (Python 3.12), inline code, one per API resource
- **Data**: 5 DynamoDB tables (`PAY_PER_REQUEST`), point-in-time recovery on
- **Evidence storage**: S3 with Object Lock (Compliance mode) — evidence packages are
  immutable once written, satisfying audit-grade retention
- **Eventing**: EventBridge bus → rule → SQS queue with DLQ (5 retries before parking)
- **Orchestration**: Step Functions standard workflow drives evidence-package generation
- **Auth**: Cognito User Pool + App Client

## What's real vs. stubbed

- **AWS Security Agent** (`AWS::SecurityAgent::*` resources in the onboarding template):
  real CloudFormation resource types, confirmed against AWS's official CFN resource
  reference and IAM role guide. `AgentSpace`, `Application`, `TargetDomain`, and
  `Pentest` will actually provision in an account with Security Agent enabled.
- **AWS Continuum**: still gated preview with **no CloudFormation resource type** as of
  this writing. There is nothing to provision via CFN for it. The platform template
  does not reference it. When AWS ships Continuum's CFN support (or a usable API), the
  drift-remediation Lambda becomes the integration point — right now there's no
  automated remediation path, only the detection/evidence pipeline above.
- One manual step the onboarding template cannot avoid: **domain-verification tokens
  (DNS TXT value or HTTP route path) are not exposed through CloudFormation.** After
  deploying `veriguard-customer-onboarding.yaml`, open the Security Agent console for
  the new AgentSpace, retrieve the token, publish it, and wait for `VERIFIED` status
  before the pentest can run. This is an AWS console limitation, not a gap in the
  template.

## Application singleton (read before deploying a 2nd onboarding stack in the same account)

`AWS::SecurityAgent::Application` is **one per AWS account, account-wide** — not
per customer, not per AgentSpace. AWS confirmed this via a real deploy error:

```
Application already exists for account <id>. Only one application per account
is allowed. (HandlerErrorCode: AlreadyExists)
```

AWS auto-provisions that one Application when Security Agent is first activated
in an account. `veriguard-customer-onboarding.yaml` does **not** create an
`Application` resource — it only creates `TargetDomain`, `AgentSpace`, `Pentest`,
and the IAM roles, none of which reference an `ApplicationId`. If you want the
account's existing Application to use this customer's `ApplicationRole` (e.g. so
a WebApp user can assume it), do that as a one-time, account-level, manual step:

```bash
aws securityagent get-application
aws securityagent update-application --role-arn <ApplicationRoleArn-from-stack-output>
```

This only needs to happen once per AWS account, regardless of how many
onboarding stacks (customers) you deploy into it.

## Deploy: platform stack (once)

```bash
aws cloudformation deploy \
  --template-file veriguard-platform.yaml \
  --stack-name veriguard-platform \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides EnvironmentName=prod EvidenceRetentionYears=1
```

Then seed demo data (optional, safe to skip in a real customer environment):

```bash
pip install boto3 --break-system-packages
python3 seed_data.py --stack-name veriguard-platform --region us-east-1
```

Get the API URL and User Pool info:

```bash
aws cloudformation describe-stacks --stack-name veriguard-platform \
  --query 'Stacks[0].Outputs'
```

Create a test user in the Cognito pool to call the API:

```bash
aws cognito-idp sign-up --client-id <UserPoolClientId> \
  --username you@example.com --password '<StrongPass123!>'
aws cognito-idp admin-confirm-sign-up --user-pool-id <UserPoolId> --username you@example.com
```

## Deploy: per-customer onboarding (once per customer, in *their* account)

```bash
aws cloudformation deploy \
  --template-file veriguard-customer-onboarding.yaml \
  --stack-name veriguard-onboarding-acme \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    CustomerName=acme \
    TargetDomainName=app.acme.com \
    VeriguardManagementAccountId=111111111111 \
    VerificationMethod=DNS_TXT \
    ExternalId=$(uuidgen) \
    TargetArchitecture=ApiGateway
```

Generate a fresh `ExternalId` per customer (e.g. `uuidgen`) and store it in Secrets
Manager — it's the confused-deputy guard on both cross-account roles. After deploy,
complete domain verification in the Security Agent console (see above), then start
the pentest.

## Parameter reference

**veriguard-platform.yaml**

| Parameter | Default | Notes |
|---|---|---|
| `EnvironmentName` | `dev` | Tag applied to all resource names |
| `EvidenceRetentionYears` | `1` | WORM retention floor on the evidence bucket |

**veriguard-customer-onboarding.yaml**

| Parameter | Default | Notes |
|---|---|---|
| `CustomerName` | — | Lowercase, used in role/resource names |
| `TargetDomainName` | — | App domain to be pentested |
| `VeriguardManagementAccountId` | — | Your Veriguard AWS account ID |
| `VerificationMethod` | `DNS_TXT` | or `HTTP_ROUTE` |
| `ExternalId` | — | Unique per customer; required, no default |
| `TargetArchitecture` | `ApiGateway` | or `LambdaFunctionUrl`, `AlbCognito` — scopes the Actor Role |

## Cost shape

Every resource is pay-per-request or pay-per-invocation: DynamoDB on-demand, Lambda,
HTTP API, Step Functions, SQS, EventBridge, S3, Cognito. At zero traffic the platform
stack costs roughly nothing — no Aurora minimum ACUs, no NAT gateway, no idle compute.
Costs scale with API calls, pentest frequency, and evidence-package volume.

## Validation performed

Both templates were checked for structural correctness (parameter/resource/output
references, `!Sub`/`!GetAtt` usage, IAM trust policy shape, DynamoDB key schemas) since
there's no AWS account in this environment to test-deploy against. Treat this as
"should deploy cleanly," not "deployed and confirmed." Recommended before your first
real deploy:

```bash
pip install cfn-lint --break-system-packages
cfn-lint veriguard-platform.yaml veriguard-customer-onboarding.yaml
```

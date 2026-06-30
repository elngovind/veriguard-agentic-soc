#!/usr/bin/env python3
"""
Veriguard — seed_data.py

Loads the demo dataset (6 tenants, findings, evidence packages, drift events,
control mappings) into the DynamoDB tables created by veriguard-platform.yaml.

Reads table names from the deployed stack's CloudFormation outputs, so it only
needs the stack name:

    pip install boto3 --break-system-packages
    python3 seed_data.py --stack-name veriguard-platform --region us-east-1

Safe to re-run: every put_item overwrites by primary key.
"""
import argparse
import datetime
import boto3


def stack_outputs(cfn, stack_name):
    desc = cfn.describe_stacks(StackName=stack_name)["Stacks"][0]
    return {o["OutputKey"]: o["OutputValue"] for o in desc["Outputs"]}


TENANTS = [
    {"tenantId": "T-001", "name": "Northwind Logistics", "tier": "Enterprise", "mrr": 18500, "slaTarget": 99.9, "slaActual": 99.94, "openFindings": 4, "framework": "SOC 2"},
    {"tenantId": "T-002", "name": "Bluepeak Health", "tier": "Enterprise", "mrr": 24200, "slaTarget": 99.95, "slaActual": 99.91, "openFindings": 7, "framework": "HIPAA"},
    {"tenantId": "T-003", "name": "Granite Financial", "tier": "Growth", "mrr": 9800, "slaTarget": 99.9, "slaActual": 99.97, "openFindings": 2, "framework": "PCI DSS"},
    {"tenantId": "T-004", "name": "Solace Retail Group", "tier": "Growth", "mrr": 7400, "slaTarget": 99.5, "slaActual": 99.61, "openFindings": 5, "framework": "SOC 2"},
    {"tenantId": "T-005", "name": "Ironclad Manufacturing", "tier": "Standard", "mrr": 4100, "slaTarget": 99.5, "slaActual": 99.38, "openFindings": 9, "framework": "ISO 27001"},
    {"tenantId": "T-006", "name": "Vantage Public Schools", "tier": "Standard", "mrr": 2600, "slaTarget": 99.0, "slaActual": 99.52, "openFindings": 1, "framework": "FERPA"},
]

SEVERITIES = ["Critical", "High", "Medium", "Low"]
FINDINGS = [
    {"findingId": f"F-{1000+i}", "tenantId": t["tenantId"], "title": title, "severity": sev, "cvss": cvss,
     "status": status, "detectedAt": "2026-06-" + day}
    for i, (t, title, sev, cvss, status, day) in enumerate([
        (TENANTS[0], "Unauthenticated S3 bucket listing", "Critical", 9.1, "Open", "02"),
        (TENANTS[0], "Outdated TLS cipher suite on public ALB", "Medium", 5.3, "Open", "04"),
        (TENANTS[0], "Verbose error messages leak stack traces", "Low", 3.1, "Open", "05"),
        (TENANTS[0], "IAM role with wildcard resource policy", "High", 7.4, "Open", "06"),
        (TENANTS[1], "SQL injection in patient search endpoint", "Critical", 9.8, "Open", "01"),
        (TENANTS[1], "PHI field returned without encryption flag", "Critical", 9.4, "Open", "01"),
        (TENANTS[1], "Session token does not expire", "High", 7.1, "Open", "03"),
        (TENANTS[1], "Missing MFA on admin console", "High", 8.0, "Open", "03"),
        (TENANTS[1], "Stale dependency: log4j-core 2.14", "Critical", 9.0, "Open", "07"),
        (TENANTS[1], "CORS misconfiguration on API gateway", "Medium", 6.1, "Open", "08"),
        (TENANTS[1], "Predictable password reset token", "Medium", 5.9, "Open", "09"),
        (TENANTS[2], "Cardholder data cached in application logs", "Critical", 8.9, "Open", "02"),
        (TENANTS[2], "Weak TLS on payment webhook endpoint", "Medium", 5.0, "Open", "10"),
        (TENANTS[3], "Open redirect on checkout flow", "Medium", 4.7, "Open", "11"),
        (TENANTS[3], "Excessive IAM permissions on CI role", "High", 7.0, "Open", "12"),
        (TENANTS[3], "Missing rate limiting on login endpoint", "Medium", 5.4, "Open", "13"),
        (TENANTS[3], "Default credentials on internal admin tool", "Critical", 9.6, "Open", "13"),
        (TENANTS[3], "Outdated WordPress plugin (CVE-2026-1190)", "High", 7.8, "Open", "14"),
    ])
]

EVIDENCE_PACKAGES = [
    {"packageId": "EP-A1B2C3D4", "tenantId": "T-001", "framework": "SOC 2", "periodStart": "2026-01-01", "periodEnd": "2026-03-31", "status": "LOCKED", "generatedAt": "2026-04-02T10:15:00Z"},
    {"packageId": "EP-B2C3D4E5", "tenantId": "T-002", "framework": "HIPAA", "periodStart": "2026-01-01", "periodEnd": "2026-03-31", "status": "LOCKED", "generatedAt": "2026-04-03T09:30:00Z"},
    {"packageId": "EP-C3D4E5F6", "tenantId": "T-003", "framework": "PCI DSS", "periodStart": "2026-01-01", "periodEnd": "2026-03-31", "status": "LOCKED", "generatedAt": "2026-04-03T14:05:00Z"},
    {"packageId": "EP-D4E5F6G7", "tenantId": "T-004", "framework": "SOC 2", "periodStart": "2026-01-01", "periodEnd": "2026-03-31", "status": "LOCKED", "generatedAt": "2026-04-04T11:45:00Z"},
    {"packageId": "EP-E5F6G7H8", "tenantId": "T-005", "framework": "ISO 27001", "periodStart": "2026-01-01", "periodEnd": "2026-03-31", "status": "LOCKED", "generatedAt": "2026-04-05T08:20:00Z"},
    {"packageId": "EP-F6G7H8I9", "tenantId": "T-006", "framework": "FERPA", "periodStart": "2026-01-01", "periodEnd": "2026-03-31", "status": "LOCKED", "generatedAt": "2026-04-05T16:10:00Z"},
]

DRIFT_EVENTS = [
    {"driftId": "D-001", "tenantId": "T-001", "control": "CC6.1 — Logical Access", "description": "New IAM user created without MFA enforced", "detectedAt": "2026-06-20T03:11:00Z", "severity": "High"},
    {"driftId": "D-002", "tenantId": "T-002", "control": "164.312(a)(1) — Access Control", "description": "S3 bucket encryption default removed", "detectedAt": "2026-06-21T07:42:00Z", "severity": "Critical"},
    {"driftId": "D-003", "tenantId": "T-003", "control": "Req 3 — Protect Stored Data", "description": "CloudTrail logging disabled in one region", "detectedAt": "2026-06-22T12:05:00Z", "severity": "Critical"},
    {"driftId": "D-004", "tenantId": "T-004", "control": "CC7.2 — System Monitoring", "description": "Security group opened to 0.0.0.0/0 on port 22", "detectedAt": "2026-06-24T18:30:00Z", "severity": "High"},
    {"driftId": "D-005", "tenantId": "T-005", "control": "A.9.2 — User Access Mgmt", "description": "Stale IAM access key (>180 days) still active", "detectedAt": "2026-06-26T05:55:00Z", "severity": "Medium"},
]

CONTROL_MAPPINGS = [
    {"mappingId": "M-001", "framework": "SOC 2", "control": "CC6.1", "description": "Logical access security measures", "automatedCheck": "IAM MFA enforcement scan"},
    {"mappingId": "M-002", "framework": "SOC 2", "control": "CC7.2", "description": "System monitoring for anomalies", "automatedCheck": "Security group exposure scan"},
    {"mappingId": "M-003", "framework": "HIPAA", "control": "164.312(a)(1)", "description": "Access control for ePHI", "automatedCheck": "S3/RDS encryption-at-rest scan"},
    {"mappingId": "M-004", "framework": "PCI DSS", "control": "Req 3", "description": "Protect stored cardholder data", "automatedCheck": "CloudTrail + KMS audit"},
    {"mappingId": "M-005", "framework": "ISO 27001", "control": "A.9.2", "description": "User access management", "automatedCheck": "Stale credential scan"},
    {"mappingId": "M-006", "framework": "FERPA", "control": "34 CFR 99.31", "description": "Conditions for disclosure of student records", "automatedCheck": "Data-sharing policy scan"},
]


def batch_put(table, items):
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    print(f"  loaded {len(items)} items into {table.table_name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack-name", default="veriguard-platform")
    ap.add_argument("--region", default="us-east-1")
    args = ap.parse_args()

    cfn = boto3.client("cloudformation", region_name=args.region)
    outputs = stack_outputs(cfn, args.stack_name)
    ddb = boto3.resource("dynamodb", region_name=args.region)

    print(f"Seeding stack '{args.stack_name}' in {args.region} at {datetime.datetime.utcnow().isoformat()}Z")
    batch_put(ddb.Table(outputs["TenantsTableName"]), TENANTS)
    batch_put(ddb.Table(outputs["FindingsTableName"]), FINDINGS)
    batch_put(ddb.Table(outputs["EvidencePackagesTableName"]), EVIDENCE_PACKAGES)
    batch_put(ddb.Table(outputs["DriftEventsTableName"]), DRIFT_EVENTS)
    batch_put(ddb.Table(outputs["ControlMappingsTableName"]), CONTROL_MAPPINGS)
    print("Done.")


if __name__ == "__main__":
    main()

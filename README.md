# Collaboration Ops Lab

An offline, deterministic laboratory for reconciling synthetic directory identities, messaging mailboxes and group memberships. It demonstrates safe comparison and review workflows without administering Microsoft 365, Exchange, Entra ID, CERN systems or any real tenant.

## Problem and approach

Collaboration platforms accumulate mismatches between identity sources and messaging services. This lab validates two local JSON snapshots, normalizes case-sensitive identifiers, detects inconsistencies and emits a dry-run report for human review. It never creates, updates or deletes an account.

Implemented checks:

- missing or mismatched mailboxes;
- orphaned mailboxes and groups, always marked for manual review;
- missing and unexpected group memberships;
- duplicate identities and memberships;
- malformed, blank or incorrectly typed input fields;
- deterministic ordering and explicit zero-write safety metadata.

## Architecture

`fixtures -> validation -> reconciliation -> JSON dry-run report`

See [docs/architecture.md](docs/architecture.md) for the Mermaid diagram, trust boundaries and optional Microsoft Graph development-tenant boundary.

## Technology

- Python 3.11+ standard library only: portable execution and no runtime dependency supply chain.
- `unittest`: focused coverage of reconciliation and validation risks.
- GitHub Actions: compilation, tests and a reproducible CLI smoke run on Python 3.11 and 3.12.
- Optional PowerShell example: isolated, read-only Microsoft Graph exploration for an authorized development tenant.

## Run locally

```bash
python -m unittest discover -s tests -v
python -m collab.cli \
  --directory fixtures/directory.json \
  --messaging fixtures/messaging.json \
  --output reports/reconciliation.json
```

The example currently produces seven review findings from synthetic data. `reports/` is ignored because every report is reproducible from the fixtures.

## Optional Microsoft Graph boundary

Live Graph integration is **not implemented or validated**. `scripts/graph_dev_readonly.ps1` is a guarded demonstration that may only be run against an authorized development tenant. It requests delegated `User.ReadBasic.All`, reads at most five basic user records and writes nothing to disk. Do not use an employer, CERN or production tenant.

## Verification

```bash
python -m compileall -q collab tests
python -m unittest discover -s tests -v
```

The test suite covers normal reconciliation, deterministic output, disabled identities, duplicate keys, duplicate members, malformed fields and the zero-write contract.

## Limitations

- All data is synthetic; no operational Microsoft 365 experience is implied.
- There is no authentication, remote provider, write-back, scheduling or tenant-scale pagination.
- Email syntax is treated as an opaque identifier rather than fully validated.
- Findings are proposals, not approved remediation actions.

## Next steps

1. Define a provider interface only when an authorized development tenant is available.
2. Add a read-only Graph adapter with pagination, redacted logging and recorded permission review.
3. Test rate-limit and partial-response behavior using controlled mocks before any live validation.

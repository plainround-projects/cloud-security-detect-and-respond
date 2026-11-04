# cloud-security-detect-and-respond

The detection-and-response layer for a sandbox cloud account, as code: every action logged to a tamper-resistant archive in a separate account, five detections kept as data and deployed as rules, posture management with a recorded baseline, and a rehearsed response, with the incident timeline rebuilt from the archive alone, time to detect and time to contain measured, and the compromised role's sessions revoked from the evidence.

| | |
| --- | --- |
| **Lesson** | `/prep/cloud-security/project-detect-and-respond`, "Detect and respond" (`data-structure-explainer/src/content/tracks/cloud-security/15-project-detect-and-respond.md` in the Plainround app) |
| **Planned hours** | 14 |
| **Level** | Advanced |
| **Architecture** | [ARCHITECTURE.md](ARCHITECTURE.md); detections: [docs/DETECTIONS.md](docs/DETECTIONS.md); the rehearsal's review: [docs/REHEARSAL_REVIEW.md](docs/REHEARSAL_REVIEW.md); account runbook: [docs/RUNBOOK.md](docs/RUNBOOK.md); decisions: [docs/adr](docs/adr) |

## Architecture

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/diagrams/architecture-dark.svg">
  <img alt="In the workload account the drill-user assumes the broad role and makes the data bucket public; the audit trail sends every call to a log archive in a separate security account and to the detection rules, which alert the responder, and the detect_respond tool replays the same detections over the archive." src="docs/diagrams/architecture.svg">
</picture>

Notice that the archive lives in another account under Object Lock, and that the detections in detections/*.json are the one thing both the rules and the tool read.

## How one run flows

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/diagrams/flow-dark.svg">
  <img alt="One rehearsal scans the archive for alerts, rebuilds the timeline, measures the clock, verifies the digests, builds the posture baseline, plans containment and writes the review, all from the logs alone." src="docs/diagrams/flow.svg">
</picture>

The run ends with a review and the two measures, detect 32 s and contain 6 min 52 s; the amber row shows that containment is not confirmed if the attacker never calls again.

## Prerequisites

| Tool | Version | Used for |
| --- | --- | --- |
| Python | 3.12 or 3.13 (tested with 3.13; CI uses 3.12) | the responder's tooling and the tests |
| Terraform | 1.9 or newer (tested with 1.17.0); `TF=tofu` works for OpenTofu | `fmt`, `validate`, the credential-free plans |
| tflint | 0.65 (with the AWS ruleset 0.38, installed by `tflint --init`) | Terraform lint |
| checkov | 3.3 (tested with 3.3.30) | security scan of the Terraform |
| OPA | 1.x (tested with 1.21.4) | policy rules and their tests |
| ShellCheck | 0.9 or newer | lint of the runbook scripts |
| GNU Make | 3.81 or newer | every command below |
| Python packages | `boto3` at run time (containment only); pytest, pytest-cov, ruff, mypy, import-linter, pip-audit for development; pinned with hashes in `requirements.lock` and `requirements-dev.lock`; `make` installs them into `.venv/` | everything |
| Cloud accounts | **none** for `make validate`, `lint`, `test` and `demo-drill`. **Two** sandbox AWS accounts you own (a security account and a workload account, for example two members of one organization), each with a budget, for `make up`, `run`, `attack`, `respond`, `measure` and `down` | the lesson's real drill |

Nothing in the offline path calls a cloud API or needs credentials: the plans run with `plan_only = true` and placeholder environment values, and the rehearsal replays a synthetic archive (documentation addresses, a placeholder account, made-up key ids). No secret is in the repository.

## Setup, run, test, stop

```bash
make install       # .venv from the hash-pinned lock file
make validate      # fmt, validate, credential-free plans of both accounts, policy rules, rules equal detections/, the rehearsal, the review is current
make demo-drill    # the rehearsal alone: alerts, timeline, time to detect and contain, archive integrity, posture baseline, a containment dry run
make lint          # ruff, mypy, import rules, terraform fmt, tflint, checkov, opa check, shellcheck
make test          # 105 unit tests with coverage (99 percent), and the 31 policy tests
make test-e2e      # the offline pipeline through make, as a reader runs it
make audit         # known-vulnerability check of the locked dependencies
make fixtures      # regenerate the synthetic archive and posture findings (a test checks they are current)
make review        # regenerate docs/REHEARSAL_REVIEW.md
make up            # deploy the archive (security account), then the trail and detections (workload account)
make run           # verify the archive, plant the drill exception, take the posture baseline
make attack        # play the attacker against the drill resources
make respond       # contain from the evidence (a dry run; make respond APPLY=--apply)
make measure       # copy the archive out, verify it, rebuild the timeline, measure both times, write the review
make down          # remove the exception and delete the workload account's resources
```

`make help` lists every target. The targets from `up` to `down` need accounts; their scripts refuse to run unless each profile belongs to the account you named and the caller is not the root user. The CLI is also usable directly:

```bash
.venv/bin/python -m detect_respond --help      # scan, drill, review, contain, verify-archive, posture, audit-rules
```

## Cost (the drill is optional, and uses your accounts)

The offline pipeline costs nothing. A day of the real drill is expected to stay under three US dollars; the posture services (AWS Config and Security Hub) are the part to watch if left on. The Terraform creates a budget that alerts at 80 percent of 20 US dollars actual and 100 percent forecast. Prices are approximate list prices; check the provider's pricing pages. The table, the teardown order and the one thing that outlives the exercise (the compliance-mode archive, for a day or two) are in [docs/RUNBOOK.md](docs/RUNBOOK.md).

## What the offline rehearsal shows

`make demo-drill` replays a synthetic archive that follows the lesson's timeline (the archive has the layout of the real bucket: log files per Region and day, and a digest file):

```text
== detections over the archive (D1, D2 and D4 must fire)
6 alerts from detections: D1, D2, D4
== the timeline, from the logs only
11:03:10  AssumeRole         drill-broad-role session "intruder"      OK
11:03:21  ListBuckets        -                                        OK
11:03:42  CreateAccessKey    drill-user                               OK       <- D1 fires
11:04:05  PutBucketAcl       drill-data-000000000000 (public-read)    OK       <- D2 fires
11:04:31  DescribeInstances  ap-southeast-2                           OK       <- D4 fires
11:09:48  (responder) PutRolePolicy      drill-broad-role                         OK
11:09:57  (responder) UpdateAccessKey    drill-user                               OK
11:10:02  CreateAccessKey    drill-user                               DENIED   <- D1 fires

time to detect:  32 s  (first action 11:03:10, first alert 11:03:42)
time to contain: 6 min 52 s  (first action 11:03:10, next call refused 11:10:02)
== the archive against its digests
digest 1: 3 files checked, 0 changed, 0 missing
every logged file matches its digest
== the posture baseline
severity    findings at start    after fixing    accepted with reason
critical                    2               0                       0
high                        7               2                       5
medium                      0               0                       0
low                         0               0                       0
== containment, as a dry run
dry run, nothing changed; to do it, add --apply:
aws iam put-role-policy --role-name drill-broad-role --policy-name deny-all-before-now --policy-document '{"Version":"2012-10-17","Statement":[{"Sid":"DenySessi
aws iam update-access-key --user-name drill-user --access-key-id AKIADRILLEXAMPLE0001 --status Inactive
```

Time to detect is 32 seconds and time to contain 6 minutes 52 seconds, the lesson's own example numbers, computed from the logs. D1 fires three times in the archive (a legitimate setup key at 10:52, the attacker's key at 11:03:42, and the attacker's refused retry at 11:10:02), which is why the alert text carries who and from where and the first step is "ask who made it".

## Done when: the lesson's checklist and the proof for each line

| # | Done when (from the lesson) | Offline proof (no account) | Proof in the sandbox accounts |
| --- | --- | --- | --- |
| 1 | An action in the account appears in the central store within minutes, and an account administrator cannot delete or alter the log. | OPA rules on both plans (`make validate`): the archive bucket is in a separate environment, has Object Lock in compliance mode, versioning, a customer-managed key, Block Public Access and a policy that denies deleting objects and versions to every principal and admits only the one pinned trail; the trail is multi-region with log file validation and logs to a bucket that is not in its own plan. `verify-archive` shows that an altered or deleted log file no longer matches its digest (tests alter one). | `scripts/03-verify-archive.sh` performs an action, waits for the file, tries to delete it as an administrator of each account (both must be refused) and runs `aws cloudtrail validate-logs`. **Needs two accounts.** |
| 2 | Performing each of the actions yourself raises its alert with enough detail to act on. | `detections/` D1 to D4 with positive and near-miss tests for each (`make test`); `scan` renders each alert with user, source address, request, Region, event id and first step; `audit-rules` proves the plan deploys exactly those patterns in the right Regions, and D4 with the rule state that includes read-only calls. | `make attack` performs D1, D2 and D4; the alert emails arrive per Region (confirm the subscriptions). **Needs an account.** |
| 3 | The baseline is recorded and the critical findings are resolved or accepted with a reason. | `posture` computes the lesson's table from two findings files and the accepted risks (`fixtures/posture`: critical 2 to 0, high 7 to 2 with 5 accepted) and exits 1 on an unfixed critical finding or an acceptance with no reason (tests). | `scripts/05-posture-baseline.sh before` and `after`, with `docs/posture-acceptances.json`. **Needs an account.** |
| 4 | The credential works, and you have written down what it can do before you start. | The `drill` module is the only place the OPA rules allow `PowerUserAccess`, an IAM user and open Block Public Access; no resource creates an access key. | `scripts/04-drill-setup.sh` writes `evidence/drill-capabilities.txt` before anything runs. **Needs an account.** |
| 5 | The timeline is built only from the logs, revocation stops the next action, and you measured time to detect and time to contain. | `drill` rebuilds the timeline from the archive folder alone, denied calls included, and measures 32 s and 6 min 52 s on the rehearsal; `contain` denies the role's sessions issued before now and deactivates the keys (tested with fakes and the SDK stubber), a dry run by default. | `make attack`, `make respond APPLY=--apply`, `make measure`. **Needs an account.** |
| 6 | The review separates prevention from detection, every claim cites a log entry, and the exception is gone. | [docs/REHEARSAL_REVIEW.md](docs/REHEARSAL_REVIEW.md) is generated from the rehearsal archive: a timeline with an event id on every row, a "prevented or only recorded" table, and the changes that would prevent recurrence; `make validate` fails if it is stale. | `make measure` writes `evidence/REVIEW.md` from your logs; `make down` removes the exception and prints the time. **Needs an account.** |

## Stretch goals

| Stretch (from the lesson) | Built? |
| --- | --- |
| Add an automated response that disables a credential when a high-severity detection fires, and test it. | No. `contain` is the building block, tested with fakes; ADR 0003 says why the automation needs its own guardrails. |
| Add a honeytoken and alert on any use of it. | Yes. D5 (`detections/d5-honeytoken-used.json`), the honeytoken user in the drill module, `scripts/06-honeytoken.sh`, and tests that D5 fires only on that key id. Deploying it and seeing a real alert needs an account. |
| Export one detection as code so it is version-controlled and tested. | Yes. Every detection is a file in `detections/`; the same file is deployed and replayed ([ADR 0001](docs/adr/0001-detections-are-data-with-one-source-of-truth.md)). |

## What is simplified for teaching

Only what the lesson scopes out, plus where this build differs from the lesson's text:

- Nothing is deployed from here. The account steps are scripts and a runbook that have not been run against real accounts; the offline replay is what was verified. The runbook lists what to confirm (the alert text, the event-pattern corners, the cross-account delivery).
- The rehearsal archive is synthetic. It follows the lesson's timeline and its numbers; real latency, event ordering and field details will differ.
- The drill role has `PowerUserAccess` plus permission to create a key for the drill user only, because `PowerUserAccess` leaves out IAM and the lesson's timeline needs the key creation to succeed.
- Retention is one day, in compliance mode, so the archive can be removed afterward; a production archive keeps logs for the period your obligations require.
- Detection rules run in three Regions chosen by hand; the batch scan covers all Regions.
- Alerts go to email. Time to detect uses the event time unless you record when each alert reached you (`evidence/alerts.json`).
- Local Terraform state, because the sandbox is deleted the same day.

## Project structure

```text
src/detect_respond/
  domain/                events and their parsing, the event-pattern matcher, detections, alert text, the timeline, drill measures,
                         containment, archive digests, posture baselines, named errors. Depends on the standard library only.
  application/           scan, run the drill, contain, verify the archive, baseline the posture; ports for the archive, the
                         catalog, the revoker, the clock and the posture files. Depends on domain only.
  infrastructure/        the archive folder reader (plain and gzip), detection and posture files, the boto3 IAM adapter, the plan
                         audit. Depends on application and domain.
  interfaces/            the command line and the text and Markdown rendering. Nothing depends on it.
detections/              one JSON file per detection (D1 to D5) and the alert template: the single source of truth.
infra/
  modules/               kms-key, log-archive, central-trail, alerting, drill, posture, budget; each with a README.
  environments/security/ the security account: the archive. environments/workload/: the trail, detections, posture, drill, budget.
policy/                  detection.rego and detection_test.rego: the OPA rules and a deny and an allow test for each.
docs/                    DETECTIONS.md, REHEARSAL_REVIEW.md (generated), RUNBOOK.md, posture-acceptances.json, adr/.
tech/                    one beginner-level note per technology used here (Python, Terraform, OPA, the AWS services, Bash, ...), starting at tech/README.md.
fixtures/                drill/ (the synthetic archive: log files, a digest, alerts.json) and posture/ (findings and accepted risks).
scripts/                 the account runbook 01 to 10 and lib.sh; make_drill_fixtures.py writes fixtures/ deterministically.
tests/
  unit/                  the matcher, the detections, the drill measures, containment, the archive, posture, the plan audit, the
                         command line, and a check that the committed fixtures are what the generator writes. No services.
  e2e/                   the offline pipeline through make (needs terraform and opa).
Makefile                 the only commands a reader needs (make help).
pyproject.toml           project metadata and every tool's configuration. requirements*.lock: hash-pinned dependencies.
```

The dependency rule (domain depends on nothing; application on domain; infrastructure and interfaces on both; nothing on interfaces) is enforced by `make lint` through import-linter. A second contract keeps boto3 out of `domain` and `application`. There is no integration test folder: the only external dependency is IAM, covered by the SDK's stubber in the unit tests, and the real-service checks are the account scripts.

## Author and license

Written by Sumit Srivastava. Released under the MIT License, see [LICENSE](LICENSE). Changes are in [CHANGELOG.md](CHANGELOG.md).

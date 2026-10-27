# Checkov

## What it is

Checkov is a command-line **security scanner for infrastructure code**. It reads Terraform files and compares each resource with a library of hundreds of checks, each with an id such as `CKV_AWS_18` ("Ensure the S3 bucket has access logging enabled"). It reports which checks passed, failed or were skipped. This repository pins **Checkov 3.3.30** (installed as a tool, for example `pipx install checkov==3.3.30` in CI; it is not in the Python lock files because it has a very large dependency tree).

## Why this repository uses it

The lesson is about hardening, and a scanner finds common weaknesses a human forgets (no encryption, no versioning, a public bucket). It runs in `make lint` so the Terraform cannot regress. Where a check does not apply, the repository does not silence it globally: each exception is written next to the resource with a reason.

## Where it appears

| Path | What it does |
| --- | --- |
| `Makefile` | `checkov -d infra --framework terraform --quiet --compact` in `make lint` |
| `infra/modules/*/main.tf` | `#checkov:skip=...` comments, 24 in total |
| `.github/workflows/ci.yml` | installs the pinned version with `pipx` |

## How it works underneath

Checkov parses the Terraform files (it does not need Terraform installed to scan, and it never contacts AWS), builds a graph of the resources and the references between them, and evaluates each check against it. Some checks look at one attribute (`enable_key_rotation`); others follow connections ("does this bucket have a matching public-access-block resource?"). A **skip comment** inside a resource block suppresses one check for that resource only and records the reason in the report.

## Walkthrough of this repository's use

From `Makefile`:

```make
	checkov -d infra --framework terraform --quiet --compact
```

- `-d infra`: scan this directory.
- `--framework terraform`: only the Terraform checks (not Kubernetes, Dockerfile and so on).
- `--quiet`: show only failed checks (no list of passes).
- `--compact`: leave the code snippets out of the report.

The output ends with a summary: `Passed checks: 113, Failed checks: 0, Skipped checks: 24`. The command exits non-zero if any check fails, so `make lint` stops.

From `infra/modules/log-archive/main.tf`:

```hcl
  #checkov:skip=CKV_AWS_18:Access to the archive is itself recorded by the security account's own trail in a real organization; this build keeps one trail.
  #checkov:skip=CKV_AWS_144:Cross-region replication of the archive is a production decision, see ARCHITECTURE.md.
  #checkov:skip=CKV2_AWS_62:Nothing reacts to log delivery here; detection runs from the rules in the workload account and the batch scan.
```

The syntax is `checkov:skip=<check id>:<reason>`, written as a comment *inside* the resource block (here `resource "aws_s3_bucket" "archive"`). Each line is one exception. The reasons say why the check does not apply in this lesson. When Checkov runs it reports these as `SKIPPED` with `Suppress comment:` showing the text, so a reviewer sees every exception.

The other skips follow the same pattern: the trail skips alerting and streaming to CloudWatch Logs (the rules in the alerting modules do the alerting), the posture module skips four checks on its delivery bucket, and the drill module skips fifteen checks because it is a *deliberate, temporary weakness* (a long-lived key, a bucket without Block Public Access) that exists only while the exercise runs. Nothing is skipped without a reason.

## Try it yourself

```bash
checkov --version
```

Expect `3.3.30`.

```bash
checkov -d infra --framework terraform --quiet --compact
```

Expect `Passed checks: 113, Failed checks: 0, Skipped checks: 24`.

```bash
sed -i '' '/CKV_AWS_18:Access to the archive/d' infra/modules/log-archive/main.tf
checkov -d infra --framework terraform --quiet --compact | grep -E "^Check|FAILED|Passed"
git checkout infra
```

(On Linux write `sed -i` without the empty quotes.) Expect `Passed checks: 113, Failed checks: 1, Skipped checks: 23` and `Check: CKV_AWS_18: "Ensure the S3 bucket has access logging enabled"` with `FAILED for resource: module.log_archive.aws_s3_bucket.archive`. The last line restores the file.

```bash
checkov -d infra --framework terraform --compact -o cli | grep -A2 "SKIPPED" | sed -n 1,3p
```

Expect a `SKIPPED for resource` line and the `Suppress comment:` with the reason.

## Mistakes people make

- Skipping a check without a reason, or in a global config file where nobody sees it. Here each skip is beside the code.
- Treating a pass as proof of security. Checkov checks known patterns; it does not know your threat model.
- Skipping a check because it is inconvenient. A skip should say why the check does not apply.
- Putting the skip comment outside the resource block, where it has no effect.

## Check yourself

1. What does Checkov scan? *The Terraform files, against a library of security checks.*
2. What is `CKV_AWS_18`? *The id of one check: S3 access logging.*
3. How do you suppress one check for one resource? *A comment `checkov:skip=<id>:<reason>` inside the resource block.*
4. Does Checkov contact AWS? *No.*
5. What does `Failed checks: 0` mean for `make lint`? *The scan passes and `make lint` continues.*

## Further reading

- Checkov documentation (3.x): <https://www.checkov.io/>
- Suppressing and skipping checks: <https://www.checkov.io/2.Basics/Suppressing%20and%20Skipping%20Policies.html>
- Terraform policy index: <https://www.checkov.io/5.Policy%20Index/terraform.html>

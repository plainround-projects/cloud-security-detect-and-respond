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
- `--framework terraform`: only the Terraform checks (not the checks for Kubernetes manifests, Dockerfiles, CloudFormation templates or the other file types Checkov can scan).
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

### Every skip, one by one

Checkov has no settings file in this repository. Its behavior is set by the flags on the `Makefile` line (explained above) and by **skip comments** written next to the code they excuse. A check has an id: `CKV_AWS_<number>` is a check written in Python for one resource type, `CKV2_AWS_<number>` is a **graph** check that follows references between several resources (for example "this bucket has a public access block resource pointing at it"). A skip comment has the form `#checkov:skip=<id>:<reason>` and sits **inside** the resource block it excuses; Checkov then reports the check as skipped and prints the reason. Titles below are the check titles from Checkov 3.3.30, printed by `checkov --list`. Every skip in this repository:

From `infra/modules/central-trail/main.tf` (line 4):

```hcl
  #checkov:skip=CKV_AWS_252:Alerts come from the EventBridge rules in the alerting modules, which see the same events sooner.
```

In `resource "aws_cloudtrail" "central"`. **CKV_AWS_252**: "Ensure CloudTrail defines an SNS Topic". Why it is skipped: Alerts come from the EventBridge rules in the alerting modules, which see the same events sooner.

From `infra/modules/central-trail/main.tf` (line 5):

```hcl
  #checkov:skip=CKV2_AWS_10:The archive in the security account is the record; streaming to CloudWatch Logs is not part of this lesson.
```

In `resource "aws_cloudtrail" "central"`. **CKV2_AWS_10**: "Ensure CloudTrail trails are integrated with CloudWatch Logs". Why it is skipped: The archive in the security account is the record; streaming to CloudWatch Logs is not part of this lesson.

From `infra/modules/drill/main.tf` (line 9):

```hcl
  #checkov:skip=CKV_AWS_273:The drill needs a long-lived user key: that is the leaked credential the exercise detects.
```

In `resource "aws_iam_user" "drill"`. **CKV_AWS_273**: "Ensure access is controlled through SSO and not AWS IAM defined users". Why it is skipped: The drill needs a long-lived user key: that is the leaked credential the exercise detects.

From `infra/modules/drill/main.tf` (line 16):

```hcl
  #checkov:skip=CKV_AWS_40:The drill user is a deliberate exception; it exists only while the drill runs.
```

In `resource "aws_iam_user_policy" "assume_broad_role"`. **CKV_AWS_40**: "Ensure IAM policies are attached only to groups or roles (Reducing access management complexity may in-turn reduce opportunity for a principal to inadvertently receive or retain excessive privileges.)". Why it is skipped: The drill user is a deliberate exception; it exists only while the drill runs.

From `infra/modules/drill/main.tf` (line 73):

```hcl
  #checkov:skip=CKV_AWS_18:Throwaway drill bucket.
```

In `resource "aws_s3_bucket" "data"`. **CKV_AWS_18**: "Ensure the S3 bucket has access logging enabled". Why it is skipped: Throwaway drill bucket.

From `infra/modules/drill/main.tf` (line 74):

```hcl
  #checkov:skip=CKV_AWS_21:Throwaway drill bucket; versioning adds nothing to the drill.
```

In `resource "aws_s3_bucket" "data"`. **CKV_AWS_21**: "Ensure all data stored in the S3 bucket have versioning enabled". Why it is skipped: Throwaway drill bucket; versioning adds nothing to the drill.

From `infra/modules/drill/main.tf` (line 75):

```hcl
  #checkov:skip=CKV_AWS_144:Throwaway drill bucket.
```

In `resource "aws_s3_bucket" "data"`. **CKV_AWS_144**: "Ensure that S3 bucket has cross-region replication enabled". Why it is skipped: Throwaway drill bucket.

From `infra/modules/drill/main.tf` (line 76):

```hcl
  #checkov:skip=CKV_AWS_145:Throwaway drill bucket holding no data.
```

In `resource "aws_s3_bucket" "data"`. **CKV_AWS_145**: "Ensure that S3 buckets are encrypted with KMS by default". Why it is skipped: Throwaway drill bucket holding no data.

From `infra/modules/drill/main.tf` (line 77):

```hcl
  #checkov:skip=CKV2_AWS_6:Block Public Access is off on purpose: the drill makes this bucket public.
```

In `resource "aws_s3_bucket" "data"`. **CKV2_AWS_6**: "Ensure that S3 bucket has a Public Access block". Why it is skipped: Block Public Access is off on purpose: the drill makes this bucket public.

From `infra/modules/drill/main.tf` (line 78):

```hcl
  #checkov:skip=CKV2_AWS_61:Throwaway drill bucket.
```

In `resource "aws_s3_bucket" "data"`. **CKV2_AWS_61**: "Ensure that an S3 bucket has a lifecycle configuration". Why it is skipped: Throwaway drill bucket.

From `infra/modules/drill/main.tf` (line 79):

```hcl
  #checkov:skip=CKV2_AWS_62:Throwaway drill bucket.
```

In `resource "aws_s3_bucket" "data"`. **CKV2_AWS_62**: "Ensure S3 buckets should have event notifications enabled". Why it is skipped: Throwaway drill bucket.

From `infra/modules/drill/main.tf` (line 86):

```hcl
  #checkov:skip=CKV2_AWS_65:ACLs stay enabled on purpose: the drill makes the bucket public with an ACL.
```

In `resource "aws_s3_bucket_ownership_controls" "data"`. **CKV2_AWS_65**: "Ensure access control lists for S3 buckets are disabled". Why it is skipped: ACLs stay enabled on purpose: the drill makes the bucket public with an ACL.

From `infra/modules/drill/main.tf` (line 95):

```hcl
  #checkov:skip=CKV_AWS_53:Deliberate drill weakness.
```

In `resource "aws_s3_bucket_public_access_block" "data"`. **CKV_AWS_53**: "Ensure S3 bucket has block public ACLS enabled". Why it is skipped: Deliberate drill weakness.

From `infra/modules/drill/main.tf` (line 96):

```hcl
  #checkov:skip=CKV_AWS_54:Deliberate drill weakness.
```

In `resource "aws_s3_bucket_public_access_block" "data"`. **CKV_AWS_54**: "Ensure S3 bucket has block public policy enabled". Why it is skipped: Deliberate drill weakness.

From `infra/modules/drill/main.tf` (line 97):

```hcl
  #checkov:skip=CKV_AWS_55:Deliberate drill weakness.
```

In `resource "aws_s3_bucket_public_access_block" "data"`. **CKV_AWS_55**: "Ensure S3 bucket has ignore public ACLs enabled". Why it is skipped: Deliberate drill weakness.

From `infra/modules/drill/main.tf` (line 98):

```hcl
  #checkov:skip=CKV_AWS_56:Deliberate drill weakness.
```

In `resource "aws_s3_bucket_public_access_block" "data"`. **CKV_AWS_56**: "Ensure S3 bucket has 'restrict_public_buckets' enabled". Why it is skipped: Deliberate drill weakness.

From `infra/modules/drill/main.tf` (line 109):

```hcl
  #checkov:skip=CKV_AWS_273:A honeytoken is a user nobody should ever sign in as; its key is bait.
```

In `resource "aws_iam_user" "honeytoken"`. **CKV_AWS_273**: "Ensure access is controlled through SSO and not AWS IAM defined users". Why it is skipped: A honeytoken is a user nobody should ever sign in as; its key is bait.

From `infra/modules/log-archive/main.tf` (line 9):

```hcl
  #checkov:skip=CKV_AWS_18:Access to the archive is itself recorded by the security account's own trail in a real organization; this build keeps one trail.
```

In `resource "aws_s3_bucket" "archive"`. **CKV_AWS_18**: "Ensure the S3 bucket has access logging enabled". Why it is skipped: Access to the archive is itself recorded by the security account's own trail in a real organization; this build keeps one trail.

From `infra/modules/log-archive/main.tf` (line 10):

```hcl
  #checkov:skip=CKV_AWS_144:Cross-region replication of the archive is a production decision, see ARCHITECTURE.md.
```

In `resource "aws_s3_bucket" "archive"`. **CKV_AWS_144**: "Ensure that S3 bucket has cross-region replication enabled". Why it is skipped: Cross-region replication of the archive is a production decision, see ARCHITECTURE.md.

From `infra/modules/log-archive/main.tf` (line 11):

```hcl
  #checkov:skip=CKV2_AWS_62:Nothing reacts to log delivery here; detection runs from the rules in the workload account and the batch scan.
```

In `resource "aws_s3_bucket" "archive"`. **CKV2_AWS_62**: "Ensure S3 buckets should have event notifications enabled". Why it is skipped: Nothing reacts to log delivery here; detection runs from the rules in the workload account and the batch scan.

From `infra/modules/posture/main.tf` (line 7):

```hcl
  #checkov:skip=CKV_AWS_18:The recorder's own delivery bucket; CloudTrail data events are not enabled for it.
```

In `resource "aws_s3_bucket" "config"`. **CKV_AWS_18**: "Ensure the S3 bucket has access logging enabled". Why it is skipped: The recorder's own delivery bucket; CloudTrail data events are not enabled for it.

From `infra/modules/posture/main.tf` (line 8):

```hcl
  #checkov:skip=CKV_AWS_144:Single-region sandbox.
```

In `resource "aws_s3_bucket" "config"`. **CKV_AWS_144**: "Ensure that S3 bucket has cross-region replication enabled". Why it is skipped: Single-region sandbox.

From `infra/modules/posture/main.tf` (line 9):

```hcl
  #checkov:skip=CKV_AWS_145:AWS Config delivers with the recorder's role; a customer-managed key needs further grants outside this lesson.
```

In `resource "aws_s3_bucket" "config"`. **CKV_AWS_145**: "Ensure that S3 buckets are encrypted with KMS by default". Why it is skipped: AWS Config delivers with the recorder's role; a customer-managed key needs further grants outside this lesson.

From `infra/modules/posture/main.tf` (line 10):

```hcl
  #checkov:skip=CKV2_AWS_62:Nothing reacts to configuration snapshots here.
```

In `resource "aws_s3_bucket" "config"`. **CKV2_AWS_62**: "Ensure S3 buckets should have event notifications enabled". Why it is skipped: Nothing reacts to configuration snapshots here.

That is 24 skips in this repository, and no other check is switched off anywhere. Each one above says why the check does not apply to this exercise, and a reader can see it in the Checkov output as `SKIPPED ... Suppress comment: <reason>`.

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

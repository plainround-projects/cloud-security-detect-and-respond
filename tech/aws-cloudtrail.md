# AWS CloudTrail

## What it is

CloudTrail records **who did what in your AWS account**. Each API call (create a user, make a bucket public, a refused attempt) becomes an **event**: a JSON record with the time, the caller, the action, the parameters, the source address and, if the call failed, an `errorCode`. A **trail** delivers those events as compressed files to an S3 bucket. This is the "audit log" of the lesson, and the evidence from which the timeline is rebuilt.

## Why this repository uses it

The whole lesson stands on the audit log. Detections read it (through EventBridge, [aws-eventbridge.md](aws-eventbridge.md)), the timeline is rebuilt from it, and both measured times come from its timestamps. Because an intruder with administrator rights could switch off or erase a log kept in the same account, the trail here delivers to a bucket in **another account** ([aws-s3.md](aws-s3.md)) and writes **digest files** that make tampering detectable.

## Where it appears

| Path | What it does |
| --- | --- |
| `infra/modules/central-trail/main.tf` | the trail in the workload account, writing to the security account's bucket |
| `infra/modules/log-archive/main.tf` | the bucket policy that admits only this trail |
| `fixtures/drill/AWSLogs/` | a synthetic archive in the real layout: log files and digest files |
| `src/detect_respond/domain/events.py` | parses an event |
| `src/detect_respond/infrastructure/log_archive.py` | reads the archive from a folder, including the digest files |
| `src/detect_respond/domain/digest.py` | checks each log file against its digest |
| `scripts/03-verify-archive.sh`, `scripts/09-collect-and-measure.sh` | check that the archive fills, and copy it out and verify it |
| `policy/detection.rego` | rules: multi-region, log file validation, a bucket outside this account, an encryption key |

## How it works underneath

AWS services write events to CloudTrail as they handle calls. **Management events** are control-plane calls (IAM, creating resources). **Data events** are high-volume object-level calls such as S3 `GetObject`; they are off unless you ask. Events reach the S3 bucket as compressed JSON files (`.json.gz`), roughly **5 to 15 minutes** after the call. **Log file validation** also writes a **digest file** about once an hour: a signed list of the SHA-256 fingerprints of that hour's log files. If a log file is changed or removed, its fingerprint no longer matches, or the file is missing from the list. The CLI command `aws cloudtrail validate-logs` checks the digest's signature with the provider's public key, which Python alone cannot do.

## Walkthrough of this repository's use

From `infra/modules/central-trail/main.tf`:

```hcl
  s3_bucket_name                = var.log_bucket_name
  kms_key_id                    = var.log_key_arn
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true
  enable_logging                = true
```

- `s3_bucket_name` and `kms_key_id`: the bucket and key live in the *security* account. The OPA rule `the logs must go to a bucket outside this account` denies a trail that delivers to a bucket created in the same plan.
- `is_multi_region_trail`: one trail records every region; an attacker's call in an unused Region is still logged.
- `include_global_service_events`: also IAM and other global services.
- `enable_log_file_validation`: write the digest files.

From `infra/modules/central-trail/main.tf`:

```hcl
  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }
```

An **event selector** says what to record: every management event, reads and writes. Reads matter: an attacker "looking around" is made of read calls (`ListBuckets`).

From `src/detect_respond/infrastructure/log_archive.py`:

```python
        return [p for p in found if (DIGEST_FOLDER in p.parts) == digests]
```

The real bucket keeps log files under `CloudTrail/` and digests under `CloudTrail-Digest/`. `_files(digests=...)` returns one kind or the other: `DIGEST_FOLDER in p.parts` is true for a digest, and the comparison with `digests` picks the right group.

From `src/detect_respond/domain/digest.py`:

```python
    mismatched, missing = [], []
```

`verify_digest` walks the digest's list. For each listed file it asks the archive for the content, and files the name under `missing` (the archive does not have it) or `mismatched` (the SHA-256 differs). `intact` is true only if both lists are empty. The docstring is honest about the limit: it checks the fingerprints only, and `validate-logs` checks the signature.

From `scripts/03-verify-archive.sh`:

```bash
aws cloudtrail validate-logs --trail-arn "arn:aws:cloudtrail:${REGION}:${WORKLOAD_ACCOUNT_ID}:trail/central-trail" \
```

The provider's own validator, run against the real trail ([aws-cli.md](aws-cli.md)).

From `src/detect_respond/domain/events.py`:

```python
DENIAL_CODES = ("AccessDenied", "AccessDeniedException", "Client.UnauthorizedOperation", "UnauthorizedOperation")
```

The `errorCode` values that mean "not allowed". A detection fires on a *refused* attempt too: an attempt is as telling as a success. After containment, the first call refused with one of these codes marks the moment of containment.

## Try it yourself

```bash
.venv/bin/python -m detect_respond verify-archive --archive fixtures/drill; echo "exit $?"
```

Expect `digest 1: 3 files checked, 0 changed, 0 missing`, `every logged file matches its digest` and `exit 0`.

To see tampering, copy the archive, damage one log file, and verify the copy:

```bash
cp -R fixtures/drill /tmp/archive-copy
f=$(find /tmp/archive-copy -name '*us-east-1*drill.json.gz' | head -n 1)
python3 -c "import gzip,sys; p=sys.argv[1]; d=gzip.open(p).read().replace(b'Create', b'Delete', 1); open(p,'wb').write(gzip.compress(d))" "$f"
.venv/bin/python -m detect_respond verify-archive --archive /tmp/archive-copy; echo "exit $?"
rm -rf /tmp/archive-copy
```

Expect `digest 1: 3 files checked, 1 changed, 0 missing`, a line `CHANGED AWSLogs/.../us-east-1/...drill.json.gz`, then `the archive does not match its digests` and `exit 1`.

```bash
python3 -c "
import json
p = json.load(open('build/workload.json'))
t = [x['change']['after'] for x in p['resource_changes'] if x['type'] == 'aws_cloudtrail'][0]
print(t['name'], t['is_multi_region_trail'], t['enable_log_file_validation'], t['s3_bucket_name'])"
```

After `make plan`, expect `central-trail True True detect-archive-000000000001`.

## Mistakes people make

- Looking for an entry too soon. Wait 5 to 15 minutes.
- Keeping the log in the same account as the workload. An administrator there can stop or erase it.
- Trusting the fingerprints alone. Run `validate-logs` too, which checks the signature.
- Recording write events only. The first sign of an intruder is often a read call.
- Turning logging off to save money: then nothing proves what happened.

## Check yourself

1. What does a trail do? *Delivers recorded API events as files to a bucket.*
2. Why does the trail deliver to another account? *So an intruder with administrator rights in the workload account cannot erase the log.*
3. What does log file validation add? *Digest files with signed fingerprints so tampering can be detected.*
4. What does `verify-archive` check, and what does it not? *Fingerprints of the files against the digest; not the digest's signature, which `validate-logs` checks.*
5. How long can delivery take? *About 5 to 15 minutes.*

## Further reading

- CloudTrail user guide: <https://docs.aws.amazon.com/awscloudtrail/latest/userguide/>
- Log file integrity validation: <https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-intro.html>
- Terraform `aws_cloudtrail` (provider 6.x): <https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudtrail>

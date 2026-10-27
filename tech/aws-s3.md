# Amazon S3 (Simple Storage Service), Object Lock and the log archive

## What it is

S3 stores **objects** (files with a name, called a **key**) in **buckets** (named containers). Bucket names are unique across all of AWS. S3 has no folders; a key such as `AWSLogs/0000/CloudTrail/a.json.gz` is one long name. Access is governed by IAM policies, a **bucket policy** (a resource-based policy) and a few bucket-level switches. **Versioning** keeps every version of an object. **Object Lock** is a write-once-read-many feature: a locked object version cannot be deleted or overwritten until its retention period ends.

## Why this repository uses it

The lesson's central rule for logs is that an intruder who gets administrator rights in the workload account must not be able to erase their tracks. The audit log therefore goes to a bucket in a *different* account, the security account, and that bucket is locked so that even the security account's owner cannot delete a log file during the retention period. Without a tamper-resistant archive, the timeline you rebuild after an incident is only as trustworthy as the attacker allows.

## Where it appears

| Path | What it does |
| --- | --- |
| `infra/modules/log-archive/main.tf` | the archive bucket with Object Lock, versioning, encryption, expiry and the policy that denies deletes |
| `infra/modules/posture/main.tf` | the bucket that AWS Config delivers snapshots to |
| `infra/modules/drill/main.tf` | the drill's data bucket, public-capable on purpose |
| `policy/detection.rego` | rules: lock in compliance mode, delete denied, versioned, Block Public Access on, KMS-encrypted |
| `scripts/03-verify-archive.sh` | tries to delete a log file as an administrator of each account |
| `scripts/09-collect-and-measure.sh` | `aws s3 sync` of the archive to a local folder |

## How it works underneath

Object Lock works on object **versions** and needs versioning. It has two modes. In **governance** mode, users with a special permission can still remove locks. In **compliance** mode, nobody can: not an administrator, and not the account owner; the retention period cannot be shortened, and the bucket cannot be emptied or deleted until every version has expired. A **default retention** applies automatically to every new object. Because compliance mode is irreversible, the exercise uses a retention of one day, and a **lifecycle rule** expires the files and old versions after two days so the bucket can be removed later. **Block Public Access** is four switches that override any policy or ACL that would make a bucket public.

## Walkthrough of this repository's use

From `infra/modules/log-archive/main.tf`:

```hcl
  bucket              = var.bucket_name
  object_lock_enabled = true
```

Object Lock is switched on when the bucket is created, so the argument is part of the bucket itself.

From `infra/modules/log-archive/main.tf`:

```hcl
    default_retention {
      mode = "COMPLIANCE"
      days = var.retention_days
    }
```

Every log file written is locked in compliance mode for `retention_days` days (1 in the exercise). The OPA rule `Object Lock must be in compliance mode with a retention of at least one day` checks both values. The comment above it says the value cannot be shortened by anyone, which is the point.

From `infra/modules/log-archive/main.tf`:

```hcl
        Sid       = "NobodyDeletesOrRewritesLogFiles"
        Effect    = "Deny"
        Principal = { AWS = "*" }
        Action    = ["s3:DeleteObject", "s3:DeleteObjectVersion", "s3:PutObjectRetention", "s3:BypassGovernanceRetention"]
        Resource  = "arn:aws:s3:::${var.bucket_name}/*"
```

A second lock, in the policy. An explicit Deny for every principal on deleting objects and versions and on changing the retention. A Deny in IAM beats every Allow ([aws-iam.md](aws-iam.md)). So even if the object lock were misconfigured, the policy refuses; and if the policy were changed, the lock refuses. `scripts/03-verify-archive.sh` proves it by trying.

From `infra/modules/log-archive/main.tf`:

```hcl
        Sid       = "TrailWritesLogFilesOfTheWorkloadAccount"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "arn:aws:s3:::${var.bucket_name}/AWSLogs/${var.workload_account_id}/*"
```

The only Allow that writes: the CloudTrail service, only into the workload account's folder, and (in the condition below it) only for the one trail and only with `bucket-owner-full-control`. The OPA rule `allows something other than the one trail, pinned by aws:SourceArn` denies any other Allow on the archive.

From `infra/modules/log-archive/main.tf`:

```hcl
    expiration {
      days = var.expire_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.expire_days
    }
```

Files leave the archive only by expiring after the retention has ended. Nobody deletes them by hand. `expire_days` (2) must be longer than `retention_days` (1), or the lifecycle rule would try to remove a locked file.

From `infra/modules/drill/main.tf`:

```hcl
  block_public_acls       = false
  ignore_public_acls      = false
  block_public_policy     = false
  restrict_public_buckets = false
```

The drill's data bucket turns all four switches **off** on purpose: the attacker makes it public (detection D2), and the exercise measures how fast that is noticed. It exists only while `enable_drill` is true, and the OPA rule `Block Public Access` is only relaxed for resources inside the drill module ([opa-rego.md](opa-rego.md)).

## Try it yourself

```bash
python3 -c "
import json
p = json.load(open('build/security.json'))
o = [x for x in p['resource_changes'] if x['type'] == 'aws_s3_bucket_object_lock_configuration'][0]['change']['after']
print(o['rule'][0]['default_retention'][0]['mode'], o['rule'][0]['default_retention'][0]['days'])"
```

After `make plan`, expect `COMPLIANCE 1`.

```bash
opa test policy -v | grep -c "archive"
```

Expect `8`: the tests that allow the secured archive and deny each way of weakening it (no lock, not compliance mode, deletes allowed, no versioning, no Block Public Access, default encryption, a policy that lets the account root write).

```bash
opa eval -d policy -i build/security.json 'data.detection.deny' --format pretty
```

Expect `[]`: the archive breaks no rule.

## Mistakes people make

- Choosing a long retention in compliance mode while experimenting. It cannot be shortened by anyone; the bucket and its data stay and bill until it ends.
- Forgetting versioning. Object Lock needs it.
- Relying on the lock alone. The policy deny is a second, independent barrier.
- Putting the archive bucket in the workload account. Then its administrator controls the bucket's account.
- Setting the expiry shorter than the retention.

## Check yourself

1. What does Object Lock in compliance mode guarantee? *A locked version cannot be deleted or overwritten by anyone until its retention ends.*
2. Why is the archive in a different account? *An administrator of the workload account has no rights there.*
3. Why two barriers (lock and policy deny)? *Each protects if the other were misconfigured.*
4. How do files finally leave the archive? *By lifecycle expiry after the retention has ended.*
5. Why does the drill bucket turn Block Public Access off? *The attack makes it public; it is a deliberate, temporary weakness.*

## Further reading

- S3 user guide: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/>
- Object Lock: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html>
- Terraform `aws_s3_bucket_object_lock_configuration` (provider 6.x): <https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_object_lock_configuration>

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

### Every argument of every AWS resource in this repository

A Terraform `resource` block describes one thing to create. Inside it, each line `name = value` is an **argument** and each `name { ... }` is a **nested block** (a group of arguments for one part of the resource). The column "Kind" says whether the AWS provider requires the argument, whether it is optional, whether it opens a nested block, or whether it is a Terraform **meta-argument** that works on every resource. In "Kind", `required` and `optional` were read from the provider's own schema (version 6.70.0, the one in the lock file), so they are not guesses. A path such as `rule.expiration.days` means the argument `days` inside the nested block `expiration` inside the nested block `rule`. Names that contain `var.` or `local.` or `module.` are values that come from elsewhere in the code ([terraform.md](terraform.md)).

#### `aws_s3_bucket`

Declared in `infra/modules/drill/main.tf` lines 72 to 83 (`data`); `infra/modules/log-archive/main.tf` lines 8 to 14 (`archive`); `infra/modules/posture/main.tf` lines 6 to 13 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `bucket` | optional | The name of the bucket. It is unique across all of AWS, which is why the account id appears in it. | `"${var.bucket_prefix}-${var.account_id}"` / `var.bucket_name` / `local.config_bucket` |
| `force_destroy` | optional | `true` lets `terraform destroy` delete the bucket even if it holds objects. Used only for throw-away data. | `true` / `var.force_destroy` |
| `object_lock_enabled` | optional | Switch on Object Lock for this bucket. Object Lock stores objects so that they cannot be deleted or overwritten for a set time, and it needs versioning ([aws-s3.md](aws-s3.md)). | `true` |
| `tags` | optional | Labels, see above. | `{ purpose = "incident-drill" }` |

#### `aws_s3_bucket_lifecycle_configuration`

Declared in `infra/modules/log-archive/main.tf` lines 68 to 91 (`archive`); `infra/modules/posture/main.tf` lines 49 to 72 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `bucket` | required | The name of the bucket the setting applies to. This resource configures one bucket; the name ties it to that bucket (the bucket itself is a separate `aws_s3_bucket` resource, [aws-s3.md](aws-s3.md)). | `aws_s3_bucket.archive.bucket` / `aws_s3_bucket.config.bucket` |
| `rule.abort_incomplete_multipart_upload.days_after_initiation` | optional | Throw away the pieces of an upload that never finished after this many days; unfinished pieces are billed otherwise. | `7` |
| `rule.expiration.days` | optional | Delete the current version of an object this many days after it was created. | `var.expire_days` / `var.retention_days` |
| `rule.id` | required | A name for the rule. | `"expire-after-retention"` / `"expire-snapshots"` |
| `rule.noncurrent_version_expiration.noncurrent_days` | required | Delete an old version this many days after it stopped being the current one. | `var.expire_days` / `7` |
| `rule.status` | required | `Enabled` or `Disabled`. | `"Enabled"` |
| `depends_on` | meta-argument | A Terraform **meta-argument** (it works on every resource and is not sent to AWS): create this resource only after the listed ones. Terraform normally works out the order from references; `depends_on` states an order that no reference shows, for example a policy that must exist before a service first writes. | `[aws_s3_bucket_versioning.archive]` / `[aws_s3_bucket_versioning.config]` |

#### `aws_s3_bucket_object_lock_configuration`

Declared in `infra/modules/log-archive/main.tf` lines 54 to 65 (`archive`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `bucket` | required | The name of the bucket the setting applies to. This resource configures one bucket; the name ties it to that bucket (the bucket itself is a separate `aws_s3_bucket` resource, [aws-s3.md](aws-s3.md)). | `aws_s3_bucket.archive.bucket` |
| `rule.default_retention.days` | optional | The number of days each new object is locked. | `var.retention_days` |
| `rule.default_retention.mode` | optional | `COMPLIANCE`: nobody, including the account owner, can delete or shorten the lock on an object until the period ends. `GOVERNANCE` could be bypassed with a special permission. | `"COMPLIANCE"` |
| `depends_on` | meta-argument | A Terraform **meta-argument** (it works on every resource and is not sent to AWS): create this resource only after the listed ones. Terraform normally works out the order from references; `depends_on` states an order that no reference shows, for example a policy that must exist before a service first writes. | `[aws_s3_bucket_versioning.archive]` |

#### `aws_s3_bucket_ownership_controls`

Declared in `infra/modules/drill/main.tf` lines 85 to 92 (`data`); `infra/modules/log-archive/main.tf` lines 16 to 22 (`archive`); `infra/modules/posture/main.tf` lines 23 to 29 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `bucket` | required | The name of the bucket the setting applies to. This resource configures one bucket; the name ties it to that bucket (the bucket itself is a separate `aws_s3_bucket` resource, [aws-s3.md](aws-s3.md)). | `aws_s3_bucket.data.bucket` / `aws_s3_bucket.archive.bucket` / `aws_s3_bucket.config.bucket` |
| `rule.object_ownership` | required | `BucketOwnerEnforced` switches off ACLs: the bucket owner owns every object and only policies grant access. | `"BucketOwnerPreferred"` / `"BucketOwnerEnforced"` |

#### `aws_s3_bucket_policy`

Declared in `infra/modules/log-archive/main.tf` lines 93 to 136 (`archive`); `infra/modules/posture/main.tf` lines 74 to 92 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `bucket` | required | The name of the bucket the setting applies to. This resource configures one bucket; the name ties it to that bucket (the bucket itself is a separate `aws_s3_bucket` resource, [aws-s3.md](aws-s3.md)). | `aws_s3_bucket.archive.bucket` / `aws_s3_bucket.config.bucket` |
| `policy` | required | The bucket policy: a resource policy that says who may do what to the bucket and its objects ([aws-s3.md](aws-s3.md)). | `jsonencode({ Version = "2012-10-17" Statement = [ { Sid = "TrailChe...` / `jsonencode({ Version = "2012-10-17" Statement = [ { Sid = "DenyPlai...` |
| `depends_on` | meta-argument | A Terraform **meta-argument** (it works on every resource and is not sent to AWS): create this resource only after the listed ones. Terraform normally works out the order from references; `depends_on` states an order that no reference shows, for example a policy that must exist before a service first writes. | `[aws_s3_bucket_public_access_block.archive]` / `[aws_s3_bucket_public_access_block.config]` |

#### `aws_s3_bucket_public_access_block`

Declared in `infra/modules/drill/main.tf` lines 94 to 104 (`data`); `infra/modules/log-archive/main.tf` lines 24 to 30 (`archive`); `infra/modules/posture/main.tf` lines 15 to 21 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `block_public_acls` | optional | Refuse any request that tries to set a public ACL. | `false` / `true` |
| `block_public_policy` | optional | Refuse a bucket policy that would make the bucket public. | `false` / `true` |
| `bucket` | required | The name of the bucket the setting applies to. This resource configures one bucket; the name ties it to that bucket (the bucket itself is a separate `aws_s3_bucket` resource, [aws-s3.md](aws-s3.md)). | `aws_s3_bucket.data.bucket` / `aws_s3_bucket.archive.bucket` / `aws_s3_bucket.config.bucket` |
| `ignore_public_acls` | optional | Ignore any public ACL that already exists. | `false` / `true` |
| `restrict_public_buckets` | optional | If a public policy exists anyway, allow only the owner account's identities and AWS services. | `false` / `true` |

#### `aws_s3_bucket_server_side_encryption_configuration`

Declared in `infra/modules/log-archive/main.tf` lines 40 to 51 (`archive`); `infra/modules/posture/main.tf` lines 39 to 47 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `bucket` | required | The name of the bucket the setting applies to. This resource configures one bucket; the name ties it to that bucket (the bucket itself is a separate `aws_s3_bucket` resource, [aws-s3.md](aws-s3.md)). | `aws_s3_bucket.archive.bucket` / `aws_s3_bucket.config.bucket` |
| `rule.apply_server_side_encryption_by_default.kms_master_key_id` | optional | Which KMS key encrypts new objects (a key id, ARN or alias). | `var.key_alias_arn` |
| `rule.apply_server_side_encryption_by_default.sse_algorithm` | required | How new objects are encrypted: `AES256` uses S3-managed keys, `aws:kms` uses a key from KMS. | `"aws:kms"` / `"AES256"` |
| `rule.bucket_key_enabled` | optional | Use a short-lived key for the bucket, so S3 asks KMS less often (lower cost, fewer log lines). | `true` |

#### `aws_s3_bucket_versioning`

Declared in `infra/modules/log-archive/main.tf` lines 32 to 38 (`archive`); `infra/modules/posture/main.tf` lines 31 to 37 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `bucket` | required | The name of the bucket the setting applies to. This resource configures one bucket; the name ties it to that bucket (the bucket itself is a separate `aws_s3_bucket` resource, [aws-s3.md](aws-s3.md)). | `aws_s3_bucket.archive.bucket` / `aws_s3_bucket.config.bucket` |
| `versioning_configuration.status` | required | `Enabled` keeps every version of an object; an overwrite or delete adds a new version instead of destroying the old one. | `"Enabled"` |

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

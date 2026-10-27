# AWS KMS (Key Management Service)

## What it is

KMS creates and guards **encryption keys**. A key never leaves the service in readable form: you ask KMS to encrypt or decrypt for you, and KMS first checks whether you are allowed. A **customer-managed key** is one you create and whose rules you write; the rules are a **key policy**. An **alias** (`alias/detect-archive`) is a friendly name that points to a key.

## Why this repository uses it

Two things in this repository are encrypted with their own keys. The central log archive lives in the **security account** and is encrypted with a key whose policy lets the *workload account's trail* write and lets the *security account* read through the storage service. That makes the key part of the tamper-resistance: an administrator of the workload account has no right to use the key at all. The three alert topics each have a key, so alert text, which names callers and resources, is encrypted too.

## Where it appears

| Path | What it does |
| --- | --- |
| `infra/modules/kms-key/main.tf` | the key, its rotation, its alias and the administration statement every key shares |
| `infra/modules/log-archive/main.tf` | the archive bucket uses the key by its alias |
| `infra/environments/security/main.tf` | the archive key and its three extra statements |
| `infra/modules/alerting/main.tf` | one key per Region for the alert topic |
| `policy/detection.rego` | rules: key rotation on; the archive and the trail must use a key |

## How it works underneath

KMS uses **envelope encryption**. To store an object, S3 asks KMS for a fresh *data key*, encrypts the object with it, and stores the data key only in encrypted form next to the object. To read the object, S3 asks KMS to decrypt that data key. So each read or write of an encrypted object involves a KMS permission check for the caller. A key policy is a resource-based policy and is **required**: if the key policy does not allow a principal (directly, or by delegating to the account's IAM policies), no IAM policy can grant access. A principal in **another account** needs both: the key policy must name it (or its account), and the principal's own account must allow the call too. Services such as CloudTrail are principals too, and need a statement of their own.

## Walkthrough of this repository's use

From `infra/modules/kms-key/main.tf`:

```hcl
resource "aws_kms_key" "this" {
  description             = var.description
  enable_key_rotation     = true
  deletion_window_in_days = var.deletion_window_in_days
```

`enable_key_rotation = true` rotates the key material every year at no extra effort. `deletion_window_in_days` is the waiting period between "schedule deletion" and the key's disappearance (7 to 30 days): deleting a key makes everything it encrypted unreadable, so AWS never deletes at once.

From `infra/modules/kms-key/main.tf`:

```hcl
  # Management only. The account root is deliberately not given kms:Decrypt or kms:Encrypt, so an IAM policy cannot
  # reach the data; only the principals in `statements` can use the key.
```

The administration statement lists management actions (`kms:Create*`, `kms:Describe*`, `kms:ScheduleKeyDeletion`, ...) but not the data actions. An administrator can still change the key policy itself (`kms:Put*` covers `PutKeyPolicy`), but that is a loud, recorded change ([aws-cloudtrail.md](aws-cloudtrail.md)), not a quiet one.

From `infra/environments/security/main.tf`:

```hcl
      Sid       = "WorkloadTrailEncryptsLogFiles"
      Effect    = "Allow"
      Principal = { Service = "cloudtrail.amazonaws.com" }
      Action    = "kms:GenerateDataKey*"
```

The trail runs in the *workload* account, but the key is in the *security* account. The statement names the CloudTrail **service** as principal and ties it down with conditions: `aws:SourceArn` pins the one trail (by account, Region and name), and an encryption-context condition limits it to trails of the workload account. `GenerateDataKey*` ends in a star, which matches `GenerateDataKey` and `GenerateDataKeyWithoutPlaintext`.

From `infra/environments/security/main.tf`:

```hcl
      Principal = { AWS = "arn:aws:iam::${var.security_account_id}:root" }
      Action    = "kms:Decrypt"
      Resource  = "*"
      Condition = { StringEquals = { "kms:ViaService" = "s3.${var.region}.amazonaws.com" } }
```

The security account may decrypt, but only **through the storage service**: the condition `kms:ViaService` is true only when S3 makes the call on the principal's behalf. The principal is the account root, which means "this account's own IAM policies decide who", so a person in the security account can read log files through S3 but cannot call KMS directly to decrypt arbitrary data.

From `infra/modules/log-archive/main.tf`:

```hcl
      kms_master_key_id = var.key_alias_arn
```

The archive encrypts every object with this key, named by alias ([aws-s3.md](aws-s3.md)). The OPA rule `the archive must be encrypted with a customer-managed key` checks it.

## Try it yourself

```bash
python3 -c "
import json
for e in ('security', 'workload'):
    p = json.load(open(f'build/{e}.json'))
    print(e, sorted(x['change']['after']['name'] for x in p['resource_changes'] if x['type'] == 'aws_kms_alias'))"
```

After `make plan`, expect `security ['alias/detect-archive']` and `workload ['alias/detect-global-alerts', 'alias/detect-home-alerts', 'alias/detect-watch-alerts']`.

```bash
python3 -c "
import json
p = json.load(open('build/security.json'))
k = [x for x in p['resource_changes'] if x['type'] == 'aws_kms_key'][0]['change']['after']
print([s['Sid'] for s in json.loads(k['policy'])['Statement']])"
```

Expect the four statements: `AccountAdministersKey`, `WorkloadTrailEncryptsLogFiles`, `WorkloadTrailDescribesTheKey`, `SecurityAccountReadsLogsThroughTheStorageService`. The policy is JSON text inside the plan, so it is parsed twice ([json.md](json.md)).

```bash
opa eval -d policy -i build/security.json 'data.detection.deny' --format pretty
```

Expect `[]`: the archive environment breaks none of the rules.

## Mistakes people make

- Believing an IAM policy can grant access to a key whose policy does not allow the caller. The key policy comes first.
- Giving the account root `kms:*` "to be safe". That hands every administrator the data.
- Forgetting the services. CloudTrail needs its own key-policy statement, with conditions, or it cannot write; a missing statement shows up as a trail that never delivers.
- Deleting a key to save money: its data is gone. The window exists for this reason.
- Putting the archive key in the workload account. Then an administrator of that account controls it.

## Check yourself

1. What does a key policy do? *It says who may use and manage the key; it is required.*
2. Why is the archive key in the security account? *So an administrator of the workload account has no rights over the evidence's encryption.*
3. What does `kms:ViaService` do? *Allows a call only when the named service makes it on the principal's behalf.*
4. Why does the CloudTrail statement have conditions? *To limit the service to the one trail and the workload account.*
5. What does `enable_key_rotation` do? *The key material is replaced every year automatically.*

## Further reading

- KMS developer guide: <https://docs.aws.amazon.com/kms/latest/developerguide/>
- Key policies: <https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html>
- Terraform `aws_kms_key` (provider 6.x): <https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key>

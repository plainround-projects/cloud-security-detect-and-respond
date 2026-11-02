# The Terraform AWS provider

## What it is

A Terraform **provider** is a plug-in that teaches Terraform how to manage one kind of system. The AWS provider (`hashicorp/aws`) knows every AWS resource type (`aws_s3_bucket`, `aws_iam_role`, ...) and how to create, read, change and delete it through AWS's APIs. This repository uses provider version **6.70.0**, locked in `.terraform.lock.hcl`, within the allowed range `~> 6.0`. A **provider alias** is a second, named configuration of the same provider, for example one that works in another Region.

## Why this repository uses it

All the cloud pieces of the lesson are AWS resources. The provider is also what makes two things possible. First, `terraform plan` works without an account, because the provider can be told to skip every call that needs credentials. Second, **one environment can work in several Regions**, which detection needs: an EventBridge rule sees only the events of its own Region, so the workload environment configures the provider three times.

## Where it appears

| Path | What it does |
| --- | --- |
| `infra/environments/*/versions.tf` | pins the provider range |
| `infra/environments/*/providers.tf` | configures the provider: region, offline switches, tags; three configurations in the workload environment |
| `infra/environments/*/.terraform.lock.hcl` | the exact version and file hashes |
| `infra/modules/*/versions.tf` | each module declares the same requirement |
| every `resource "aws_..."` block | a resource type the provider implements |

## How it works underneath

`terraform init` downloads the provider binary from the registry into `.terraform/` and checks it against the lock file. When you plan or apply, Terraform starts the provider as a separate process and talks to it. The provider turns each resource block into AWS API calls using credentials found in the usual places (environment variables, a profile). A **default tag** is a tag the provider adds to every resource that supports tags. An aliased provider is handed to a module explicitly; a module that is not given one uses the default configuration.

## Walkthrough of this repository's use

From `infra/environments/workload/providers.tf`:

```hcl
provider "aws" {
  region = var.region

  skip_credentials_validation = var.plan_only
  skip_metadata_api_check     = var.plan_only
  skip_requesting_account_id  = var.plan_only
  skip_region_validation      = var.plan_only
```

- `region`: where resources are created.
- `skip_credentials_validation`: do not check the credentials with a call to the security token service.
- `skip_metadata_api_check`: do not look for credentials from a cloud instance's metadata service.
- `skip_requesting_account_id`: do not ask AWS for the account id (the account id comes from a variable).
- `skip_region_validation`: do not check the region name against a list.

These four, driven by `var.plan_only`, are what makes a credential-free plan possible. Real runs leave `plan_only` false.

From `infra/environments/workload/providers.tf`:

```hcl
provider "aws" {
  alias  = "global"
  region = "us-east-1"
```

A second configuration of the provider with an **alias**. It works in `us-east-1`, where IAM events arrive. A third, `alias = "watch_ap_southeast_2"`, works in a Region the account never uses, so a call there can be detected. A resource or module chooses one with `provider = aws.global` or, for a module, `providers = { aws = aws.global }` ([terraform.md](terraform.md)). The three blocks repeat the same four skip settings, because each configuration is separate.

From `infra/environments/workload/providers.tf`:

```hcl
  default_tags {
    tags = {
      project = "detect-and-respond"
      account = "workload"
      managed = "terraform"
    }
  }
```

Every taggable resource gets `project`, `account` and `managed` automatically; the teardown script finds leftovers by the `project` tag. The security environment uses `account = "security"`.

The `Makefile` supplies placeholder credentials in the environment for the offline plan (`AWS_ACCESS_KEY_ID=plan-only`): the provider wants *some* value to start, but with the skip switches it never sends anything.

From `infra/environments/workload/.terraform.lock.hcl`:

```hcl
provider "registry.terraform.io/hashicorp/aws" {
  version     = "6.70.0"
  constraints = "~> 6.0"
```

`version` is what was installed; `constraints` repeats the allowed range. The `hashes` list under it fingerprints the provider files for macOS and Linux, so CI installs the same bytes.

**Resource types used here (26 in the workload plan):** identity (`aws_iam_user`, `aws_iam_user_policy`, `aws_iam_role`, `aws_iam_role_policy`, `aws_iam_role_policy_attachment`), keys (`aws_kms_key`, `aws_kms_alias`), storage (`aws_s3_bucket` and its companion resources `_public_access_block`, `_versioning`, `_server_side_encryption_configuration`, `_lifecycle_configuration`, `_ownership_controls`, `_policy`), the audit trail (`aws_cloudtrail`), alerting (`aws_cloudwatch_event_rule`, `aws_cloudwatch_event_target`, `aws_sns_topic`, `aws_sns_topic_policy`, `aws_sns_topic_subscription`), posture (`aws_config_*`, `aws_securityhub_*`) and cost (`aws_budgets_budget`). Each service has its own file: [aws-iam.md](aws-iam.md), [aws-kms.md](aws-kms.md), [aws-s3.md](aws-s3.md), [aws-cloudtrail.md](aws-cloudtrail.md), [aws-eventbridge.md](aws-eventbridge.md), [aws-sns.md](aws-sns.md), [aws-config.md](aws-config.md), [aws-security-hub.md](aws-security-hub.md), [aws-budgets.md](aws-budgets.md).

### Every argument of every AWS resource in this repository

A Terraform `resource` block describes one thing to create. Inside it, each line `name = value` is an **argument** and each `name { ... }` is a **nested block** (a group of arguments for one part of the resource). The column "Kind" says whether the AWS provider requires the argument, whether it is optional, whether it opens a nested block, or whether it is a Terraform **meta-argument** that works on every resource. In "Kind", `required` and `optional` were read from the provider's own schema (version 6.70.0, the one in the lock file), so they are not guesses. A path such as `rule.expiration.days` means the argument `days` inside the nested block `expiration` inside the nested block `rule`. Names that contain `var.` or `local.` or `module.` are values that come from elsewhere in the code ([terraform.md](terraform.md)).

#### `aws_budgets_budget`

Declared in `infra/modules/budget/main.tf` lines 1 to 23 (`this`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `budget_type` | required | What the budget measures: `COST` is money spent (other values count usage, reservations or savings plans). | `"COST"` |
| `limit_amount` | optional | The amount of the limit, as text, in the unit below. | `tostring(var.monthly_limit_usd)` |
| `limit_unit` | optional | The unit of the limit: a currency code such as `USD`. | `"USD"` |
| `name` | optional | The name of the budget. | `var.name` |
| `notification.comparison_operator` | required | How the spend is compared with the threshold: `GREATER_THAN` sends the message once the spend is above it. | `"GREATER_THAN"` |
| `notification.notification_type` | required | `ACTUAL` reacts to money already spent; `FORECASTED` reacts to what AWS predicts will be spent. | `"ACTUAL"` / `"FORECASTED"` |
| `notification.subscriber_email_addresses` | optional | The e-mail addresses that receive the message. | `[var.email]` |
| `notification.threshold` | required | The number that triggers the message; meaning depends on `threshold_type`. | `80` / `100` |
| `notification.threshold_type` | required | `PERCENTAGE` means the threshold is a percent of the limit; `ABSOLUTE_VALUE` would mean an amount. | `"PERCENTAGE"` |
| `time_unit` | required | How often the budget starts again: `MONTHLY` here. | `"MONTHLY"` |

#### `aws_cloudtrail`

Declared in `infra/modules/central-trail/main.tf` lines 3 to 18 (`central`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `enable_log_file_validation` | optional | Make CloudTrail write a signed digest file every hour. The digest lists a hash of each log file, so an edited or deleted log file can be detected afterwards. | `true` |
| `enable_logging` | optional | Whether the trail is recording. `false` pauses it without deleting it; the control "an audit trail exists" relies on it being `true`. | `true` |
| `event_selector.include_management_events` | optional | Record **management events**, the calls that create, change or delete resources and sign-ins (as opposed to data events, such as reading an object). | `true` |
| `event_selector.read_write_type` | optional | Which management events to record: `All`, `ReadOnly` or `WriteOnly`. | `"All"` |
| `include_global_service_events` | optional | Also record events of services that are not tied to one Region, such as IAM and the security token service, which are logged in `us-east-1`. | `true` |
| `is_multi_region_trail` | optional | Record events from every AWS Region in one trail, not only the Region the trail lives in. Without it, activity in another Region is not logged. | `true` |
| `kms_key_id` | optional | The key ([aws-kms.md](aws-kms.md)) that encrypts the log files. The log files are encrypted by default with S3 keys; naming a key makes them unreadable to anyone the key policy does not allow. | `var.log_key_arn` |
| `name` | required | The name of the trail. | `var.name` |
| `s3_bucket_name` | required | The bucket the trail writes its log files to ([aws-s3.md](aws-s3.md)). The bucket's policy must allow the CloudTrail service to write there. | `var.log_bucket_name` |

#### `aws_cloudwatch_event_rule`

Declared in `infra/modules/alerting/main.tf` lines 64 to 72 (`detection`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `description` | optional | A sentence for people: what the rule watches for. | `"${each.key}: ${each.value.title}"` |
| `event_pattern` | optional | A JSON filter ([json.md](json.md)): an event is passed on only when every field of the pattern matches the event. Fields not mentioned are ignored. | `each.value.pattern_json` |
| `name` | optional | The name of the rule. | `"${var.name}-${lower(each.key)}"` |
| `state` | optional | `ENABLED` makes the rule active; `DISABLED` keeps it but ignores events. | `each.value.state` |
| `for_each` | meta-argument | A Terraform meta-argument: make one copy of this resource for each item of a map or set. Each copy is addressed by its key, so adding or removing an item adds or removes only that copy. | `var.detections` |

#### `aws_cloudwatch_event_target`

Declared in `infra/modules/alerting/main.tf` lines 74 to 87 (`alert`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `arn` | required | Where matching events are sent: the ARN of the target, here a topic ([aws-sns.md](aws-sns.md)). | `aws_sns_topic.alerts.arn` |
| `input_transformer.input_paths` | optional | A map that pulls values out of the event: each name on the left becomes a variable that holds the part of the event at the path on the right (written like `$.detail.eventName`). | `local.alert_paths` |
| `input_transformer.input_template` | required | The message actually sent: text with the variables from `input_paths` written in angle brackets. It replaces the raw event, so the e-mail is readable. | `format("\"%s\"", replace( replace(replace(replace(replace(var.templ...` |
| `rule` | required | The name of the rule whose matching events this target receives. | `aws_cloudwatch_event_rule.detection[each.key].name` |
| `for_each` | meta-argument | A Terraform meta-argument: make one copy of this resource for each item of a map or set. Each copy is addressed by its key, so adding or removing an item adds or removes only that copy. | `var.detections` |

#### `aws_config_configuration_recorder`

Declared in `infra/modules/posture/main.tf` lines 137 to 145 (`this`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `name` | optional | The name of the recorder. | `var.name` |
| `recording_group.all_supported` | optional | `true` records every supported resource type in the Region. | `true` |
| `recording_group.include_global_resource_types` | optional | Also record resource types that are global, such as IAM roles; usually switched on in only one Region. | `true` |
| `role_arn` | required | The role AWS Config assumes to read the configuration of resources ([aws-iam.md](aws-iam.md)). | `aws_iam_role.config.arn` |

#### `aws_config_configuration_recorder_status`

Declared in `infra/modules/posture/main.tf` lines 154 to 159 (`this`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `is_enabled` | required | Start (`true`) or stop recording. A recorder that exists but is not enabled records nothing. | `true` |
| `name` | required | The recorder this status belongs to. | `aws_config_configuration_recorder.this.name` |
| `depends_on` | meta-argument | A Terraform **meta-argument** (it works on every resource and is not sent to AWS): create this resource only after the listed ones. Terraform normally works out the order from references; `depends_on` states an order that no reference shows, for example a policy that must exist before a service first writes. | `[aws_config_delivery_channel.this]` |

#### `aws_config_delivery_channel`

Declared in `infra/modules/posture/main.tf` lines 147 to 152 (`this`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `name` | optional | The name of the delivery channel. | `var.name` |
| `s3_bucket_name` | required | The bucket where Config writes its snapshots and configuration history. | `aws_s3_bucket.config.bucket` |
| `depends_on` | meta-argument | A Terraform **meta-argument** (it works on every resource and is not sent to AWS): create this resource only after the listed ones. Terraform normally works out the order from references; `depends_on` states an order that no reference shows, for example a policy that must exist before a service first writes. | `[aws_config_configuration_recorder.this, aws_s3_bucket_policy.config]` |

#### `aws_iam_role`

Declared in `infra/modules/drill/main.tf` lines 31 to 46 (`broad`); `infra/modules/posture/main.tf` lines 94 to 106 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `assume_role_policy` | required | The **trust policy**: who may assume the role ([aws-sts.md](aws-sts.md)). The role's permissions are separate. | `jsonencode({ Version = "2012-10-17" Statement = [{ Sid = "OnlyTheDr...` / `jsonencode({ Version = "2012-10-17" Statement = [{ Effect = "Allow"...` |
| `name` | optional | The name of the role; it appears in the role's ARN. | `var.role_name` / `"${var.name}-config-recorder"` |
| `tags` | optional | Labels (key and value text) attached to the resource. They cost nothing and do nothing by themselves; people and scripts find and group resources by them, and the provider's `default_tags` add the project-wide ones. | `{ purpose = "incident-drill" }` |
| `depends_on` | meta-argument | A Terraform **meta-argument** (it works on every resource and is not sent to AWS): create this resource only after the listed ones. Terraform normally works out the order from references; `depends_on` states an order that no reference shows, for example a policy that must exist before a service first writes. | `[aws_iam_user.drill]` |

#### `aws_iam_role_policy`

Declared in `infra/modules/drill/main.tf` lines 56 to 69 (`mint_a_key_for_the_drill_user`); `infra/modules/posture/main.tf` lines 113 to 135 (`deliver`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `name` | optional | The name of this inline policy within the role. | `"create-access-key-for-the-drill-user"` / `"deliver-to-the-config-bucket"` |
| `policy` | required | The permissions, as JSON text: what the role may do. See [aws-iam.md](aws-iam.md). | `jsonencode({ Version = "2012-10-17" Statement = [{ Sid = "CreateAKe...` / `jsonencode({ Version = "2012-10-17" Statement = [ { Sid = "CheckThe...` |
| `role` | required | The role the policy is embedded in (by name). | `aws_iam_role.broad.name` / `aws_iam_role.config.name` |

#### `aws_iam_role_policy_attachment`

Declared in `infra/modules/drill/main.tf` lines 49 to 52 (`power_user`); `infra/modules/posture/main.tf` lines 108 to 111 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `policy_arn` | required | The ARN of an existing managed policy (one that is not embedded in the role). | `"arn:aws:iam::aws:policy/PowerUserAccess"` / `"arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"` |
| `role` | required | The role to attach the managed policy to. | `aws_iam_role.broad.name` / `aws_iam_role.config.name` |

#### `aws_iam_user`

Declared in `infra/modules/drill/main.tf` lines 8 to 12 (`drill`); `infra/modules/drill/main.tf` lines 108 to 114 (`honeytoken`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `name` | required | The name of the IAM user (a long-lived identity, used here only for the drill). | `var.user_name` / `"honeytoken-svc"` |
| `tags` | optional | Labels (key and value text) attached to the resource. They cost nothing and do nothing by themselves; people and scripts find and group resources by them, and the provider's `default_tags` add the project-wide ones. | `{ purpose = "incident-drill" }` / `{ purpose = "honeytoken" }` |
| `count` | meta-argument | A Terraform meta-argument: make this many copies (here 0 or 1, which switches the resource on or off with a variable). | `var.enable_honeytoken ? 1 : 0` |

#### `aws_iam_user_policy`

Declared in `infra/modules/drill/main.tf` lines 15 to 29 (`assume_broad_role`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `name` | optional | The name of the inline policy. | `"assume-the-drill-role"` |
| `policy` | required | The policy document as JSON text, written in HCL with `jsonencode(...)` ([json.md](json.md)). | `jsonencode({ Version = "2012-10-17" Statement = [{ Sid = "AssumeOnl...` |
| `user` | required | The user the policy is embedded in. | `aws_iam_user.drill.name` |

#### `aws_kms_alias`

Declared in `infra/modules/kms-key/main.tf` lines 26 to 29 (`this`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `name` | optional | The friendly name, which must start with `alias/`. Code refers to the alias instead of the key id. | `"alias/${var.alias}"` |
| `target_key_id` | required | The key the alias points to. | `aws_kms_key.this.key_id` |

#### `aws_kms_key`

Declared in `infra/modules/kms-key/main.tf` lines 19 to 24 (`this`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `deletion_window_in_days` | optional | How long a deleted key waits, unusable but recoverable, before it is really removed. The shortest AWS allows is 7. | `var.deletion_window_in_days` |
| `description` | optional | A sentence for people: what the key protects. | `var.description` |
| `enable_key_rotation` | optional | Let AWS create new key material every year. Old data stays readable (the key keeps the old material) and new data uses the new. | `true` |
| `policy` | optional | The **key policy**: who may use and who may administer the key ([aws-kms.md](aws-kms.md)). A key is unusable by anyone this policy does not allow, even an account administrator. | `jsonencode({ Version = "2012-10-17", Statement = concat([local.admi...` |

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

#### `aws_securityhub_account`

Declared in `infra/modules/posture/main.tf` lines 161 to 163 (`this`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `depends_on` | meta-argument | See above: create the Security Hub account only after the resources listed. | `[aws_config_configuration_recorder_status.this]` |

#### `aws_securityhub_standards_subscription`

Declared in `infra/modules/posture/main.tf` lines 165 to 169 (`foundational`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `standards_arn` | required | The ARN of the set of checks to turn on, for example the AWS Foundational Security Best Practices standard. | `"arn:aws:securityhub:${var.region}::standards/aws-foundational-secu...` |
| `depends_on` | meta-argument | A Terraform **meta-argument** (it works on every resource and is not sent to AWS): create this resource only after the listed ones. Terraform normally works out the order from references; `depends_on` states an order that no reference shows, for example a policy that must exist before a service first writes. | `[aws_securityhub_account.this]` |

#### `aws_sns_topic`

Declared in `infra/modules/alerting/main.tf` lines 36 to 39 (`alerts`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `kms_master_key_id` | optional | The key that encrypts messages at rest in the topic. | `module.key.key_arn` |
| `name` | optional | The name of the topic. | `"${var.name}-alerts"` |

#### `aws_sns_topic_policy`

Declared in `infra/modules/alerting/main.tf` lines 41 to 55 (`alerts`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `arn` | required | The topic the policy is attached to. | `aws_sns_topic.alerts.arn` |
| `policy` | required | Who may publish to or subscribe to the topic (here: the EventBridge service for one rule). | `jsonencode({ Version = "2012-10-17" Statement = [{ Sid = "EventsPub...` |

#### `aws_sns_topic_subscription`

Declared in `infra/modules/alerting/main.tf` lines 58 to 62 (`responder`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `endpoint` | required | The address that receives them. | `var.alert_email` |
| `protocol` | required | How messages are delivered: `email` sends a mail after the address confirms. | `"email"` |
| `topic_arn` | required | The topic to subscribe to. | `aws_sns_topic.alerts.arn` |

## Try it yourself

```bash
grep -c '^provider "aws"' infra/environments/workload/providers.tf infra/environments/security/providers.tf
```

Expect `infra/environments/workload/providers.tf:3` and `infra/environments/security/providers.tf:1`: three configurations in the workload environment, one in the security environment.

```bash
grep -A2 'provider "registry' infra/environments/workload/.terraform.lock.hcl
```

Expect the provider address, `version     = "6.70.0"` and `constraints = "~> 6.0"`.

```bash
ls infra/environments/workload/.terraform/providers/registry.terraform.io/hashicorp/aws
```

After `make plan`, expect a folder named `6.70.0`.

```bash
python3 -c "
import json
p = json.load(open('build/workload.json'))
print(len({r['type'] for r in p['resource_changes']}), sorted({r['type'] for r in p['resource_changes']})[:2])"
```

Expect `26 ['aws_budgets_budget', 'aws_cloudtrail']`: 26 different resource types, and the first two alphabetically.

## Mistakes people make

- Running `apply` against a real account with the placeholder credentials set in the environment: the offline switches exist only for `plan`.
- Forgetting to pass a provider alias to a module. The module then works in the default Region and the rule sees nothing.
- Pinning only a range and not committing the lock file: two machines then get different provider versions.
- Assuming an argument exists because it did in an older provider major version; major versions (5, 6, 7) can rename things. This repository stays on 6.x.

## Check yourself

1. What does a provider do? *Translates resource blocks into API calls for one system.*
2. Why does the workload environment configure the provider three times? *Rules see only their own Region, so one configuration per Region is needed, selected by alias.*
3. Why four `skip_*` settings? *Each disables one call that needs a real account, so a plan works offline.*
4. What are default tags for? *Marking every resource so it can be found later, such as at teardown.*
5. What does the lock file add to the version range? *The exact version and file hashes.*

## Further reading

- AWS provider documentation (6.x): <https://registry.terraform.io/providers/hashicorp/aws/6.70.0/docs>
- Provider configuration and aliases: <https://developer.hashicorp.com/terraform/language/providers/configuration>
- Dependency lock file: <https://developer.hashicorp.com/terraform/language/files/dependency-lock>

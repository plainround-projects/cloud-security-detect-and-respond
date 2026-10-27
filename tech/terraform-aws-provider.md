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

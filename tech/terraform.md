# Terraform (and HCL)

## What it is

Terraform is a command-line tool for **infrastructure as code**: you describe the cloud resources you want (a bucket, a trail, an alert rule) in text files, and Terraform works out what to create, change or delete to make the cloud match. The files are written in **HCL** (HashiCorp Configuration Language), a settings-style language of blocks and attributes. This repository needs **Terraform 1.9 or newer** (`required_version = ">= 1.9"`) and was verified with **1.17.0**. OpenTofu, a compatible fork, also works (`TF=tofu make plan`).

## Why this repository uses it

The lesson builds detection and response across **two accounts**: an archive in the security account and the trail, the detections, posture management and the drill weakness in the workload account. Describing all of it as code makes it reviewable and repeatable, and lets Terraform produce a **plan** (a preview of what it would build) without touching a cloud account. The OPA rules and the `audit-rules` command read that plan, which is how "the rule that runs is the rule that was tested" is checked before anything exists.

## Where it appears

| Path | What it does |
| --- | --- |
| `infra/environments/security/` | the security account: the archive key and bucket |
| `infra/environments/workload/` | the workload account: trail, detections in three Regions, posture, drill, budget |
| `infra/modules/` | seven reusable pieces: `kms-key`, `log-archive`, `central-trail`, `alerting`, `drill`, `posture`, `budget` |
| `infra/environments/*/.terraform.lock.hcl` | the provider lock ([terraform-aws-provider.md](terraform-aws-provider.md)) |
| `infra/environments/*/plan-only.tfvars` | placeholder values for the offline plans |
| `infra/environments/*/sandbox.tfvars.example` | what a real values file looks like |
| `Makefile` | `plan`, `validate`, `fmt`, `lint`, `up`, `down` call Terraform |

## How it works underneath

Terraform reads every `.tf` file in a folder (a **root module**) as one configuration. A **resource** block says "this thing should exist". Terraform keeps a **state** (a record of what it has created, kept in a file); for a new folder, the state is empty. `terraform init` downloads the **providers** (plug-ins that know how to talk to a cloud) into `.terraform/`. `terraform plan` compares the configuration with the state and the real cloud, and prints the actions. `terraform apply` carries them out. A **module** is a folder of `.tf` files used like a function: you pass **variables** in and read **outputs** out. Terraform builds a graph from references and creates things in dependency order. Each environment folder is separate, with its own state, so applying the security environment never touches the workload account.

## Walkthrough of this repository's use

This note covers **every Terraform file** in `infra/`: the environments (the folders you run Terraform in), the modules (reusable folders they call), the values files and the lock file. Read this section first; it explains the language the files are written in.

**What Terraform does.** Terraform reads text files that *describe* the cloud resources you want, and works out what it must create, change or delete to make the real cloud match. It does not run the steps you write; it compares the description with what exists. `terraform init` downloads the provider plug-in (the part that talks to AWS), `terraform plan` prints what would change without changing anything, and `terraform apply` makes the changes. This repository only runs `plan` for its offline checks ([make.md](make.md)).

**HCL, the language.** The files end in `.tf` and are written in HCL. The building block is a **block**: a type, optional quoted labels, and a body in curly braces. `resource "aws_s3_bucket" "logs" { ... }` declares one thing: its **type** (`aws_s3_bucket`, defined by the AWS provider) and its **local name** (`logs`, chosen by the author; it must be unique within the module). Inside the body, a line `name = value` is an **argument** that configures the resource. A value can be text in double quotes, a number, `true` or `false`, a list `[a, b]`, a map `{ key = value }` or an expression. In text, `"${var.name}-logs"` **interpolates**: it pastes the value of the expression into the string. `var.NAME` is an input variable, `local.NAME` is a named local value, `module.NAME.OUTPUT` is an output of a module, and `aws_s3_bucket.logs.bucket` is an attribute of another resource. Whenever one block refers to another, Terraform learns that the second must be created first. A line that starts with `#` is a comment.

**Other block types.** `variable "x" { ... }` declares an **input**; `output "x" { ... }` exposes a **result**; `locals { ... }` defines named values computed once; `module "x" { source = "../path" ... }` **calls** a module, a folder of `.tf` files used like a function (variables in, outputs out); `provider "aws" { ... }` configures the plug-in; and the `terraform { ... }` block states which Terraform and which providers are needed. **Expressions** the files use: `condition ? a : b` (choose one of two), `[for x in list : f(x)]` and `{ for k, v in map : k => f(v) }` (build a list or a map from another collection, optionally with an `if` filter), `concat(a, b)` (join two lists), `jsonencode(value)` (turn a value into JSON text), and `each.key`/`each.value`, available when a block uses `for_each` (one copy per entry) or `count` (a number of copies).

### Environments

An **environment** is a folder you run Terraform in. It composes the modules and holds the values. Each environment has its own state, so applying one never touches another.

#### Environment `infra/environments/security`

##### `infra/environments/security/versions.tf`

From `infra/environments/security/versions.tf` (lines 1 to 10):

```hcl
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

The `terraform` block holds settings about Terraform itself. `required_version = ">= 1.9"` makes Terraform refuse to run if it is older than 1.9. `required_providers` lists the provider plug-ins this folder needs: the entry `aws` has `source = "hashicorp/aws"` (the registry address of the AWS provider) and `version = "~> 6.0"`, meaning "6.0 or newer, but below 7" ([terraform-aws-provider.md](terraform-aws-provider.md)). Every module repeats the same block so it can be used and checked on its own.

##### `infra/environments/security/providers.tf`

From `infra/environments/security/providers.tf` (lines 1 to 18):

```hcl
# The security account. `plan_only` makes the provider skip every call to AWS, so `make plan` works with no account and no
# credentials. It must stay false for `terraform apply`.
provider "aws" {
  region = var.region

  skip_credentials_validation = var.plan_only
  skip_metadata_api_check     = var.plan_only
  skip_requesting_account_id  = var.plan_only
  skip_region_validation      = var.plan_only

  default_tags {
    tags = {
      project = "detect-and-respond"
      account = "security"
      managed = "terraform"
    }
  }
}
```

The comment above the block says: "The security account. `plan_only` makes the provider skip every call to AWS, so `make plan` works with no account and no credentials. It must stay false for `terraform apply`.". 
Configures the **AWS provider** ([terraform-aws-provider.md](terraform-aws-provider.md)). `region = var.region` is where resources are created. The four `skip_*` attributes, each set to `var.plan_only`, switch off every call that needs a real account when `plan_only` is true: `skip_credentials_validation` (do not check the credentials with a call to the token service), `skip_metadata_api_check` (do not look for credentials from a cloud server's metadata address), `skip_requesting_account_id` (do not ask AWS for the account number, which comes from a variable) and `skip_region_validation` (do not check the region name against a list). That is what makes a plan without an account possible. The nested `default_tags` block lists tags that the provider puts on **every** resource that supports tags, here a project name, the account role and `managed = "terraform"`; the teardown scripts find leftovers by the project tag.

##### `infra/environments/security/variables.tf`

From `infra/environments/security/variables.tf` (lines 1 to 5):

```hcl
variable "plan_only" {
  description = "Skip all provider calls so the configuration can be planned without credentials. Never true for apply."
  type        = bool
  default     = false
}
```

Declares the **input variable** `plan_only`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Skip all provider calls so the configuration can be planned without credentials. Never true for apply." `type = bool` restricts the value to true or false; Terraform refuses any other kind of value. `default = false` is the value used when the caller supplies none, which makes the variable optional.

From `infra/environments/security/variables.tf` (lines 7 to 11):

```hcl
variable "region" {
  description = "Region of the archive bucket (the workload account's home Region)."
  type        = string
  default     = "eu-west-1"
}
```

Declares the **input variable** `region`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Region of the archive bucket (the workload account's home Region)." `type = string` restricts the value to text; Terraform refuses any other kind of value. `default = "eu-west-1"` is the value used when the caller supplies none, which makes the variable optional.

From `infra/environments/security/variables.tf` (lines 13 to 21):

```hcl
variable "security_account_id" {
  description = "The security account, which owns the archive. scripts/01-deploy-security.sh writes it; it is never committed."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.security_account_id))
    error_message = "security_account_id must be 12 digits."
  }
}
```

Declares the **input variable** `security_account_id`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The security account, which owns the archive. scripts/01-deploy-security.sh writes it; it is never committed." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value. The `validation` block rejects a bad value before anything is planned: the `condition` `can(regex("^[0-9]{12}$", var.security_account_id))` must be true, otherwise Terraform stops with the `error_message` "security_account_id must be 12 digits.". `can(regex(...))` is true when the text matches the pattern.

From `infra/environments/security/variables.tf` (lines 23 to 31):

```hcl
variable "workload_account_id" {
  description = "The workload account whose trail delivers here."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.workload_account_id))
    error_message = "workload_account_id must be 12 digits."
  }
}
```

Declares the **input variable** `workload_account_id`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The workload account whose trail delivers here." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value. The `validation` block rejects a bad value before anything is planned: the `condition` `can(regex("^[0-9]{12}$", var.workload_account_id))` must be true, otherwise Terraform stops with the `error_message` "workload_account_id must be 12 digits.". `can(regex(...))` is true when the text matches the pattern.

From `infra/environments/security/variables.tf` (lines 33 to 37):

```hcl
variable "retention_days" {
  description = "Compliance-mode retention. Nobody can shorten it, so the exercise uses 1."
  type        = number
  default     = 1
}
```

Declares the **input variable** `retention_days`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Compliance-mode retention. Nobody can shorten it, so the exercise uses 1." `type = number` restricts the value to a number; Terraform refuses any other kind of value. `default = 1` is the value used when the caller supplies none, which makes the variable optional.

From `infra/environments/security/variables.tf` (lines 39 to 43):

```hcl
variable "expire_days" {
  description = "Days after which log files expire and the bucket can be destroyed."
  type        = number
  default     = 2
}
```

Declares the **input variable** `expire_days`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Days after which log files expire and the bucket can be destroyed." `type = number` restricts the value to a number; Terraform refuses any other kind of value. `default = 2` is the value used when the caller supplies none, which makes the variable optional.

##### `infra/environments/security/main.tf`

From `infra/environments/security/main.tf` (lines 1 to 5):

```hcl
locals {
  trail_name  = "central-trail"
  bucket_name = "detect-archive-${var.security_account_id}"
  trail_arn   = "arn:aws:cloudtrail:${var.region}:${var.workload_account_id}:trail/${local.trail_name}"
}
```

Three named values: the archive bucket's name (with the security account's number, because bucket names are unique across all of AWS), and the full name (ARN) of the workload account's trail, **built from text** so the key policy can name a trail in another account.

From `infra/environments/security/main.tf` (lines 7 to 45):

```hcl
# The key that encrypts the archive. The workload account's trail may use it to write; the security account's principals may
# decrypt through the storage service; the account root administers it but cannot decrypt on its own authority.
module "archive_key" {
  source = "../../modules/kms-key"

  alias       = "detect-archive"
  description = "Encrypts the central audit log archive."
  account_id  = var.security_account_id
  region      = var.region

  statements = [
    {
      Sid       = "WorkloadTrailEncryptsLogFiles"
      Effect    = "Allow"
      Principal = { Service = "cloudtrail.amazonaws.com" }
      Action    = "kms:GenerateDataKey*"
      Resource  = "*"
      Condition = {
        StringEquals = { "aws:SourceArn" = local.trail_arn }
        StringLike   = { "kms:EncryptionContext:aws:cloudtrail:arn" = "arn:aws:cloudtrail:*:${var.workload_account_id}:trail/*" }
      }
    },
    {
      Sid       = "WorkloadTrailDescribesTheKey"
      Effect    = "Allow"
      Principal = { Service = "cloudtrail.amazonaws.com" }
      Action    = "kms:DescribeKey"
      Resource  = "*"
    },
    {
      Sid       = "SecurityAccountReadsLogsThroughTheStorageService"
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${var.security_account_id}:root" }
      Action    = "kms:Decrypt"
      Resource  = "*"
      Condition = { StringEquals = { "kms:ViaService" = "s3.${var.region}.amazonaws.com" } }
    },
  ]
}
```

The comment above the block says: "The key that encrypts the archive. The workload account's trail may use it to write; the security account's principals may decrypt through the storage service; the account root administers it but cannot decrypt on its own authority.". 
Creates the **archive key**. The comment above says: the workload account's trail may use it to write; the security account's principals may decrypt through the storage service; the account root administers it but cannot decrypt on its own authority ([aws-kms.md](aws-kms.md)). The `statements` list has three grants:

- `WorkloadTrailEncryptsLogFiles`: the audit service (`Principal = { Service = "cloudtrail.amazonaws.com" }`) may `kms:GenerateDataKey*`, limited by `StringEquals` on `aws:SourceArn` (the one trail) and `StringLike` on `kms:EncryptionContext:aws:cloudtrail:arn` (trails of the workload account).
- `WorkloadTrailDescribesTheKey`: the same service may `kms:DescribeKey`.
- `SecurityAccountReadsLogsThroughTheStorageService`: the security account (`arn:aws:iam::<security account>:root`) may `kms:Decrypt`, only when the call comes through the storage service (`"kms:ViaService" = "s3.<region>.amazonaws.com"`).


The arguments:

- `source = "../../modules/kms-key"`: the folder of the module that is used here, `kms-key` ([terraform.md](terraform.md)).
- `alias = "detect-archive"` sets the module's input `alias`, described there as "Alias of the key, without the alias/ prefix."
- `description = "Encrypts the central audit log archive."` sets the module's input `description`, described there as "What the key protects."
- `account_id = var.security_account_id` sets the module's input `account_id`, described there as "Account that owns the key; its root administers the key." The value is the input variable `security_account_id`.
- `region = var.region` sets the module's input `region`, described there as "Region of the key." The value is the input variable `region`.
- `statements = [ ...` sets the module's input `statements`, described there as "Key policy statements that grant use of the key, as policy-document statement objects." The value spans several lines and is explained after this list.

From `infra/environments/security/main.tf` (lines 47 to 59):

```hcl
module "log_archive" {
  source = "../../modules/log-archive"

  bucket_name         = local.bucket_name
  workload_account_id = var.workload_account_id
  region              = var.region
  trail_name          = local.trail_name
  key_alias_arn       = module.archive_key.alias_arn
  retention_days      = var.retention_days
  expire_days         = var.expire_days

  depends_on = [module.archive_key]
}
```

Creates the **archive** by using the `log-archive` module ([aws-s3.md](aws-s3.md)). `depends_on = [module.archive_key]` creates the key first.

The arguments:

- `source = "../../modules/log-archive"`: the folder of the module that is used here, `log-archive` ([terraform.md](terraform.md)).
- `bucket_name = local.bucket_name` sets the module's input `bucket_name`, described there as "Name of the archive bucket, in the security account." The value is the local value `bucket_name`.
- `workload_account_id = var.workload_account_id` sets the module's input `workload_account_id`, described there as "The account whose trail delivers here; only its trail may write." The value is the input variable `workload_account_id`.
- `region = var.region` sets the module's input `region`, described there as "Home region of the workload account's trail." The value is the input variable `region`.
- `trail_name = local.trail_name` sets the module's input `trail_name`, described there as "Name of the workload account's trail; the bucket policy admits that trail only." The value is the local value `trail_name`.
- `key_alias_arn = module.archive_key.alias_arn` sets the module's input `key_alias_arn`, described there as "Alias ARN of the key that encrypts the archive." The value is the output `alias_arn` of the module `archive_key`.
- `retention_days = var.retention_days` sets the module's input `retention_days`, described there as "Compliance-mode retention. Nobody can shorten it, so the exercise uses 1." The value is the input variable `retention_days`.
- `expire_days = var.expire_days` sets the module's input `expire_days`, described there as "Days after which log files expire. Must be longer than retention_days." The value is the input variable `expire_days`.
- `depends_on = [module.archive_key]` forces Terraform to create the listed module(s) **first**, an ordering that Terraform could not discover by itself because the modules do not reference each other.

##### `infra/environments/security/outputs.tf`

From `infra/environments/security/outputs.tf` (lines 1 to 4):

```hcl
output "log_bucket_name" {
  description = "Archive bucket; pass it to the workload environment as log_bucket_name."
  value       = module.log_archive.bucket_name
}
```

Declares the **output** `log_bucket_name`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "Archive bucket; pass it to the workload environment as log_bucket_name." `value = module.log_archive.bucket_name` is the output `bucket_name` of the module `log_archive`.

From `infra/environments/security/outputs.tf` (lines 6 to 9):

```hcl
output "log_key_arn" {
  description = "Archive key ARN; pass it to the workload environment as log_key_arn."
  value       = module.archive_key.key_arn
}
```

Declares the **output** `log_key_arn`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "Archive key ARN; pass it to the workload environment as log_key_arn." `value = module.archive_key.key_arn` is the output `key_arn` of the module `archive_key`.

From `infra/environments/security/outputs.tf` (lines 11 to 14):

```hcl
output "trail_name" {
  description = "The trail name the bucket policy admits."
  value       = "central-trail"
}
```

Declares the **output** `trail_name`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "The trail name the bucket policy admits." `value = "central-trail"` is the expression that computes it: `"central-trail"`.

##### `infra/environments/security/plan-only.tfvars`

A `.tfvars` file gives **values to the variables** that the configuration declares: each line is `name = value`. Terraform reads a file passed with `-var-file` and any file whose name ends in `.auto.tfvars` without being asked.

From `infra/environments/security/plan-only.tfvars` (lines 1 to 2):

```text
# Placeholders for `make plan`: no account, no credentials, nothing is read from or sent to a cloud.
plan_only           = true
```

The comment above the line says: "Placeholders for `make plan`: no account, no credentials, nothing is read from or sent to a cloud.". Sets the variable `plan_only` to `true`.

From `infra/environments/security/plan-only.tfvars` (line 3):

```text
security_account_id = "000000000001"
```

Sets the variable `security_account_id` to `"000000000001"`.

From `infra/environments/security/plan-only.tfvars` (line 4):

```text
workload_account_id = "000000000000"
```

Sets the variable `workload_account_id` to `"000000000000"`.

##### `infra/environments/security/sandbox.tfvars.example`

A `.tfvars` file gives **values to the variables** that the configuration declares: each line is `name = value`. Terraform reads a file passed with `-var-file` and any file whose name ends in `.auto.tfvars` without being asked.

From `infra/environments/security/sandbox.tfvars.example` (lines 1 to 2):

```text
# Copy to sandbox.auto.tfvars (ignored by git) and fill in. scripts/01-deploy-security.sh does this for you.
security_account_id = "REPLACE_WITH_THE_SECURITY_ACCOUNT_ID"
```

The comment above the line says: "Copy to sandbox.auto.tfvars (ignored by git) and fill in. scripts/01-deploy-security.sh does this for you.". Sets the variable `security_account_id` to `"REPLACE_WITH_THE_SECURITY_ACCOUNT_ID"`.

From `infra/environments/security/sandbox.tfvars.example` (line 3):

```text
workload_account_id = "REPLACE_WITH_THE_WORKLOAD_ACCOUNT_ID"
```

Sets the variable `workload_account_id` to `"REPLACE_WITH_THE_WORKLOAD_ACCOUNT_ID"`.

From `infra/environments/security/sandbox.tfvars.example` (line 4):

```text
retention_days      = 1 # compliance mode: nobody, including you, can shorten it
```

Sets the variable `retention_days` to `1`. The comment at the end of the line says: "compliance mode: nobody, including you, can shorten it".

From `infra/environments/security/sandbox.tfvars.example` (line 5):

```text
expire_days         = 2 # the bucket can be destroyed once the files have expired
```

Sets the variable `expire_days` to `2`. The comment at the end of the line says: "the bucket can be destroyed once the files have expired".

##### `infra/environments/security/.terraform.lock.hcl`

From `infra/environments/security/.terraform.lock.hcl` (lines 1 to 2):

```hcl
# This file is maintained automatically by "terraform init".
# Manual edits may be lost in future updates.
```

The two comment lines at the top say the file is maintained by `terraform init`.

From `infra/environments/security/.terraform.lock.hcl` (lines 4 to 27):

```hcl
provider "registry.terraform.io/hashicorp/aws" {
  version     = "6.70.0"
  constraints = "~> 6.0"
  hashes = [
    "h1:HCr4MYgxlkFBOAeWKOoktNNzZaQX8ZZY4YTxmL/1V/Y=",
    "h1:L+05gOXA+kdYTtayIw0WxdaTp3JryZCMZpfrJVhoJA0=",
    "zh:068ca7ed4fc77e3d63d7fac54515a426a32f3dc143b55a6ad00963fe68289955",
    "zh:2d8c016b3809ab32f536b01bf2c98fcbdeb066b7b7e50f756ff6ff1e0b0539c7",
    "zh:450d960b60ea81268bd355600340787254f750d76e0075208a6fb903d7336b09",
    "zh:50447833cce21288ffc331342f9d83854e80515e2d86e8f5776a07ce18866b20",
    "zh:58acc041b080778ded75320e241ebcf6cf2ed145bede644b86a4784ce46086c6",
    "zh:7e899a44a1da95fefb1b04b231cf7cdb5871f482f60a710ede78bf25ac265724",
    "zh:8b141d13f4b84d7a47bc5a4855d0fc985191317b3249603532d4de03db5741c5",
    "zh:9035357f7d065ce8d35a9b05337977910683219c0f13fa09155d28f9b32e23a7",
    "zh:9b12af85486a96aedd8d7984b0ff811a4b42e3d88dad1a3fb4c0b580d04fa425",
    "zh:9ba0990a876d2641a185ca88263719afc4d5ac43533bdb147437f0073d2cd74d",
    "zh:a8773c7a02e1b3290df89351ee493fd8b74f807f92a7f69534e05901d4515761",
    "zh:ab0ebb298578eeeffe0fbf0a8b27ce99acd4419b7049272f1ab87e8c47229407",
    "zh:b88a3f22127bfb17604adc53e9bdb8ed0eddf4b9b77bf19871cba2e7fcd5b4a3",
    "zh:c7b1fb41e7f086b670f78932ede2b539903a8d71bac06f55f14a1a33d09a1ccf",
    "zh:df482bd93f51125f78feab7742aae1d7f22c7108ee2dc47787c4a1d611e6ccfd",
    "zh:fca401ffaa42d5f350d667123569de51a23de8c30b87ce0bd9d86fc80835fd4d",
  ]
}
```

`.terraform.lock.hcl` is written by `terraform init`; nobody edits it. It records the exact provider that was installed so that every machine gets the same one. `provider "registry.terraform.io/hashicorp/aws"` names the provider by its full registry address. `version = "6.70.0"` is the exact version installed. `constraints = "~> 6.0"` repeats the range the configuration allows. `hashes` is a list of **fingerprints** of the provider's files: each `h1:` entry is a hash of the provider package for one kind of machine, and each `zh:` entry is a hash of the downloaded archive; `terraform init` refuses to use a provider whose files do not match. The entries cover both macOS and Linux, so the CI installs the same bytes.

#### Environment `infra/environments/workload`

##### `infra/environments/workload/versions.tf`

From `infra/environments/workload/versions.tf` (lines 1 to 10):

```hcl
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

The `terraform` block holds settings about Terraform itself. `required_version = ">= 1.9"` makes Terraform refuse to run if it is older than 1.9. `required_providers` lists the provider plug-ins this folder needs: the entry `aws` has `source = "hashicorp/aws"` (the registry address of the AWS provider) and `version = "~> 6.0"`, meaning "6.0 or newer, but below 7" ([terraform-aws-provider.md](terraform-aws-provider.md)). Every module repeats the same block so it can be used and checked on its own.

##### `infra/environments/workload/providers.tf`

From `infra/environments/workload/providers.tf` (lines 1 to 19):

```hcl
# The workload account, in three Regions. EventBridge only sees events in its own Region, so each Region that matters
# gets its own provider. IAM events arrive in us-east-1; the sandbox works in the home Region; ap-southeast-2 stands for a
# Region the account does not operate in. `plan_only` makes the providers skip every call to AWS.
provider "aws" {
  region = var.region

  skip_credentials_validation = var.plan_only
  skip_metadata_api_check     = var.plan_only
  skip_requesting_account_id  = var.plan_only
  skip_region_validation      = var.plan_only

  default_tags {
    tags = {
      project = "detect-and-respond"
      account = "workload"
      managed = "terraform"
    }
  }
}
```

The comment above the block says: "The workload account, in three Regions. EventBridge only sees events in its own Region, so each Region that matters gets its own provider. IAM events arrive in us-east-1; the sandbox works in the home Region; ap-southeast-2 stands for a Region the account does not operate in. `plan_only` makes the providers skip every call to AWS.". 
Configures the **AWS provider** ([terraform-aws-provider.md](terraform-aws-provider.md)). `region = var.region` is where resources are created. The four `skip_*` attributes, each set to `var.plan_only`, switch off every call that needs a real account when `plan_only` is true: `skip_credentials_validation` (do not check the credentials with a call to the token service), `skip_metadata_api_check` (do not look for credentials from a cloud server's metadata address), `skip_requesting_account_id` (do not ask AWS for the account number, which comes from a variable) and `skip_region_validation` (do not check the region name against a list). That is what makes a plan without an account possible. The nested `default_tags` block lists tags that the provider puts on **every** resource that supports tags, here a project name, the account role and `managed = "terraform"`; the teardown scripts find leftovers by the project tag.

From `infra/environments/workload/providers.tf` (lines 21 to 37):

```hcl
provider "aws" {
  alias  = "global"
  region = "us-east-1"

  skip_credentials_validation = var.plan_only
  skip_metadata_api_check     = var.plan_only
  skip_requesting_account_id  = var.plan_only
  skip_region_validation      = var.plan_only

  default_tags {
    tags = {
      project = "detect-and-respond"
      account = "workload"
      managed = "terraform"
    }
  }
}
```

A **second configuration of the AWS provider**, told apart by `alias`. `region` is fixed to a different Region, so any module handed this alias creates its resources there. The four `skip_*` attributes repeat the offline switches, because each configuration is separate (see the first provider block), and `default_tags` repeats the tags ([terraform-aws-provider.md](terraform-aws-provider.md)).

From `infra/environments/workload/providers.tf` (lines 39 to 55):

```hcl
provider "aws" {
  alias  = "watch_ap_southeast_2"
  region = "ap-southeast-2"

  skip_credentials_validation = var.plan_only
  skip_metadata_api_check     = var.plan_only
  skip_requesting_account_id  = var.plan_only
  skip_region_validation      = var.plan_only

  default_tags {
    tags = {
      project = "detect-and-respond"
      account = "workload"
      managed = "terraform"
    }
  }
}
```

A **second configuration of the AWS provider**, told apart by `alias`. `region` is fixed to a different Region, so any module handed this alias creates its resources there. The four `skip_*` attributes repeat the offline switches, because each configuration is separate (see the first provider block), and `default_tags` repeats the tags ([terraform-aws-provider.md](terraform-aws-provider.md)).

##### `infra/environments/workload/variables.tf`

From `infra/environments/workload/variables.tf` (lines 1 to 5):

```hcl
variable "plan_only" {
  description = "Skip all provider calls so the configuration can be planned without credentials. Never true for apply."
  type        = bool
  default     = false
}
```

Declares the **input variable** `plan_only`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Skip all provider calls so the configuration can be planned without credentials. Never true for apply." `type = bool` restricts the value to true or false; Terraform refuses any other kind of value. `default = false` is the value used when the caller supplies none, which makes the variable optional.

From `infra/environments/workload/variables.tf` (lines 7 to 11):

```hcl
variable "region" {
  description = "The workload account's home Region."
  type        = string
  default     = "eu-west-1"
}
```

Declares the **input variable** `region`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The workload account's home Region." `type = string` restricts the value to text; Terraform refuses any other kind of value. `default = "eu-west-1"` is the value used when the caller supplies none, which makes the variable optional.

From `infra/environments/workload/variables.tf` (lines 13 to 21):

```hcl
variable "workload_account_id" {
  description = "The sandbox workload account. scripts/02-deploy-workload.sh writes it; it is never committed."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.workload_account_id))
    error_message = "workload_account_id must be 12 digits."
  }
}
```

Declares the **input variable** `workload_account_id`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The sandbox workload account. scripts/02-deploy-workload.sh writes it; it is never committed." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value. The `validation` block rejects a bad value before anything is planned: the `condition` `can(regex("^[0-9]{12}$", var.workload_account_id))` must be true, otherwise Terraform stops with the `error_message` "workload_account_id must be 12 digits.". `can(regex(...))` is true when the text matches the pattern.

From `infra/environments/workload/variables.tf` (lines 23 to 26):

```hcl
variable "log_bucket_name" {
  description = "Archive bucket in the security account (output log_bucket_name of the security environment)."
  type        = string
}
```

Declares the **input variable** `log_bucket_name`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Archive bucket in the security account (output log_bucket_name of the security environment)." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/environments/workload/variables.tf` (lines 28 to 31):

```hcl
variable "log_key_arn" {
  description = "Archive key in the security account (output log_key_arn of the security environment)."
  type        = string
}
```

Declares the **input variable** `log_key_arn`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Archive key in the security account (output log_key_arn of the security environment)." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/environments/workload/variables.tf` (lines 33 to 36):

```hcl
variable "alert_email" {
  description = "Address that receives the alerts and the budget notices."
  type        = string
}
```

Declares the **input variable** `alert_email`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Address that receives the alerts and the budget notices." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/environments/workload/variables.tf` (lines 38 to 42):

```hcl
variable "monthly_budget_usd" {
  description = "Monthly cost limit for the account's budget."
  type        = number
  default     = 20
}
```

Declares the **input variable** `monthly_budget_usd`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Monthly cost limit for the account's budget." `type = number` restricts the value to a number; Terraform refuses any other kind of value. `default = 20` is the value used when the caller supplies none, which makes the variable optional.

From `infra/environments/workload/variables.tf` (lines 44 to 48):

```hcl
variable "enable_drill" {
  description = "Create the deliberate weakness for the incident drill. True only while the exercise runs."
  type        = bool
  default     = false
}
```

Declares the **input variable** `enable_drill`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Create the deliberate weakness for the incident drill. True only while the exercise runs." `type = bool` restricts the value to true or false; Terraform refuses any other kind of value. `default = false` is the value used when the caller supplies none, which makes the variable optional.

From `infra/environments/workload/variables.tf` (lines 50 to 54):

```hcl
variable "enable_posture" {
  description = "Turn on Security Hub and AWS Config recording."
  type        = bool
  default     = true
}
```

Declares the **input variable** `enable_posture`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Turn on Security Hub and AWS Config recording." `type = bool` restricts the value to true or false; Terraform refuses any other kind of value. `default = true` is the value used when the caller supplies none, which makes the variable optional.

From `infra/environments/workload/variables.tf` (lines 56 to 60):

```hcl
variable "honeytoken_access_key_id" {
  description = "Access key id of the honeytoken user. Empty until scripts/06-honeytoken.sh has created it; detection D5 is deployed only when set."
  type        = string
  default     = ""
}
```

Declares the **input variable** `honeytoken_access_key_id`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Access key id of the honeytoken user. Empty until scripts/06-honeytoken.sh has created it; detection D5 is deployed only when set." `type = string` restricts the value to text; Terraform refuses any other kind of value. `default = ""` is the value used when the caller supplies none, which makes the variable optional.

From `infra/environments/workload/variables.tf` (lines 62 to 66):

```hcl
variable "force_destroy" {
  description = "Let destroy delete non-empty buckets. True only for the throwaway sandbox."
  type        = bool
  default     = false
}
```

Declares the **input variable** `force_destroy`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Let destroy delete non-empty buckets. True only for the throwaway sandbox." `type = bool` restricts the value to true or false; Terraform refuses any other kind of value. `default = false` is the value used when the caller supplies none, which makes the variable optional.

##### `infra/environments/workload/main.tf`

From `infra/environments/workload/main.tf` (lines 1 to 28):

```hcl
locals {
  trail_name     = "central-trail"
  detections_dir = "${path.root}/../../../detections"

  detection_all = {
    for file in fileset(local.detections_dir, "d*.json") :
    jsondecode(file("${local.detections_dir}/${file}")).id => jsondecode(file("${local.detections_dir}/${file}"))
  }

  # A detection with a parameter (the honeytoken's key id) is deployed only once the parameter is set.
  honeytoken_ready = var.honeytoken_access_key_id != ""
  deployable       = { for id, d in local.detection_all : id => d if !contains(keys(d), "parameters") || local.honeytoken_ready }

  template = file("${local.detections_dir}/alert-template.txt")

  # Where each detection runs: "global" (us-east-1, where IAM events arrive), "home" and "watch" (a Region we do not operate in).
  for_target = {
    for target in ["global", "home", "watch"] : target => {
      for id, d in local.deployable : id => {
        title        = d.title
        severity     = d.severity
        first_step   = d.firstStep
        pattern_json = replace(jsonencode(d.pattern), "__HONEYTOKEN_ACCESS_KEY_ID__", var.honeytoken_access_key_id)
        state        = try(d.includeReadOnly, false) ? "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS" : "ENABLED"
      } if contains(d.deployTo, target)
    }
  }
}
```

Named values that decide **what is deployed where**.

- `trail_name` and `detections_dir` are the trail's name and the folder of the detection files (`path.root` is the folder of this environment, and the dots go up three levels to the repository's `detections/`).
- `detection_all` reads every detection file into a map: `fileset(folder, "d*.json")` lists the files, `jsondecode(file(...))` reads one file as data ([json.md](json.md)), `.id` is its id; the `for` expression builds `{ id => detection }`.
- `honeytoken_ready` is true when a honeytoken key id was given. The comment says a detection with a parameter is deployed only once the parameter is set. `deployable` keeps the detections that have no `parameters` entry, or all of them when `honeytoken_ready` (`contains(keys(d), "parameters")` asks whether the detection has that field).
- `template` reads the alert text file.
- `for_target` builds, for each of the three places `global`, `home` and `watch`, the detections that run there (`if contains(d.deployTo, target)`). For each it keeps `title`, `severity`, `first_step`, the pattern as JSON text (`jsonencode(d.pattern)`, with `replace` filling the honeytoken placeholder) and `state` (`try(d.includeReadOnly, false) ? "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS" : "ENABLED"`: the wider state only for a detection that sets `includeReadOnly`). The comment explains the three places: `global` (the region where IAM events arrive), `home`, and `watch` (a region the account does not operate in).

From `infra/environments/workload/main.tf` (lines 30 to 37):

```hcl
# Step 1: every action in every Region goes to the archive in the security account.
module "central_trail" {
  source = "../../modules/central-trail"

  name            = local.trail_name
  log_bucket_name = var.log_bucket_name
  log_key_arn     = var.log_key_arn
}
```

The comment above the block says: "Step 1: every action in every Region goes to the archive in the security account.". Step 1: creates the **multi-region trail** that sends every action to the archive in the security account ([aws-cloudtrail.md](aws-cloudtrail.md)).

The arguments:

- `source = "../../modules/central-trail"`: the folder of the module that is used here, `central-trail` ([terraform.md](terraform.md)).
- `name = local.trail_name` sets the module's input `name`, described there as "Trail name; the archive bucket policy admits this trail only." The value is the local value `trail_name`.
- `log_bucket_name = var.log_bucket_name` sets the module's input `log_bucket_name`, described there as "Archive bucket in the security account." The value is the input variable `log_bucket_name`.
- `log_key_arn = var.log_key_arn` sets the module's input `log_key_arn`, described there as "ARN of the archive key in the security account." The value is the input variable `log_key_arn`.

From `infra/environments/workload/main.tf` (lines 39 to 50):

```hcl
# Step 2: the detections, one alerting module per Region. Add a watched Region by adding a provider and a module like the last one.
module "alerting_global" {
  source    = "../../modules/alerting"
  providers = { aws = aws.global }

  name        = "detect-global"
  region      = "us-east-1"
  account_id  = var.workload_account_id
  alert_email = var.alert_email
  template    = local.template
  detections  = local.for_target["global"]
}
```

The comment above the block says: "Step 2: the detections, one alerting module per Region. Add a watched Region by adding a provider and a module like the last one.". Step 2: creates the **alerting for IAM events** in `us-east-1`, where IAM events arrive. The comment above all the alerting modules says why there are several: EventBridge sees only events in its own Region, so each Region that matters gets its own copy ([aws-eventbridge.md](aws-eventbridge.md)).

The arguments:

- `source = "../../modules/alerting"`: the folder of the module that is used here, `alerting` ([terraform.md](terraform.md)).
- `providers = { aws = aws.global }` hands the module a **named copy of the provider** (the alias), so its resources are created in that region.
- `name = "detect-global"` sets the module's input `name`, described there as "Name prefix of this Region's alerting, for example detect-global."
- `region = "us-east-1"` sets the module's input `region`, described there as "The Region this instance runs in (the provider decides; used in names and policies)."
- `account_id = var.workload_account_id` sets the module's input `account_id`, described there as "The account that owns the rules." The value is the input variable `workload_account_id`.
- `alert_email = var.alert_email` sets the module's input `alert_email`, described there as "Address that receives the alerts." The value is the input variable `alert_email`.
- `template = local.template` sets the module's input `template`, described there as "Alert text template from detections/alert-template.txt." The value is the local value `template`.
- `detections = local.for_target["global"]` sets the module's input `detections`, described there as "Detections to deploy here, by id: title, severity, first_step, pattern_json (the pattern as JSON text) and state."

From `infra/environments/workload/main.tf` (lines 52 to 61):

```hcl
module "alerting_home" {
  source = "../../modules/alerting"

  name        = "detect-home"
  region      = var.region
  account_id  = var.workload_account_id
  alert_email = var.alert_email
  template    = local.template
  detections  = local.for_target["home"]
}
```

Creates the alerting in the **home Region**, where the sandbox works. With no `providers` argument it uses the default provider configuration.

The arguments:

- `source = "../../modules/alerting"`: the folder of the module that is used here, `alerting` ([terraform.md](terraform.md)).
- `name = "detect-home"` sets the module's input `name`, described there as "Name prefix of this Region's alerting, for example detect-global."
- `region = var.region` sets the module's input `region`, described there as "The Region this instance runs in (the provider decides; used in names and policies)." The value is the input variable `region`.
- `account_id = var.workload_account_id` sets the module's input `account_id`, described there as "The account that owns the rules." The value is the input variable `workload_account_id`.
- `alert_email = var.alert_email` sets the module's input `alert_email`, described there as "Address that receives the alerts." The value is the input variable `alert_email`.
- `template = local.template` sets the module's input `template`, described there as "Alert text template from detections/alert-template.txt." The value is the local value `template`.
- `detections = local.for_target["home"]` sets the module's input `detections`, described there as "Detections to deploy here, by id: title, severity, first_step, pattern_json (the pattern as JSON text) and state."

From `infra/environments/workload/main.tf` (lines 63 to 73):

```hcl
module "alerting_watch_ap_southeast_2" {
  source    = "../../modules/alerting"
  providers = { aws = aws.watch_ap_southeast_2 }

  name        = "detect-watch"
  region      = "ap-southeast-2"
  account_id  = var.workload_account_id
  alert_email = var.alert_email
  template    = local.template
  detections  = local.for_target["watch"]
}
```

Creates the alerting in a **watched Region** the account does not use, so a call there is detected. The comment says that adding a watched Region is adding a provider and a module like this one.

The arguments:

- `source = "../../modules/alerting"`: the folder of the module that is used here, `alerting` ([terraform.md](terraform.md)).
- `providers = { aws = aws.watch_ap_southeast_2 }` hands the module a **named copy of the provider** (the alias), so its resources are created in that region.
- `name = "detect-watch"` sets the module's input `name`, described there as "Name prefix of this Region's alerting, for example detect-global."
- `region = "ap-southeast-2"` sets the module's input `region`, described there as "The Region this instance runs in (the provider decides; used in names and policies)."
- `account_id = var.workload_account_id` sets the module's input `account_id`, described there as "The account that owns the rules." The value is the input variable `workload_account_id`.
- `alert_email = var.alert_email` sets the module's input `alert_email`, described there as "Address that receives the alerts." The value is the input variable `alert_email`.
- `template = local.template` sets the module's input `template`, described there as "Alert text template from detections/alert-template.txt." The value is the local value `template`.
- `detections = local.for_target["watch"]` sets the module's input `detections`, described there as "Detections to deploy here, by id: title, severity, first_step, pattern_json (the pattern as JSON text) and state."

From `infra/environments/workload/main.tf` (lines 75 to 83):

```hcl
# Step 3: posture management.
module "posture" {
  source = "../../modules/posture"
  count  = var.enable_posture ? 1 : 0

  account_id    = var.workload_account_id
  region        = var.region
  force_destroy = var.force_destroy
}
```

The comment above the block says: "Step 3: posture management.". Step 3: **posture management** ([aws-config.md](aws-config.md), [aws-security-hub.md](aws-security-hub.md)). `count = var.enable_posture ? 1 : 0` creates it only when the variable is true.

The arguments:

- `source = "../../modules/posture"`: the folder of the module that is used here, `posture` ([terraform.md](terraform.md)).
- `count = var.enable_posture ? 1 : 0` makes zero or one copy of the module, depending on the condition (`condition ? 1 : 0`); the copy is addressed as `module.NAME[0]`.
- `account_id = var.workload_account_id` sets the module's input `account_id`, described there as "The account being assessed." The value is the input variable `workload_account_id`.
- `region = var.region` sets the module's input `region`, described there as "Region of the standards subscription." The value is the input variable `region`.
- `force_destroy = var.force_destroy` sets the module's input `force_destroy`, described there as "Delete the snapshot bucket with its objects on destroy. True only in a throwaway sandbox." The value is the input variable `force_destroy`.

From `infra/environments/workload/main.tf` (lines 85 to 92):

```hcl
# Step 4: the deliberate weakness for the drill, present only while the exercise runs.
module "drill" {
  source = "../../modules/drill"
  count  = var.enable_drill ? 1 : 0

  account_id        = var.workload_account_id
  enable_honeytoken = true
}
```

The comment above the block says: "Step 4: the deliberate weakness for the drill, present only while the exercise runs.". Step 4: the **deliberate weakness** for the drill, present only while the exercise runs ([aws-iam.md](aws-iam.md)). `count = var.enable_drill ? 1 : 0` creates it only when the variable is true, which is how the teardown removes it.

The arguments:

- `source = "../../modules/drill"`: the folder of the module that is used here, `drill` ([terraform.md](terraform.md)).
- `count = var.enable_drill ? 1 : 0` makes zero or one copy of the module, depending on the condition (`condition ? 1 : 0`); the copy is addressed as `module.NAME[0]`.
- `account_id = var.workload_account_id` sets the module's input `account_id`, described there as "The sandbox account." The value is the input variable `workload_account_id`.
- `enable_honeytoken = true` sets the module's input `enable_honeytoken`, described there as "Also create the honeytoken user (the lesson's second stretch goal)."

From `infra/environments/workload/main.tf` (lines 94 to 100):

```hcl
module "budget" {
  source = "../../modules/budget"

  name              = "detect-and-respond"
  email             = var.alert_email
  monthly_limit_usd = var.monthly_budget_usd
}
```

Creates the **cost budget** with its two email alerts ([aws-budgets.md](aws-budgets.md)).

The arguments:

- `source = "../../modules/budget"`: the folder of the module that is used here, `budget` ([terraform.md](terraform.md)).
- `name = "detect-and-respond"` sets the module's input `name`, described there as "Budget name."
- `email = var.alert_email` sets the module's input `email`, described there as "Address that receives the budget alerts." The value is the input variable `alert_email`.
- `monthly_limit_usd = var.monthly_budget_usd` sets the module's input `monthly_limit_usd`, described there as "Monthly cost limit in US dollars." The value is the input variable `monthly_budget_usd`.

##### `infra/environments/workload/outputs.tf`

From `infra/environments/workload/outputs.tf` (lines 1 to 8):

```hcl
output "alert_topics" {
  description = "Alert topic ARNs by Region; each needs its email subscription confirmed once."
  value = {
    global = module.alerting_global.topic_arn
    home   = module.alerting_home.topic_arn
    watch  = module.alerting_watch_ap_southeast_2.topic_arn
  }
}
```

Declares the **output** `alert_topics`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "Alert topic ARNs by Region; each needs its email subscription confirmed once." The `value` is a map from each place (`global`, `home`, `watch`) to the ARN of its alert topic, taken from the three alerting modules. The description reminds the reader that each topic needs its email subscription confirmed once.

From `infra/environments/workload/outputs.tf` (lines 10 to 17):

```hcl
output "rule_names" {
  description = "The rules deployed, by Region and detection id."
  value = {
    global = module.alerting_global.rule_names
    home   = module.alerting_home.rule_names
    watch  = module.alerting_watch_ap_southeast_2.rule_names
  }
}
```

Declares the **output** `rule_names`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "The rules deployed, by Region and detection id." The `value` is a map from each place to the names of the rules deployed there (an output of each alerting module), so a person can see which detection runs in which Region.

From `infra/environments/workload/outputs.tf` (lines 19 to 22):

```hcl
output "drill_role_arn" {
  description = "The over-privileged drill role, when the drill is enabled."
  value       = one(module.drill[*].role_arn)
}
```

Declares the **output** `drill_role_arn`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "The over-privileged drill role, when the drill is enabled." `value = one(module.drill[*].role_arn)` is the expression that computes it: `one(module.drill[*].role_arn)`.

From `infra/environments/workload/outputs.tf` (lines 24 to 27):

```hcl
output "drill_bucket" {
  description = "The bucket the attacker makes public, when the drill is enabled."
  value       = one(module.drill[*].bucket_name)
}
```

Declares the **output** `drill_bucket`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "The bucket the attacker makes public, when the drill is enabled." `value = one(module.drill[*].bucket_name)` is the expression that computes it: `one(module.drill[*].bucket_name)`.

##### `infra/environments/workload/plan-only.tfvars`

A `.tfvars` file gives **values to the variables** that the configuration declares: each line is `name = value`. Terraform reads a file passed with `-var-file` and any file whose name ends in `.auto.tfvars` without being asked.

From `infra/environments/workload/plan-only.tfvars` (lines 1 to 3):

```text
# Placeholders for `make plan`: no account, no credentials, nothing is read from or sent to a cloud. The drill and the
# honeytoken are on so the plan exercises every detection and the deliberate weakness (and the rules that fence it in).
plan_only                = true
```

The comment above the line says: "Placeholders for `make plan`: no account, no credentials, nothing is read from or sent to a cloud. The drill and the honeytoken are on so the plan exercises every detection and the deliberate weakness (and the rules that fence it in).". Sets the variable `plan_only` to `true`.

From `infra/environments/workload/plan-only.tfvars` (line 4):

```text
workload_account_id      = "000000000000"
```

Sets the variable `workload_account_id` to `"000000000000"`.

From `infra/environments/workload/plan-only.tfvars` (line 5):

```text
log_bucket_name          = "detect-archive-000000000001"
```

Sets the variable `log_bucket_name` to `"detect-archive-000000000001"`.

From `infra/environments/workload/plan-only.tfvars` (line 6):

```text
log_key_arn              = "arn:aws:kms:eu-west-1:000000000001:key/00000000-0000-4000-8000-000000000000"
```

Sets the variable `log_key_arn` to `"arn:aws:kms:eu-west-1:000000000001:key/00000000-0000-4000-8000-000000000000"`.

From `infra/environments/workload/plan-only.tfvars` (line 7):

```text
alert_email              = "alerts@example.com"
```

Sets the variable `alert_email` to `"alerts@example.com"`.

From `infra/environments/workload/plan-only.tfvars` (line 8):

```text
enable_drill             = true
```

Sets the variable `enable_drill` to `true`.

From `infra/environments/workload/plan-only.tfvars` (line 9):

```text
honeytoken_access_key_id = "AKIAPLANONLY00000000"
```

Sets the variable `honeytoken_access_key_id` to `"AKIAPLANONLY00000000"`.

##### `infra/environments/workload/sandbox.tfvars.example`

A `.tfvars` file gives **values to the variables** that the configuration declares: each line is `name = value`. Terraform reads a file passed with `-var-file` and any file whose name ends in `.auto.tfvars` without being asked.

From `infra/environments/workload/sandbox.tfvars.example` (lines 1 to 2):

```text
# Copy to sandbox.auto.tfvars (ignored by git) and fill in. scripts/02-deploy-workload.sh does this for you.
workload_account_id = "REPLACE_WITH_THE_WORKLOAD_ACCOUNT_ID"
```

The comment above the line says: "Copy to sandbox.auto.tfvars (ignored by git) and fill in. scripts/02-deploy-workload.sh does this for you.". Sets the variable `workload_account_id` to `"REPLACE_WITH_THE_WORKLOAD_ACCOUNT_ID"`.

From `infra/environments/workload/sandbox.tfvars.example` (line 3):

```text
log_bucket_name     = "REPLACE_WITH_OUTPUT_log_bucket_name_OF_THE_SECURITY_ENVIRONMENT"
```

Sets the variable `log_bucket_name` to `"REPLACE_WITH_OUTPUT_log_bucket_name_OF_THE_SECURITY_ENVIRONMENT"`.

From `infra/environments/workload/sandbox.tfvars.example` (line 4):

```text
log_key_arn         = "REPLACE_WITH_OUTPUT_log_key_arn_OF_THE_SECURITY_ENVIRONMENT"
```

Sets the variable `log_key_arn` to `"REPLACE_WITH_OUTPUT_log_key_arn_OF_THE_SECURITY_ENVIRONMENT"`.

From `infra/environments/workload/sandbox.tfvars.example` (line 5):

```text
alert_email         = "REPLACE_WITH_YOUR_ADDRESS"
```

Sets the variable `alert_email` to `"REPLACE_WITH_YOUR_ADDRESS"`.

From `infra/environments/workload/sandbox.tfvars.example` (line 6):

```text
force_destroy       = true # the sandbox is deleted the same day
```

Sets the variable `force_destroy` to `true`. The comment at the end of the line says: "the sandbox is deleted the same day".

From `infra/environments/workload/sandbox.tfvars.example` (line 7):

```text
enable_drill        = false # true only while the incident drill runs
```

Sets the variable `enable_drill` to `false`. The comment at the end of the line says: "true only while the incident drill runs".

From `infra/environments/workload/sandbox.tfvars.example` (line 8):

```text
# honeytoken_access_key_id = "AKIA..." # set after scripts/06-honeytoken.sh, then apply again to deploy D5
```

A comment for the reader: honeytoken_access_key_id = "AKIA..." # set after scripts/06-honeytoken.sh, then apply again to deploy D5

##### `infra/environments/workload/.terraform.lock.hcl`

From `infra/environments/workload/.terraform.lock.hcl` (lines 1 to 2):

```hcl
# This file is maintained automatically by "terraform init".
# Manual edits may be lost in future updates.
```

The two comment lines at the top say the file is maintained by `terraform init`.

From `infra/environments/workload/.terraform.lock.hcl` (lines 4 to 27):

```hcl
provider "registry.terraform.io/hashicorp/aws" {
  version     = "6.70.0"
  constraints = "~> 6.0"
  hashes = [
    "h1:HCr4MYgxlkFBOAeWKOoktNNzZaQX8ZZY4YTxmL/1V/Y=",
    "h1:L+05gOXA+kdYTtayIw0WxdaTp3JryZCMZpfrJVhoJA0=",
    "zh:068ca7ed4fc77e3d63d7fac54515a426a32f3dc143b55a6ad00963fe68289955",
    "zh:2d8c016b3809ab32f536b01bf2c98fcbdeb066b7b7e50f756ff6ff1e0b0539c7",
    "zh:450d960b60ea81268bd355600340787254f750d76e0075208a6fb903d7336b09",
    "zh:50447833cce21288ffc331342f9d83854e80515e2d86e8f5776a07ce18866b20",
    "zh:58acc041b080778ded75320e241ebcf6cf2ed145bede644b86a4784ce46086c6",
    "zh:7e899a44a1da95fefb1b04b231cf7cdb5871f482f60a710ede78bf25ac265724",
    "zh:8b141d13f4b84d7a47bc5a4855d0fc985191317b3249603532d4de03db5741c5",
    "zh:9035357f7d065ce8d35a9b05337977910683219c0f13fa09155d28f9b32e23a7",
    "zh:9b12af85486a96aedd8d7984b0ff811a4b42e3d88dad1a3fb4c0b580d04fa425",
    "zh:9ba0990a876d2641a185ca88263719afc4d5ac43533bdb147437f0073d2cd74d",
    "zh:a8773c7a02e1b3290df89351ee493fd8b74f807f92a7f69534e05901d4515761",
    "zh:ab0ebb298578eeeffe0fbf0a8b27ce99acd4419b7049272f1ab87e8c47229407",
    "zh:b88a3f22127bfb17604adc53e9bdb8ed0eddf4b9b77bf19871cba2e7fcd5b4a3",
    "zh:c7b1fb41e7f086b670f78932ede2b539903a8d71bac06f55f14a1a33d09a1ccf",
    "zh:df482bd93f51125f78feab7742aae1d7f22c7108ee2dc47787c4a1d611e6ccfd",
    "zh:fca401ffaa42d5f350d667123569de51a23de8c30b87ce0bd9d86fc80835fd4d",
  ]
}
```

`.terraform.lock.hcl` is written by `terraform init`; nobody edits it. It records the exact provider that was installed so that every machine gets the same one. `provider "registry.terraform.io/hashicorp/aws"` names the provider by its full registry address. `version = "6.70.0"` is the exact version installed. `constraints = "~> 6.0"` repeats the range the configuration allows. `hashes` is a list of **fingerprints** of the provider's files: each `h1:` entry is a hash of the provider package for one kind of machine, and each `zh:` entry is a hash of the downloaded archive; `terraform init` refuses to use a provider whose files do not match. The entries cover both macOS and Linux, so the CI installs the same bytes.

### Modules

A **module** is a folder of `.tf` files that is used like a function: the caller passes values to its variables and reads its outputs. Each module has the same four files: `versions.tf` (what it needs), `variables.tf` (its inputs), `main.tf` (what it creates) and `outputs.tf` (what it returns).

#### Module `infra/modules/alerting`

##### `infra/modules/alerting/versions.tf`

From `infra/modules/alerting/versions.tf` (lines 1 to 10):

```hcl
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

The `terraform` block holds settings about Terraform itself. `required_version = ">= 1.9"` makes Terraform refuse to run if it is older than 1.9. `required_providers` lists the provider plug-ins this folder needs: the entry `aws` has `source = "hashicorp/aws"` (the registry address of the AWS provider) and `version = "~> 6.0"`, meaning "6.0 or newer, but below 7" ([terraform-aws-provider.md](terraform-aws-provider.md)). Every module repeats the same block so it can be used and checked on its own.

##### `infra/modules/alerting/variables.tf`

From `infra/modules/alerting/variables.tf` (lines 1 to 4):

```hcl
variable "name" {
  description = "Name prefix of this Region's alerting, for example detect-global."
  type        = string
}
```

Declares the **input variable** `name`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Name prefix of this Region's alerting, for example detect-global." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/alerting/variables.tf` (lines 6 to 9):

```hcl
variable "region" {
  description = "The Region this instance runs in (the provider decides; used in names and policies)."
  type        = string
}
```

Declares the **input variable** `region`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The Region this instance runs in (the provider decides; used in names and policies)." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/alerting/variables.tf` (lines 11 to 14):

```hcl
variable "account_id" {
  description = "The account that owns the rules."
  type        = string
}
```

Declares the **input variable** `account_id`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The account that owns the rules." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/alerting/variables.tf` (lines 16 to 19):

```hcl
variable "alert_email" {
  description = "Address that receives the alerts."
  type        = string
}
```

Declares the **input variable** `alert_email`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Address that receives the alerts." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/alerting/variables.tf` (lines 21 to 24):

```hcl
variable "template" {
  description = "Alert text template from detections/alert-template.txt."
  type        = string
}
```

Declares the **input variable** `template`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Alert text template from detections/alert-template.txt." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/alerting/variables.tf` (lines 26 to 35):

```hcl
variable "detections" {
  description = "Detections to deploy here, by id: title, severity, first_step, pattern_json (the pattern as JSON text) and state."
  type = map(object({
    title        = string
    severity     = string
    first_step   = string
    pattern_json = string
    state        = string
  }))
}
```

Declares the **input variable** `detections`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Detections to deploy here, by id: title, severity, first_step, pattern_json (the pattern as JSON text) and state." `type = map(object({` restricts the value to the shape `map(object({`; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

##### `infra/modules/alerting/main.tf`

From `infra/modules/alerting/main.tf` (lines 1 to 16):

```hcl
# Alerting for one Region: a key, a topic that emails the responder, and one rule per detection deployed here. EventBridge
# only sees events in its own Region, which is why this module is instantiated once per Region that matters.
locals {
  # The text the responder receives. {..} fields are filled here, <..> fields by the rule's input transformer when it fires.
  alert_paths = {
    time     = "$.time"
    who      = "$.detail.userIdentity.arn"
    source   = "$.detail.eventSource"
    name     = "$.detail.eventName"
    params   = "$.detail.requestParameters"
    ip       = "$.detail.sourceIPAddress"
    agent    = "$.detail.userAgent"
    region   = "$.detail.awsRegion"
    event_id = "$.detail.eventID"
  }
}
```

The comment above the block says: "Alerting for one Region: a key, a topic that emails the responder, and one rule per detection deployed here. EventBridge only sees events in its own Region, which is why this module is instantiated once per Region that matters.". One named value, `alert_paths`, a map from field name to a **path** into the event: `time = "$.time"`, `who = "$.detail.userIdentity.arn"`, `source = "$.detail.eventSource"`, `name = "$.detail.eventName"`, `params = "$.detail.requestParameters"`, `ip = "$.detail.sourceIPAddress"`, `agent = "$.detail.userAgent"`, `region = "$.detail.awsRegion"` and `event_id = "$.detail.eventID"`. In a path, `$` is the whole event and each dot steps one level inside. The comment above says which fields are filled where: `{..}` fields by Terraform when it deploys, `<..>` fields by the rule's input transformer when it fires ([aws-eventbridge.md](aws-eventbridge.md)).

From `infra/modules/alerting/main.tf` (lines 18 to 34):

```hcl
module "key" {
  source = "../kms-key"

  alias       = "${var.name}-alerts"
  description = "Encrypts the alert topic in ${var.region}."
  account_id  = var.account_id
  region      = var.region

  statements = [{
    Sid       = "EventsPublishesEncryptedAlerts"
    Effect    = "Allow"
    Principal = { Service = "events.amazonaws.com" }
    Action    = ["kms:GenerateDataKey*", "kms:Decrypt"]
    Resource  = "*"
    Condition = { StringEquals = { "aws:SourceAccount" = var.account_id } }
  }]
}
```

Creates a key for this Region's alert topic ([aws-kms.md](aws-kms.md)). The one `statement`, `EventsPublishesEncryptedAlerts`, lets the event service (`Principal = { Service = "events.amazonaws.com" }`) use `kms:GenerateDataKey*` and `kms:Decrypt` on the key, only on behalf of this account (`Condition = { StringEquals = { "aws:SourceAccount" = var.account_id } }`), so the encrypted topic can receive alerts.

The arguments:

- `source = "../kms-key"`: the folder of the module that is used here, `kms-key` ([terraform.md](terraform.md)).
- `alias = "${var.name}-alerts"` sets the module's input `alias`, described there as "Alias of the key, without the alias/ prefix."
- `description = "Encrypts the alert topic in ${var.region}."` sets the module's input `description`, described there as "What the key protects."
- `account_id = var.account_id` sets the module's input `account_id`, described there as "Account that owns the key; its root administers the key." The value is the input variable `account_id`.
- `region = var.region` sets the module's input `region`, described there as "Region of the key." The value is the input variable `region`.
- `statements = [{ ...` sets the module's input `statements`, described there as "Key policy statements that grant use of the key, as policy-document statement objects." The value spans several lines and is explained after this list.

From `infra/modules/alerting/main.tf` (lines 36 to 39):

```hcl
resource "aws_sns_topic" "alerts" {
  name              = "${var.name}-alerts"
  kms_master_key_id = module.key.key_arn
}
```

Creates the **notification topic** ([aws-sns.md](aws-sns.md)). `name = "${var.name}-alerts"` labels it and `kms_master_key_id = module.key.key_arn` encrypts it at rest with the key above.

From `infra/modules/alerting/main.tf` (lines 41 to 55):

```hcl
resource "aws_sns_topic_policy" "alerts" {
  arn = aws_sns_topic.alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "EventsPublishes"
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.alerts.arn
      Condition = { StringEquals = { "aws:SourceAccount" = var.account_id } }
    }]
  })
}
```

Attaches the **topic policy**, written with `jsonencode`. `arn = aws_sns_topic.alerts.arn` names the topic. The one statement, `EventsPublishes`, allows `sns:Publish` on the topic to the event service (`Principal = { Service = "events.amazonaws.com" }`), only for requests made on behalf of this account (`aws:SourceAccount`). Nobody else may publish, so no one can send fake alerts.

From `infra/modules/alerting/main.tf` (lines 57 to 62):

```hcl
# The subscription stays pending until the address confirms it from the email AWS sends.
resource "aws_sns_topic_subscription" "responder" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
```

The comment above the block says: "The subscription stays pending until the address confirms it from the email AWS sends.". Subscribes the responder's address. The comment above says the subscription stays pending until the address confirms it from the email AWS sends. `topic_arn` names the topic, `protocol = "email"` chooses email delivery and `endpoint = var.alert_email` is the address.

From `infra/modules/alerting/main.tf` (lines 64 to 72):

```hcl
resource "aws_cloudwatch_event_rule" "detection" {
  for_each = var.detections

  name = "${var.name}-${lower(each.key)}"
  # The pattern is the detection file, unchanged, so what the tests replay is what runs.
  event_pattern = each.value.pattern_json
  description   = "${each.key}: ${each.value.title}"
  state         = each.value.state
}
```

Creates **one rule for each detection** given to this Region (`for_each = var.detections`; `each.key` is the detection's id such as `D1`) ([aws-eventbridge.md](aws-eventbridge.md)). `name = "${var.name}-${lower(each.key)}"` builds a name such as `detect-global-d1` (`lower` makes the id lower case). The comment says the pattern is the detection file, unchanged, so what the tests replay is what runs: `event_pattern = each.value.pattern_json`. `description` is a label. `state = each.value.state` is `ENABLED`, or the wider state for a detection that needs read-only calls.

From `infra/modules/alerting/main.tf` (lines 74 to 87):

```hcl
resource "aws_cloudwatch_event_target" "alert" {
  for_each = var.detections

  rule = aws_cloudwatch_event_rule.detection[each.key].name
  arn  = aws_sns_topic.alerts.arn

  input_transformer {
    input_paths = local.alert_paths
    input_template = format("\"%s\"", replace(
      replace(replace(replace(replace(var.template, "{id}", each.key), "{title}", each.value.title), "{severity}", each.value.severity), "{first_step}", each.value.first_step),
      "\n", "\\n"
    ))
  }
}
```

Connects each rule to the topic (`for_each = var.detections` again). `rule = aws_cloudwatch_event_rule.detection[each.key].name` names the rule of the same detection (square brackets pick the entry for that key). `arn = aws_sns_topic.alerts.arn` is where the matching events go. The nested `input_transformer` block reshapes each event before it is delivered: `input_paths = local.alert_paths` extracts the named fields from the event, and `input_template = format("\"%s\"", replace(...))` is the message. The template is the alert text from `detections/alert-template.txt` (variable `template`) in which Terraform replaces `{id}`, `{title}`, `{severity}` and `{first_step}` (one `replace(text, old, new)` after another), then `replace(..., "\n", "\\n")` turns line breaks into the two characters `\n`, and `format("\"%s\"", text)` wraps the whole in quotation marks, because the message must itself be a JSON string. At run time the service replaces the `<time>`, `<who>` and the other angle-bracket fields with the extracted values.

##### `infra/modules/alerting/outputs.tf`

From `infra/modules/alerting/outputs.tf` (lines 1 to 4):

```hcl
output "topic_arn" {
  description = "ARN of the alert topic."
  value       = aws_sns_topic.alerts.arn
}
```

Declares the **output** `topic_arn`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "ARN of the alert topic." `value = aws_sns_topic.alerts.arn` is the attribute `arn` of the resource `aws_sns_topic.alerts` created by this module.

From `infra/modules/alerting/outputs.tf` (lines 6 to 9):

```hcl
output "rule_names" {
  description = "Names of the rules, by detection id."
  value       = { for id, rule in aws_cloudwatch_event_rule.detection : id => rule.name }
}
```

Declares the **output** `rule_names`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "Names of the rules, by detection id." `value = { for id, rule in aws_cloudwatch_event_rule.detection : id => rule.name }` is the expression that computes it: `{ for id, rule in aws_cloudwatch_event_rule.detection : id => rule.name }`.

#### Module `infra/modules/budget`

##### `infra/modules/budget/versions.tf`

From `infra/modules/budget/versions.tf` (lines 1 to 10):

```hcl
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

The `terraform` block holds settings about Terraform itself. `required_version = ">= 1.9"` makes Terraform refuse to run if it is older than 1.9. `required_providers` lists the provider plug-ins this folder needs: the entry `aws` has `source = "hashicorp/aws"` (the registry address of the AWS provider) and `version = "~> 6.0"`, meaning "6.0 or newer, but below 7" ([terraform-aws-provider.md](terraform-aws-provider.md)). Every module repeats the same block so it can be used and checked on its own.

##### `infra/modules/budget/variables.tf`

From `infra/modules/budget/variables.tf` (lines 1 to 4):

```hcl
variable "name" {
  description = "Budget name."
  type        = string
}
```

Declares the **input variable** `name`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Budget name." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/budget/variables.tf` (lines 6 to 9):

```hcl
variable "email" {
  description = "Address that receives the budget alerts."
  type        = string
}
```

Declares the **input variable** `email`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Address that receives the budget alerts." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/budget/variables.tf` (lines 11 to 15):

```hcl
variable "monthly_limit_usd" {
  description = "Monthly cost limit in US dollars."
  type        = number
  default     = 10
}
```

Declares the **input variable** `monthly_limit_usd`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Monthly cost limit in US dollars." `type = number` restricts the value to a number; Terraform refuses any other kind of value. `default = 10` is the value used when the caller supplies none, which makes the variable optional.

##### `infra/modules/budget/main.tf`

From `infra/modules/budget/main.tf` (lines 1 to 23):

```hcl
resource "aws_budgets_budget" "this" {
  name         = var.name
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.email]
  }
}
```

Creates a **cost budget** ([aws-budgets.md](aws-budgets.md)). `name = var.name` labels it. `budget_type = "COST"` measures money (not usage). `limit_amount = tostring(var.monthly_limit_usd)` is the limit; the service wants text, so `tostring(...)` converts the number. `limit_unit = "USD"` is the currency. `time_unit = "MONTHLY"` makes the limit reset every month. The two `notification` blocks that follow are the alerts, explained below.

The first `notification` block: `comparison_operator = "GREATER_THAN"` and `threshold = 80` with `threshold_type = "PERCENTAGE"` mean "above 80 percent of the limit"; `notification_type = "ACTUAL"` uses the money already spent; `subscriber_email_addresses = [var.email]` is the list of addresses to email. The second block is the same with `notification_type = "FORECASTED"` and `threshold = 100`: email when the service **predicts** that the month will exceed the whole limit.

##### `infra/modules/budget/outputs.tf`

From `infra/modules/budget/outputs.tf` (lines 1 to 4):

```hcl
output "name" {
  description = "Budget name."
  value       = aws_budgets_budget.this.name
}
```

Declares the **output** `name`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "Budget name." `value = aws_budgets_budget.this.name` is the attribute `name` of the resource `aws_budgets_budget.this` created by this module.

#### Module `infra/modules/central-trail`

##### `infra/modules/central-trail/versions.tf`

From `infra/modules/central-trail/versions.tf` (lines 1 to 10):

```hcl
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

The `terraform` block holds settings about Terraform itself. `required_version = ">= 1.9"` makes Terraform refuse to run if it is older than 1.9. `required_providers` lists the provider plug-ins this folder needs: the entry `aws` has `source = "hashicorp/aws"` (the registry address of the AWS provider) and `version = "~> 6.0"`, meaning "6.0 or newer, but below 7" ([terraform-aws-provider.md](terraform-aws-provider.md)). Every module repeats the same block so it can be used and checked on its own.

##### `infra/modules/central-trail/variables.tf`

From `infra/modules/central-trail/variables.tf` (lines 1 to 4):

```hcl
variable "name" {
  description = "Trail name; the archive bucket policy admits this trail only."
  type        = string
}
```

Declares the **input variable** `name`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Trail name; the archive bucket policy admits this trail only." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/central-trail/variables.tf` (lines 6 to 9):

```hcl
variable "log_bucket_name" {
  description = "Archive bucket in the security account."
  type        = string
}
```

Declares the **input variable** `log_bucket_name`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Archive bucket in the security account." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/central-trail/variables.tf` (lines 11 to 14):

```hcl
variable "log_key_arn" {
  description = "ARN of the archive key in the security account."
  type        = string
}
```

Declares the **input variable** `log_key_arn`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "ARN of the archive key in the security account." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

##### `infra/modules/central-trail/main.tf`

From `infra/modules/central-trail/main.tf` (lines 1 to 18):

```hcl
# The trail in the workload account. It writes to a bucket and a key in the security account, with log file validation,
# so the evidence survives a compromise of this account.
resource "aws_cloudtrail" "central" {
  #checkov:skip=CKV_AWS_252:Alerts come from the EventBridge rules in the alerting modules, which see the same events sooner.
  #checkov:skip=CKV2_AWS_10:The archive in the security account is the record; streaming to CloudWatch Logs is not part of this lesson.
  name                          = var.name
  s3_bucket_name                = var.log_bucket_name
  kms_key_id                    = var.log_key_arn
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true
  enable_logging                = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }
}
```

The comment above the block says: "The trail in the workload account. It writes to a bucket and a key in the security account, with log file validation, so the evidence survives a compromise of this account.". Creates the **trail** in the workload account ([aws-cloudtrail.md](aws-cloudtrail.md)). The comment above says it writes to a bucket and a key in the security account, with log file validation, so the evidence survives a compromise of this account. `name = var.name` labels it, `s3_bucket_name = var.log_bucket_name` and `kms_key_id = var.log_key_arn` name the bucket and the key in the other account, `is_multi_region_trail = true` records every region, `include_global_service_events = true` also records global services, `enable_log_file_validation = true` writes digest files, `enable_logging = true` switches recording on. The nested `event_selector` with `read_write_type = "All"` and `include_management_events = true` records every control-plane call, reads and writes.

- `#checkov:skip=CKV_AWS_252:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_252` for this resource only. The stated reason is: "Alerts come from the EventBridge rules in the alerting modules, which see the same events sooner.".
- `#checkov:skip=CKV2_AWS_10:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV2_AWS_10` for this resource only. The stated reason is: "The archive in the security account is the record; streaming to CloudWatch Logs is not part of this lesson.".

##### `infra/modules/central-trail/outputs.tf`

From `infra/modules/central-trail/outputs.tf` (lines 1 to 4):

```hcl
output "name" {
  description = "Trail name."
  value       = aws_cloudtrail.central.name
}
```

Declares the **output** `name`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "Trail name." `value = aws_cloudtrail.central.name` is the attribute `name` of the resource `aws_cloudtrail.central` created by this module.

#### Module `infra/modules/drill`

##### `infra/modules/drill/versions.tf`

From `infra/modules/drill/versions.tf` (lines 1 to 10):

```hcl
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

The `terraform` block holds settings about Terraform itself. `required_version = ">= 1.9"` makes Terraform refuse to run if it is older than 1.9. `required_providers` lists the provider plug-ins this folder needs: the entry `aws` has `source = "hashicorp/aws"` (the registry address of the AWS provider) and `version = "~> 6.0"`, meaning "6.0 or newer, but below 7" ([terraform-aws-provider.md](terraform-aws-provider.md)). Every module repeats the same block so it can be used and checked on its own.

##### `infra/modules/drill/variables.tf`

From `infra/modules/drill/variables.tf` (lines 1 to 4):

```hcl
variable "account_id" {
  description = "The sandbox account."
  type        = string
}
```

Declares the **input variable** `account_id`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The sandbox account." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/drill/variables.tf` (lines 6 to 10):

```hcl
variable "user_name" {
  description = "The drill user that holds the leaked key."
  type        = string
  default     = "drill-user"
}
```

Declares the **input variable** `user_name`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The drill user that holds the leaked key." `type = string` restricts the value to text; Terraform refuses any other kind of value. `default = "drill-user"` is the value used when the caller supplies none, which makes the variable optional.

From `infra/modules/drill/variables.tf` (lines 12 to 16):

```hcl
variable "role_name" {
  description = "The over-privileged role the drill user can assume."
  type        = string
  default     = "drill-broad-role"
}
```

Declares the **input variable** `role_name`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The over-privileged role the drill user can assume." `type = string` restricts the value to text; Terraform refuses any other kind of value. `default = "drill-broad-role"` is the value used when the caller supplies none, which makes the variable optional.

From `infra/modules/drill/variables.tf` (lines 18 to 22):

```hcl
variable "bucket_prefix" {
  description = "Prefix of the drill bucket the attacker makes public."
  type        = string
  default     = "drill-data"
}
```

Declares the **input variable** `bucket_prefix`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Prefix of the drill bucket the attacker makes public." `type = string` restricts the value to text; Terraform refuses any other kind of value. `default = "drill-data"` is the value used when the caller supplies none, which makes the variable optional.

From `infra/modules/drill/variables.tf` (lines 24 to 28):

```hcl
variable "enable_honeytoken" {
  description = "Also create the honeytoken user (the lesson's second stretch goal)."
  type        = bool
  default     = false
}
```

Declares the **input variable** `enable_honeytoken`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Also create the honeytoken user (the lesson's second stretch goal)." `type = bool` restricts the value to true or false; Terraform refuses any other kind of value. `default = false` is the value used when the caller supplies none, which makes the variable optional.

##### `infra/modules/drill/main.tf`

From `infra/modules/drill/main.tf` (lines 1 to 6):

```hcl
# The deliberate weakness the incident drill needs, and nothing else. It exists only while the exercise runs: the
# environment creates this module only when enable_drill is true, and `make down` removes it. The drill user's access key
# is NOT created here (it would sit in the state); scripts/03-drill-setup.sh creates it and prints nothing secret.
locals {
  user_arn = "arn:aws:iam::${var.account_id}:user/${var.user_name}"
}
```

The comment above the block says: "The deliberate weakness the incident drill needs, and nothing else. It exists only while the exercise runs: the environment creates this module only when enable_drill is true, and `make down` removes it. The drill user's access key is NOT created here (it would sit in the state); scripts/03-drill-setup.sh creates it and prints nothing secret.". One named value, `user_arn`, the drill user's full name **built from text** (`arn:aws:iam::<account>:user/<user name>`), so the policies below can name the user before it exists.

From `infra/modules/drill/main.tf` (lines 8 to 12):

```hcl
resource "aws_iam_user" "drill" {
  #checkov:skip=CKV_AWS_273:The drill needs a long-lived user key: that is the leaked credential the exercise detects.
  name = var.user_name
  tags = { purpose = "incident-drill" }
}
```

Creates the **drill user**, the account whose long-lived key is "leaked" in the exercise. `name = var.user_name` and `tags = { purpose = "incident-drill" }` label it; the tag lets the teardown and the policy rules find it. The key itself is **not** created here: it would sit in the state file ([aws-iam.md](aws-iam.md)).

- `#checkov:skip=CKV_AWS_273:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_273` for this resource only. The stated reason is: "The drill needs a long-lived user key: that is the leaked credential the exercise detects.".

From `infra/modules/drill/main.tf` (lines 14 to 29):

```hcl
# The user can do one thing: assume the broad role.
resource "aws_iam_user_policy" "assume_broad_role" {
  #checkov:skip=CKV_AWS_40:The drill user is a deliberate exception; it exists only while the drill runs.
  name = "assume-the-drill-role"
  user = aws_iam_user.drill.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "AssumeOnlyTheDrillRole"
      Effect   = "Allow"
      Action   = "sts:AssumeRole"
      Resource = "arn:aws:iam::${var.account_id}:role/${var.role_name}"
    }]
  })
}
```

The comment above the block says: "The user can do one thing: assume the broad role.". Gives the user exactly one permission. `name`, `user` identify the policy and the user. The statement `AssumeOnlyTheDrillRole` allows `sts:AssumeRole` on `Resource = "arn:aws:iam::<account>:role/<role name>"`, the one broad role. Nothing else. The comment above this resource says the user can do one thing.

- `#checkov:skip=CKV_AWS_40:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_40` for this resource only. The stated reason is: "The drill user is a deliberate exception; it exists only while the drill runs.".

From `infra/modules/drill/main.tf` (lines 31 to 46):

```hcl
resource "aws_iam_role" "broad" {
  name = var.role_name
  tags = { purpose = "incident-drill" }

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "OnlyTheDrillUserAssumes"
      Effect    = "Allow"
      Principal = { AWS = local.user_arn }
      Action    = "sts:AssumeRole"
    }]
  })

  depends_on = [aws_iam_user.drill]
}
```

Creates the **broad role**, the deliberately over-privileged identity that the attacker uses. `name = var.role_name` and the `purpose` tag label it. The trust policy, `assume_role_policy`, has one statement, `OnlyTheDrillUserAssumes`: `Principal = { AWS = local.user_arn }`, `Action = "sts:AssumeRole"`, so only the drill user can take the role. `depends_on = [aws_iam_user.drill]` creates the user first, since a trust policy that names a user which does not exist yet is refused.

From `infra/modules/drill/main.tf` (lines 48 to 52):

```hcl
# The weakness: far more than the role needs.
resource "aws_iam_role_policy_attachment" "power_user" {
  role       = aws_iam_role.broad.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}
```

The comment above the block says: "The weakness: far more than the role needs.". Attaches AWS's managed policy `PowerUserAccess` to the role (`role` names the role, `policy_arn` the policy). The comment above it says: this is the weakness, far more than the role needs. `PowerUserAccess` allows nearly everything except managing IAM.

From `infra/modules/drill/main.tf` (lines 54 to 69):

```hcl
# PowerUserAccess leaves out IAM, so the role is also allowed to mint a key for the drill user. That is what lets detection
# D1 fire on a call that succeeds, as in the lesson's timeline.
resource "aws_iam_role_policy" "mint_a_key_for_the_drill_user" {
  name = "create-access-key-for-the-drill-user"
  role = aws_iam_role.broad.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "CreateAKeyForTheDrillUserOnly"
      Effect   = "Allow"
      Action   = "iam:CreateAccessKey"
      Resource = local.user_arn
    }]
  })
}
```

The comment above the block says: "PowerUserAccess leaves out IAM, so the role is also allowed to mint a key for the drill user. That is what lets detection D1 fire on a call that succeeds, as in the lesson's timeline.". An extra inline policy on the broad role. The comment above explains: `PowerUserAccess` leaves out IAM, so the role is also allowed to mint a key for the drill user, which is what lets detection D1 fire on a call that **succeeds**. The statement `CreateAKeyForTheDrillUserOnly` allows `iam:CreateAccessKey` on `Resource = local.user_arn` only.

From `infra/modules/drill/main.tf` (lines 71 to 83):

```hcl
# The target the attacker makes public. Block Public Access is off and ACLs are on: also deliberate, also temporary.
resource "aws_s3_bucket" "data" {
  #checkov:skip=CKV_AWS_18:Throwaway drill bucket.
  #checkov:skip=CKV_AWS_21:Throwaway drill bucket; versioning adds nothing to the drill.
  #checkov:skip=CKV_AWS_144:Throwaway drill bucket.
  #checkov:skip=CKV_AWS_145:Throwaway drill bucket holding no data.
  #checkov:skip=CKV2_AWS_6:Block Public Access is off on purpose: the drill makes this bucket public.
  #checkov:skip=CKV2_AWS_61:Throwaway drill bucket.
  #checkov:skip=CKV2_AWS_62:Throwaway drill bucket.
  bucket        = "${var.bucket_prefix}-${var.account_id}"
  force_destroy = true
  tags          = { purpose = "incident-drill" }
}
```

The comment above the block says: "The target the attacker makes public. Block Public Access is off and ACLs are on: also deliberate, also temporary.". Creates the **target bucket** that the attacker makes public ([aws-s3.md](aws-s3.md)). `bucket = "${var.bucket_prefix}-${var.account_id}"` is its name, `force_destroy = true` lets teardown remove it, and `tags` labels it. The skip comments say the scanner checks do not apply to this throwaway bucket.

- `#checkov:skip=CKV_AWS_18:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_18` for this resource only. The stated reason is: "Throwaway drill bucket.".
- `#checkov:skip=CKV_AWS_21:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_21` for this resource only. The stated reason is: "Throwaway drill bucket; versioning adds nothing to the drill.".
- `#checkov:skip=CKV_AWS_144:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_144` for this resource only. The stated reason is: "Throwaway drill bucket.".
- `#checkov:skip=CKV_AWS_145:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_145` for this resource only. The stated reason is: "Throwaway drill bucket holding no data.".
- `#checkov:skip=CKV2_AWS_6:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV2_AWS_6` for this resource only. The stated reason is: "Block Public Access is off on purpose: the drill makes this bucket public.".
- `#checkov:skip=CKV2_AWS_61:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV2_AWS_61` for this resource only. The stated reason is: "Throwaway drill bucket.".
- `#checkov:skip=CKV2_AWS_62:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV2_AWS_62` for this resource only. The stated reason is: "Throwaway drill bucket.".

From `infra/modules/drill/main.tf` (lines 85 to 92):

```hcl
resource "aws_s3_bucket_ownership_controls" "data" {
  #checkov:skip=CKV2_AWS_65:ACLs stay enabled on purpose: the drill makes the bucket public with an ACL.
  bucket = aws_s3_bucket.data.bucket

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}
```

Sets the bucket's object ownership to `BucketOwnerPreferred`, which **keeps ACLs working**. The skip comment says why: the drill makes the bucket public with an ACL, and with `BucketOwnerEnforced` that would be impossible.

- `#checkov:skip=CKV2_AWS_65:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV2_AWS_65` for this resource only. The stated reason is: "ACLs stay enabled on purpose: the drill makes the bucket public with an ACL.".

From `infra/modules/drill/main.tf` (lines 94 to 104):

```hcl
resource "aws_s3_bucket_public_access_block" "data" {
  #checkov:skip=CKV_AWS_53:Deliberate drill weakness.
  #checkov:skip=CKV_AWS_54:Deliberate drill weakness.
  #checkov:skip=CKV_AWS_55:Deliberate drill weakness.
  #checkov:skip=CKV_AWS_56:Deliberate drill weakness.
  bucket                  = aws_s3_bucket.data.bucket
  block_public_acls       = false
  ignore_public_acls      = false
  block_public_policy     = false
  restrict_public_buckets = false
}
```

Sets all four Block Public Access switches to `false`, the opposite of every other bucket in the repository: `block_public_acls`, `ignore_public_acls`, `block_public_policy`, `restrict_public_buckets`. The skip comments mark each as a deliberate drill weakness. The OPA rule allows this only inside the drill module ([opa-rego.md](opa-rego.md)).

- `#checkov:skip=CKV_AWS_53:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_53` for this resource only. The stated reason is: "Deliberate drill weakness.".
- `#checkov:skip=CKV_AWS_54:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_54` for this resource only. The stated reason is: "Deliberate drill weakness.".
- `#checkov:skip=CKV_AWS_55:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_55` for this resource only. The stated reason is: "Deliberate drill weakness.".
- `#checkov:skip=CKV_AWS_56:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_56` for this resource only. The stated reason is: "Deliberate drill weakness.".

From `infra/modules/drill/main.tf` (lines 106 to 114):

```hcl
# The honeytoken: a user with no permissions at all. Any use of its key, allowed or denied, is an intruder. The key is created
# by scripts/06-honeytoken.sh and its id is passed to the environment so detection D5 can watch for it.
resource "aws_iam_user" "honeytoken" {
  #checkov:skip=CKV_AWS_273:A honeytoken is a user nobody should ever sign in as; its key is bait.
  count = var.enable_honeytoken ? 1 : 0

  name = "honeytoken-svc"
  tags = { purpose = "honeytoken" }
}
```

The comment above the block says: "The honeytoken: a user with no permissions at all. Any use of its key, allowed or denied, is an intruder. The key is created by scripts/06-honeytoken.sh and its id is passed to the environment so detection D5 can watch for it.". Creates the **honeytoken user**, the bait. The comment above explains: a user with no permissions at all; any use of its key, allowed or denied, is an intruder; the key is created by `scripts/06-honeytoken.sh` and its id is passed to the environment so detection D5 can watch for it. `count = var.enable_honeytoken ? 1 : 0` creates the user only when the variable is true. `name = "honeytoken-svc"` and `tags = { purpose = "honeytoken" }` label it.

- `#checkov:skip=CKV_AWS_273:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_273` for this resource only. The stated reason is: "A honeytoken is a user nobody should ever sign in as; its key is bait.".

##### `infra/modules/drill/outputs.tf`

From `infra/modules/drill/outputs.tf` (lines 1 to 4):

```hcl
output "role_arn" {
  description = "ARN of the over-privileged role."
  value       = aws_iam_role.broad.arn
}
```

Declares the **output** `role_arn`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "ARN of the over-privileged role." `value = aws_iam_role.broad.arn` is the attribute `arn` of the resource `aws_iam_role.broad` created by this module.

From `infra/modules/drill/outputs.tf` (lines 6 to 9):

```hcl
output "bucket_name" {
  description = "The drill bucket."
  value       = aws_s3_bucket.data.bucket
}
```

Declares the **output** `bucket_name`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "The drill bucket." `value = aws_s3_bucket.data.bucket` is the attribute `bucket` of the resource `aws_s3_bucket.data` created by this module.

#### Module `infra/modules/kms-key`

##### `infra/modules/kms-key/versions.tf`

From `infra/modules/kms-key/versions.tf` (lines 1 to 10):

```hcl
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

The `terraform` block holds settings about Terraform itself. `required_version = ">= 1.9"` makes Terraform refuse to run if it is older than 1.9. `required_providers` lists the provider plug-ins this folder needs: the entry `aws` has `source = "hashicorp/aws"` (the registry address of the AWS provider) and `version = "~> 6.0"`, meaning "6.0 or newer, but below 7" ([terraform-aws-provider.md](terraform-aws-provider.md)). Every module repeats the same block so it can be used and checked on its own.

##### `infra/modules/kms-key/variables.tf`

From `infra/modules/kms-key/variables.tf` (lines 1 to 4):

```hcl
variable "alias" {
  description = "Alias of the key, without the alias/ prefix."
  type        = string
}
```

Declares the **input variable** `alias`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Alias of the key, without the alias/ prefix." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/kms-key/variables.tf` (lines 6 to 9):

```hcl
variable "description" {
  description = "What the key protects."
  type        = string
}
```

Declares the **input variable** `description`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "What the key protects." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/kms-key/variables.tf` (lines 11 to 14):

```hcl
variable "account_id" {
  description = "Account that owns the key; its root administers the key."
  type        = string
}
```

Declares the **input variable** `account_id`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Account that owns the key; its root administers the key." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/kms-key/variables.tf` (lines 16 to 19):

```hcl
variable "region" {
  description = "Region of the key."
  type        = string
}
```

Declares the **input variable** `region`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Region of the key." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/kms-key/variables.tf` (lines 21 to 25):

```hcl
variable "statements" {
  description = "Key policy statements that grant use of the key, as policy-document statement objects."
  type        = any
  default     = []
}
```

Declares the **input variable** `statements`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Key policy statements that grant use of the key, as policy-document statement objects." `type = any` restricts the value to the shape `any`; Terraform refuses any other kind of value. `default = []` is the value used when the caller supplies none, which makes the variable optional.

From `infra/modules/kms-key/variables.tf` (lines 27 to 31):

```hcl
variable "deletion_window_in_days" {
  description = "Waiting period before a scheduled deletion takes effect (7 to 30)."
  type        = number
  default     = 7
}
```

Declares the **input variable** `deletion_window_in_days`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Waiting period before a scheduled deletion takes effect (7 to 30)." `type = number` restricts the value to a number; Terraform refuses any other kind of value. `default = 7` is the value used when the caller supplies none, which makes the variable optional.

##### `infra/modules/kms-key/main.tf`

From `infra/modules/kms-key/main.tf` (lines 1 to 17):

```hcl
locals {
  # Management only. The account root is deliberately not given kms:Decrypt or kms:Encrypt, so an IAM policy cannot
  # reach the data; only the principals in `statements` can use the key.
  administration_actions = [
    "kms:Create*", "kms:Describe*", "kms:Enable*", "kms:List*", "kms:Put*", "kms:Update*", "kms:Revoke*",
    "kms:Disable*", "kms:Get*", "kms:Delete*", "kms:TagResource", "kms:UntagResource",
    "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion",
  ]

  administration = {
    Sid       = "AccountAdministersKey"
    Effect    = "Allow"
    Principal = { AWS = "arn:aws:iam::${var.account_id}:root" }
    Action    = local.administration_actions
    Resource  = "*"
  }
}
```

The `locals` block defines named values used inside this module. `administration_actions` is the list of key **management** actions the account is allowed: `kms:Create*`, `kms:Describe*`, `kms:Enable*`, `kms:List*`, `kms:Put*`, `kms:Update*`, `kms:Revoke*`, `kms:Disable*`, `kms:Get*`, `kms:Delete*`, `kms:TagResource`, `kms:UntagResource`, `kms:ScheduleKeyDeletion` and `kms:CancelKeyDeletion`. The `*` is a wildcard: `kms:Create*` means every action whose name starts with `Create`. The data actions (`Encrypt`, `Decrypt`, `GenerateDataKey`) are **not** in the list, which is the point of the comment. `administration` is one policy statement built from it: `Sid` is its name, `Effect = "Allow"`, `Principal = { AWS = "arn:aws:iam::<account>:root" }` is the account itself (the root principal stands for "this account's own IAM policies"), `Action` is the list above and `Resource = "*"` means "this key" (a key policy is attached to one key). ([aws-kms.md](aws-kms.md))

From `infra/modules/kms-key/main.tf` (lines 19 to 24):

```hcl
resource "aws_kms_key" "this" {
  description             = var.description
  enable_key_rotation     = true
  deletion_window_in_days = var.deletion_window_in_days
  policy                  = jsonencode({ Version = "2012-10-17", Statement = concat([local.administration], var.statements) })
}
```

Creates the **key**. `description = var.description` is a label. `enable_key_rotation = true` makes the service replace the key material every year automatically. `deletion_window_in_days = var.deletion_window_in_days` is the waiting period between "schedule deletion" and the key's disappearance (7 to 30 days), because deleting a key makes everything it encrypted unreadable. `policy = jsonencode({ Version = ..., Statement = concat([local.administration], var.statements) })` writes the key policy as JSON: `concat(a, b)` joins two lists, so the key gets the shared administration statement followed by whatever statements the caller passes in (the caller decides who may *use* the key) ([aws-kms.md](aws-kms.md)).

From `infra/modules/kms-key/main.tf` (lines 26 to 29):

```hcl
resource "aws_kms_alias" "this" {
  name          = "alias/${var.alias}"
  target_key_id = aws_kms_key.this.key_id
}
```

Creates an **alias**, a friendly name for the key. `name = "alias/${var.alias}"` must start with `alias/`; `${...}` pastes the variable into the text. `target_key_id = aws_kms_key.this.key_id` points the alias at the key created above. Buckets and scripts use the alias, so the key can be replaced without changing them.

##### `infra/modules/kms-key/outputs.tf`

From `infra/modules/kms-key/outputs.tf` (lines 1 to 4):

```hcl
output "key_arn" {
  description = "ARN of the key."
  value       = aws_kms_key.this.arn
}
```

Declares the **output** `key_arn`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "ARN of the key." `value = aws_kms_key.this.arn` is the attribute `arn` of the resource `aws_kms_key.this` created by this module.

From `infra/modules/kms-key/outputs.tf` (lines 6 to 9):

```hcl
output "alias_arn" {
  description = "ARN of the alias, built from names so it is known at plan time. Callers that use it must depend on this module."
  value       = "arn:aws:kms:${var.region}:${var.account_id}:alias/${var.alias}"
}
```

Declares the **output** `alias_arn`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "ARN of the alias, built from names so it is known at plan time. Callers that use it must depend on this module." `value = "arn:aws:kms:${var.region}:${var.account_id}:alias/${var.alias}"` is the expression that computes it: `"arn:aws:kms:${var.region}:${var.account_id}:alias/${var.alias}"`.

#### Module `infra/modules/log-archive`

##### `infra/modules/log-archive/versions.tf`

From `infra/modules/log-archive/versions.tf` (lines 1 to 10):

```hcl
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

The `terraform` block holds settings about Terraform itself. `required_version = ">= 1.9"` makes Terraform refuse to run if it is older than 1.9. `required_providers` lists the provider plug-ins this folder needs: the entry `aws` has `source = "hashicorp/aws"` (the registry address of the AWS provider) and `version = "~> 6.0"`, meaning "6.0 or newer, but below 7" ([terraform-aws-provider.md](terraform-aws-provider.md)). Every module repeats the same block so it can be used and checked on its own.

##### `infra/modules/log-archive/variables.tf`

From `infra/modules/log-archive/variables.tf` (lines 1 to 4):

```hcl
variable "bucket_name" {
  description = "Name of the archive bucket, in the security account."
  type        = string
}
```

Declares the **input variable** `bucket_name`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Name of the archive bucket, in the security account." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/log-archive/variables.tf` (lines 6 to 9):

```hcl
variable "workload_account_id" {
  description = "The account whose trail delivers here; only its trail may write."
  type        = string
}
```

Declares the **input variable** `workload_account_id`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The account whose trail delivers here; only its trail may write." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/log-archive/variables.tf` (lines 11 to 14):

```hcl
variable "region" {
  description = "Home region of the workload account's trail."
  type        = string
}
```

Declares the **input variable** `region`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Home region of the workload account's trail." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/log-archive/variables.tf` (lines 16 to 19):

```hcl
variable "trail_name" {
  description = "Name of the workload account's trail; the bucket policy admits that trail only."
  type        = string
}
```

Declares the **input variable** `trail_name`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Name of the workload account's trail; the bucket policy admits that trail only." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/log-archive/variables.tf` (lines 21 to 24):

```hcl
variable "key_alias_arn" {
  description = "Alias ARN of the key that encrypts the archive."
  type        = string
}
```

Declares the **input variable** `key_alias_arn`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Alias ARN of the key that encrypts the archive." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/log-archive/variables.tf` (lines 26 to 35):

```hcl
variable "retention_days" {
  description = "Compliance-mode retention. Nobody can shorten it, so the exercise uses 1."
  type        = number
  default     = 1

  validation {
    condition     = var.retention_days >= 1
    error_message = "retention_days must be at least 1."
  }
}
```

Declares the **input variable** `retention_days`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Compliance-mode retention. Nobody can shorten it, so the exercise uses 1." `type = number` restricts the value to a number; Terraform refuses any other kind of value. `default = 1` is the value used when the caller supplies none, which makes the variable optional. The `validation` block rejects a bad value before anything is planned: the `condition` `var.retention_days >= 1` must be true, otherwise Terraform stops with the `error_message` "retention_days must be at least 1.". `can(regex(...))` is true when the text matches the pattern.

From `infra/modules/log-archive/variables.tf` (lines 37 to 41):

```hcl
variable "expire_days" {
  description = "Days after which log files expire. Must be longer than retention_days."
  type        = number
  default     = 2
}
```

Declares the **input variable** `expire_days`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Days after which log files expire. Must be longer than retention_days." `type = number` restricts the value to a number; Terraform refuses any other kind of value. `default = 2` is the value used when the caller supplies none, which makes the variable optional.

##### `infra/modules/log-archive/main.tf`

From `infra/modules/log-archive/main.tf` (lines 1 to 6):

```hcl
# The central, tamper-resistant log store. It lives in a separate account (the security account): an administrator of the
# workload account has no rights here. Object Lock in compliance mode means even this account's owner cannot delete or
# shorten the retention of a log file inside the retention period.
locals {
  trail_arn = "arn:aws:cloudtrail:${var.region}:${var.workload_account_id}:trail/${var.trail_name}"
}
```

The comment above the block says: "The central, tamper-resistant log store. It lives in a separate account (the security account): an administrator of the workload account has no rights here. Object Lock in compliance mode means even this account's owner cannot delete or shorten the retention of a log file inside the retention period.". The `locals` block defines a named value used inside this module. `trail_arn` is the full name of the workload account's trail, **built from text** (region, workload account number and trail name), so the bucket policy can name a trail that lives in another account ([terraform.md](terraform.md)).

From `infra/modules/log-archive/main.tf` (lines 8 to 14):

```hcl
resource "aws_s3_bucket" "archive" {
  #checkov:skip=CKV_AWS_18:Access to the archive is itself recorded by the security account's own trail in a real organization; this build keeps one trail.
  #checkov:skip=CKV_AWS_144:Cross-region replication of the archive is a production decision, see ARCHITECTURE.md.
  #checkov:skip=CKV2_AWS_62:Nothing reacts to log delivery here; detection runs from the rules in the workload account and the batch scan.
  bucket              = var.bucket_name
  object_lock_enabled = true
}
```

Creates the **archive bucket** ([aws-s3.md](aws-s3.md)). `bucket = var.bucket_name` is its name. `object_lock_enabled = true` switches on **Object Lock** at creation, the write-once protection. It sets no `force_destroy`: a locked bucket cannot be emptied early, and that is the point.

- `#checkov:skip=CKV_AWS_18:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_18` for this resource only. The stated reason is: "Access to the archive is itself recorded by the security account's own trail in a real organization; this build keeps one trail.".
- `#checkov:skip=CKV_AWS_144:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_144` for this resource only. The stated reason is: "Cross-region replication of the archive is a production decision, see ARCHITECTURE.md.".
- `#checkov:skip=CKV2_AWS_62:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV2_AWS_62` for this resource only. The stated reason is: "Nothing reacts to log delivery here; detection runs from the rules in the workload account and the batch scan.".

From `infra/modules/log-archive/main.tf` (lines 16 to 22):

```hcl
resource "aws_s3_bucket_ownership_controls" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
```

Turns off the old per-object permission lists (ACLs). `bucket = <the bucket>.bucket` ties it to the bucket made above (referring to another resource's attribute is how Terraform learns the order in which to create things). The nested `rule` block sets `object_ownership = "BucketOwnerEnforced"`: the bucket owner owns every object and ACLs are ignored, so policies are the only way access is granted ([aws-s3.md](aws-s3.md)).

From `infra/modules/log-archive/main.tf` (lines 24 to 30):

```hcl
resource "aws_s3_bucket_public_access_block" "archive" {
  bucket                  = aws_s3_bucket.archive.bucket
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}
```

Switches on **Block Public Access**, four independent safety switches, all set to `true`: `block_public_acls` (refuse any request that tries to attach a public ACL), `ignore_public_acls` (ignore any public ACL that exists), `block_public_policy` (refuse a bucket policy that would make the bucket public) and `restrict_public_buckets` (even if such a policy exists, allow only the owner's account and services). `bucket = ...` names the bucket they apply to ([aws-s3.md](aws-s3.md)).

From `infra/modules/log-archive/main.tf` (lines 32 to 38):

```hcl
resource "aws_s3_bucket_versioning" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  versioning_configuration {
    status = "Enabled"
  }
}
```

Turns on **versioning** for the bucket named in `bucket`. The nested `versioning_configuration` block has `status = "Enabled"`: from now on an overwrite or a delete keeps the earlier version, so the earlier data can be recovered.

From `infra/modules/log-archive/main.tf` (lines 40 to 51):

```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  rule {
    bucket_key_enabled = true

    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.key_alias_arn
    }
  }
}
```

Sets the bucket's **default encryption**. In the nested `rule` block, `bucket_key_enabled = true` makes S3 reuse one short-lived key for many objects, which cuts the number of calls to the key service (and their cost). In the inner `apply_server_side_encryption_by_default` block, `sse_algorithm = "aws:kms"` chooses encryption with a key from the key service, and `kms_master_key_id = var.key_alias_arn` names which key, by the alias ARN passed in ([aws-kms.md](aws-kms.md)). The key policy, not the bucket policy, then decides who can read.

From `infra/modules/log-archive/main.tf` (lines 53 to 65):

```hcl
# Compliance mode cannot be shortened or removed by anyone. The exercise uses a one-day retention so teardown is possible.
resource "aws_s3_bucket_object_lock_configuration" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.retention_days
    }
  }

  depends_on = [aws_s3_bucket_versioning.archive]
}
```

The comment above the block says: "Compliance mode cannot be shortened or removed by anyone. The exercise uses a one-day retention so teardown is possible.". Sets the **default lock** applied to every new object. The comment above the block explains: compliance mode cannot be shortened or removed by anyone, and the exercise uses a one-day retention so teardown is possible. The nested `rule` holds `default_retention` with `mode = "COMPLIANCE"` and `days = var.retention_days`. `depends_on = [aws_s3_bucket_versioning.archive]` creates versioning first, because Object Lock works on versions.

From `infra/modules/log-archive/main.tf` (lines 67 to 91):

```hcl
# Files leave only by expiring after the retention has ended; nobody deletes them by hand.
resource "aws_s3_bucket_lifecycle_configuration" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  rule {
    id     = "expire-after-retention"
    status = "Enabled"

    filter {}

    expiration {
      days = var.expire_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.expire_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.archive]
}
```

The comment above the block says: "Files leave only by expiring after the retention has ended; nobody deletes them by hand.". A **lifecycle configuration** is a set of rules that S3 applies on a schedule. The comment above the block says files leave only by expiring after the retention has ended; nobody deletes them by hand. One `rule`: `id = "expire-after-retention"`, `status = "Enabled"`. `filter {}` is an empty filter: the rule applies to **every** object in the bucket. `expiration { days = var.expire_days }` removes current files after that many days and `noncurrent_version_expiration { noncurrent_days = var.expire_days }` removes old versions after that many days; the expiry must be longer than the retention, or the rule would try to remove a locked file. `abort_incomplete_multipart_upload { days_after_initiation = 7 }` cleans up large uploads that were started and never finished, after 7 days. `depends_on` creates versioning first.

From `infra/modules/log-archive/main.tf` (lines 93 to 136):

```hcl
resource "aws_s3_bucket_policy" "archive" {
  bucket = aws_s3_bucket.archive.bucket

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "TrailChecksTheBucketAcl"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = "arn:aws:s3:::${var.bucket_name}"
        Condition = { StringEquals = { "aws:SourceArn" = local.trail_arn } }
      },
      {
        Sid       = "TrailWritesLogFilesOfTheWorkloadAccount"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "arn:aws:s3:::${var.bucket_name}/AWSLogs/${var.workload_account_id}/*"
        Condition = {
          StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control", "aws:SourceArn" = local.trail_arn }
        }
      },
      {
        Sid       = "NobodyDeletesOrRewritesLogFiles"
        Effect    = "Deny"
        Principal = { AWS = "*" }
        Action    = ["s3:DeleteObject", "s3:DeleteObjectVersion", "s3:PutObjectRetention", "s3:BypassGovernanceRetention"]
        Resource  = "arn:aws:s3:::${var.bucket_name}/*"
      },
      {
        Sid       = "DenyPlainHttp"
        Effect    = "Deny"
        Principal = { AWS = "*" }
        Action    = "s3:*"
        Resource  = ["arn:aws:s3:::${var.bucket_name}", "arn:aws:s3:::${var.bucket_name}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.archive]
}
```

Attaches a **bucket policy**, a policy document stored on the bucket itself. `policy = jsonencode({...})` turns the HCL value into JSON text, because the service wants JSON text ([json.md](json.md)); `Version = "2012-10-17"` is the policy language version, not a date of this project. 
The policy has four statements:

- `TrailChecksTheBucketAcl`: allows the audit service (`Principal = { Service = "cloudtrail.amazonaws.com" }`) `s3:GetBucketAcl`, only for the one trail (`aws:SourceArn`).
- `TrailWritesLogFilesOfTheWorkloadAccount`: allows `s3:PutObject` into `AWSLogs/<workload account>/*`, only for that trail and only with `s3:x-amz-acl = bucket-owner-full-control`. The folder name contains the **workload** account's number, because the trail runs in that account but the bucket belongs to the security account.
- `NobodyDeletesOrRewritesLogFiles`: `Effect = "Deny"`, `Principal = { AWS = "*" }`, `Action = ["s3:DeleteObject", "s3:DeleteObjectVersion", "s3:PutObjectRetention", "s3:BypassGovernanceRetention"]` on all objects. A Deny beats every Allow, so no one can delete a file or version, shorten a retention or bypass a lock. This is a second barrier besides Object Lock.
- `DenyPlainHttp`: The `Deny` statement `DenyPlainHttp`: `Principal = { AWS = "*" }` (everyone), `Action = "s3:*"` (every S3 action), `Resource` lists both the bucket and its objects (`.../*`), and `Condition = { Bool = { "aws:SecureTransport" = "false" } }` makes it apply only to requests that did **not** use an encrypted (HTTPS) connection. A Deny beats every Allow, so no one can use the bucket over plain HTTP.

The `depends_on` line orders the creation: the policy is created only after Block Public Access is on, so a public statement could never be accepted in between.

##### `infra/modules/log-archive/outputs.tf`

From `infra/modules/log-archive/outputs.tf` (lines 1 to 4):

```hcl
output "bucket_name" {
  description = "Name of the archive bucket."
  value       = aws_s3_bucket.archive.bucket
}
```

Declares the **output** `bucket_name`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "Name of the archive bucket." `value = aws_s3_bucket.archive.bucket` is the attribute `bucket` of the resource `aws_s3_bucket.archive` created by this module.

#### Module `infra/modules/posture`

##### `infra/modules/posture/versions.tf`

From `infra/modules/posture/versions.tf` (lines 1 to 10):

```hcl
terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
```

The `terraform` block holds settings about Terraform itself. `required_version = ">= 1.9"` makes Terraform refuse to run if it is older than 1.9. `required_providers` lists the provider plug-ins this folder needs: the entry `aws` has `source = "hashicorp/aws"` (the registry address of the AWS provider) and `version = "~> 6.0"`, meaning "6.0 or newer, but below 7" ([terraform-aws-provider.md](terraform-aws-provider.md)). Every module repeats the same block so it can be used and checked on its own.

##### `infra/modules/posture/variables.tf`

From `infra/modules/posture/variables.tf` (lines 1 to 5):

```hcl
variable "name" {
  description = "Name prefix."
  type        = string
  default     = "detect"
}
```

Declares the **input variable** `name`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Name prefix." `type = string` restricts the value to text; Terraform refuses any other kind of value. `default = "detect"` is the value used when the caller supplies none, which makes the variable optional.

From `infra/modules/posture/variables.tf` (lines 7 to 10):

```hcl
variable "account_id" {
  description = "The account being assessed."
  type        = string
}
```

Declares the **input variable** `account_id`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "The account being assessed." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/posture/variables.tf` (lines 12 to 15):

```hcl
variable "region" {
  description = "Region of the standards subscription."
  type        = string
}
```

Declares the **input variable** `region`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Region of the standards subscription." `type = string` restricts the value to text; Terraform refuses any other kind of value. There is no `default`, so the caller **must** provide a value.

From `infra/modules/posture/variables.tf` (lines 17 to 21):

```hcl
variable "retention_days" {
  description = "Days configuration snapshots are kept."
  type        = number
  default     = 30
}
```

Declares the **input variable** `retention_days`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Days configuration snapshots are kept." `type = number` restricts the value to a number; Terraform refuses any other kind of value. `default = 30` is the value used when the caller supplies none, which makes the variable optional.

From `infra/modules/posture/variables.tf` (lines 23 to 27):

```hcl
variable "force_destroy" {
  description = "Delete the snapshot bucket with its objects on destroy. True only in a throwaway sandbox."
  type        = bool
  default     = false
}
```

Declares the **input variable** `force_destroy`: a value the caller of this configuration or module must or may supply. `description` is the human-readable explanation: "Delete the snapshot bucket with its objects on destroy. True only in a throwaway sandbox." `type = bool` restricts the value to true or false; Terraform refuses any other kind of value. `default = false` is the value used when the caller supplies none, which makes the variable optional.

##### `infra/modules/posture/main.tf`

From `infra/modules/posture/main.tf` (lines 1 to 4):

```hcl
# Posture management: Security Hub with the foundational best-practices standard, fed by AWS Config recording.
locals {
  config_bucket = "${var.name}-config-${var.account_id}"
}
```

The comment above the block says: "Posture management: Security Hub with the foundational best-practices standard, fed by AWS Config recording.". One named value, `config_bucket`, the name of the bucket that receives the configuration snapshots, built from the module's name and the account number.

From `infra/modules/posture/main.tf` (lines 6 to 13):

```hcl
resource "aws_s3_bucket" "config" {
  #checkov:skip=CKV_AWS_18:The recorder's own delivery bucket; CloudTrail data events are not enabled for it.
  #checkov:skip=CKV_AWS_144:Single-region sandbox.
  #checkov:skip=CKV_AWS_145:AWS Config delivers with the recorder's role; a customer-managed key needs further grants outside this lesson.
  #checkov:skip=CKV2_AWS_62:Nothing reacts to configuration snapshots here.
  bucket        = local.config_bucket
  force_destroy = var.force_destroy
}
```

Creates the **bucket** that AWS Config delivers its snapshots to ([aws-config.md](aws-config.md)). `bucket = local.config_bucket` is its name and `force_destroy = var.force_destroy` lets the sandbox teardown delete it with its contents. The skip comments say why the scanner checks do not apply.

- `#checkov:skip=CKV_AWS_18:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_18` for this resource only. The stated reason is: "The recorder's own delivery bucket; CloudTrail data events are not enabled for it.".
- `#checkov:skip=CKV_AWS_144:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_144` for this resource only. The stated reason is: "Single-region sandbox.".
- `#checkov:skip=CKV_AWS_145:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV_AWS_145` for this resource only. The stated reason is: "AWS Config delivers with the recorder's role; a customer-managed key needs further grants outside this lesson.".
- `#checkov:skip=CKV2_AWS_62:...` is a comment that the scanner Checkov reads ([checkov.md](checkov.md)): it skips the check `CKV2_AWS_62` for this resource only. The stated reason is: "Nothing reacts to configuration snapshots here.".

From `infra/modules/posture/main.tf` (lines 15 to 21):

```hcl
resource "aws_s3_bucket_public_access_block" "config" {
  bucket                  = aws_s3_bucket.config.bucket
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}
```

Switches on **Block Public Access**, four independent safety switches, all set to `true`: `block_public_acls` (refuse any request that tries to attach a public ACL), `ignore_public_acls` (ignore any public ACL that exists), `block_public_policy` (refuse a bucket policy that would make the bucket public) and `restrict_public_buckets` (even if such a policy exists, allow only the owner's account and services). `bucket = ...` names the bucket they apply to ([aws-s3.md](aws-s3.md)).

From `infra/modules/posture/main.tf` (lines 23 to 29):

```hcl
resource "aws_s3_bucket_ownership_controls" "config" {
  bucket = aws_s3_bucket.config.bucket

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
```

Turns off the old per-object permission lists (ACLs). `bucket = <the bucket>.bucket` ties it to the bucket made above (referring to another resource's attribute is how Terraform learns the order in which to create things). The nested `rule` block sets `object_ownership = "BucketOwnerEnforced"`: the bucket owner owns every object and ACLs are ignored, so policies are the only way access is granted ([aws-s3.md](aws-s3.md)).

From `infra/modules/posture/main.tf` (lines 31 to 37):

```hcl
resource "aws_s3_bucket_versioning" "config" {
  bucket = aws_s3_bucket.config.bucket

  versioning_configuration {
    status = "Enabled"
  }
}
```

Turns on **versioning** for the bucket named in `bucket`. The nested `versioning_configuration` block has `status = "Enabled"`: from now on an overwrite or a delete keeps the earlier version, so the earlier data can be recovered.

From `infra/modules/posture/main.tf` (lines 39 to 47):

```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  bucket = aws_s3_bucket.config.bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

Sets the bucket's **default encryption** to `sse_algorithm = "AES256"`, the service-managed key. This bucket receives AWS Config snapshots, and the Config service cannot write to a bucket encrypted with a customer-managed key without extra grants that are outside this lesson (the scanner skip on the bucket says the same).

From `infra/modules/posture/main.tf` (lines 49 to 72):

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "config" {
  bucket = aws_s3_bucket.config.bucket

  rule {
    id     = "expire-snapshots"
    status = "Enabled"

    filter {}

    expiration {
      days = var.retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.config]
}
```

A **lifecycle configuration** is a set of rules that S3 applies on a schedule. One `rule`: `id = "expire-snapshots"`, `status = "Enabled"`. `filter {}` is an empty filter: the rule applies to **every** object in the bucket. `expiration { days = var.retention_days }` removes snapshots after that many days and `noncurrent_version_expiration { noncurrent_days = 7 }` removes old versions after 7 days. `abort_incomplete_multipart_upload { days_after_initiation = 7 }` cleans up large uploads that were started and never finished, after 7 days. `depends_on` creates versioning first.

From `infra/modules/posture/main.tf` (lines 74 to 92):

```hcl
resource "aws_s3_bucket_policy" "config" {
  bucket = aws_s3_bucket.config.bucket

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyPlainHttp"
        Effect    = "Deny"
        Principal = { AWS = "*" }
        Action    = "s3:*"
        Resource  = ["arn:aws:s3:::${local.config_bucket}", "arn:aws:s3:::${local.config_bucket}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.config]
}
```

Attaches a **bucket policy**, a policy document stored on the bucket itself. `policy = jsonencode({...})` turns the HCL value into JSON text, because the service wants JSON text ([json.md](json.md)); `Version = "2012-10-17"` is the policy language version, not a date of this project. It has one statement, The `Deny` statement `DenyPlainHttp`: `Principal = { AWS = "*" }` (everyone), `Action = "s3:*"` (every S3 action), `Resource` lists both the bucket and its objects (`.../*`), and `Condition = { Bool = { "aws:SecureTransport" = "false" } }` makes it apply only to requests that did **not** use an encrypted (HTTPS) connection. A Deny beats every Allow, so no one can use the bucket over plain HTTP.

The `depends_on` line orders the creation: the policy is created only after Block Public Access is on, so a public statement could never be accepted in between.

From `infra/modules/posture/main.tf` (lines 94 to 106):

```hcl
resource "aws_iam_role" "config" {
  name = "${var.name}-config-recorder"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "config.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = { StringEquals = { "aws:SourceAccount" = var.account_id } }
    }]
  })
}
```

Creates the **role** the configuration recorder takes. `name = "${var.name}-config-recorder"`. The trust policy allows `sts:AssumeRole` for `Principal = { Service = "config.amazonaws.com" }`, only on behalf of this account (`Condition = { StringEquals = { "aws:SourceAccount" = var.account_id } }`) ([aws-iam.md](aws-iam.md)).

From `infra/modules/posture/main.tf` (lines 108 to 111):

```hcl
resource "aws_iam_role_policy_attachment" "config" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}
```

Attaches AWS's managed policy `service-role/AWS_ConfigRole` to the role, which lets the recorder read the settings of resources. `role` names the role and `policy_arn` the policy.

From `infra/modules/posture/main.tf` (lines 113 to 135):

```hcl
resource "aws_iam_role_policy" "deliver" {
  name = "deliver-to-the-config-bucket"
  role = aws_iam_role.config.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "CheckTheBucket"
        Effect   = "Allow"
        Action   = "s3:GetBucketAcl"
        Resource = "arn:aws:s3:::${local.config_bucket}"
      },
      {
        Sid       = "WriteSnapshots"
        Effect    = "Allow"
        Action    = "s3:PutObject"
        Resource  = "arn:aws:s3:::${local.config_bucket}/AWSLogs/${var.account_id}/Config/*"
        Condition = { StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" } }
      },
    ]
  })
}
```

Gives the role its delivery permissions. Statement `CheckTheBucket` allows `s3:GetBucketAcl` on the bucket. Statement `WriteSnapshots` allows `s3:PutObject` on `arn:aws:s3:::<bucket>/AWSLogs/<account>/Config/*` (one folder of one bucket), with the condition `s3:x-amz-acl = bucket-owner-full-control`.

From `infra/modules/posture/main.tf` (lines 137 to 145):

```hcl
resource "aws_config_configuration_recorder" "this" {
  name     = var.name
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}
```

Creates the **recorder**. `name` labels it, `role_arn = aws_iam_role.config.arn` is the role above. The nested `recording_group` block sets `all_supported = true` (every supported resource type) and `include_global_resource_types = true` (also global ones such as IAM) ([aws-config.md](aws-config.md)).

From `infra/modules/posture/main.tf` (lines 147 to 152):

```hcl
resource "aws_config_delivery_channel" "this" {
  name           = var.name
  s3_bucket_name = aws_s3_bucket.config.bucket

  depends_on = [aws_config_configuration_recorder.this, aws_s3_bucket_policy.config]
}
```

Creates the **delivery channel**: `name` labels it and `s3_bucket_name` is the bucket above. `depends_on` makes Terraform create the recorder and the bucket policy first.

From `infra/modules/posture/main.tf` (lines 154 to 159):

```hcl
resource "aws_config_configuration_recorder_status" "this" {
  name       = aws_config_configuration_recorder.this.name
  is_enabled = true

  depends_on = [aws_config_delivery_channel.this]
}
```

Switches the recorder **on**: `name` names it and `is_enabled = true` turns it on. `depends_on = [aws_config_delivery_channel.this]` makes it the last step, since recording needs a place to deliver to.

From `infra/modules/posture/main.tf` (lines 161 to 163):

```hcl
resource "aws_securityhub_account" "this" {
  depends_on = [aws_config_configuration_recorder_status.this]
}
```

Turns on **Security Hub** for the account ([aws-security-hub.md](aws-security-hub.md)). It has no arguments; `depends_on = [aws_config_configuration_recorder_status.this]` makes the recorder run first.

From `infra/modules/posture/main.tf` (lines 165 to 169):

```hcl
resource "aws_securityhub_standards_subscription" "foundational" {
  standards_arn = "arn:aws:securityhub:${var.region}::standards/aws-foundational-security-best-practices/v/1.0.0"

  depends_on = [aws_securityhub_account.this]
}
```

Subscribes to a **standard**, a list of controls: `standards_arn` is the address of AWS Foundational Security Best Practices, version 1.0.0, in this region. `depends_on` creates the Security Hub account first.

##### `infra/modules/posture/outputs.tf`

From `infra/modules/posture/outputs.tf` (lines 1 to 4):

```hcl
output "standards_subscription_arn" {
  description = "ARN of the best-practices subscription."
  value       = aws_securityhub_standards_subscription.foundational.id
}
```

Declares the **output** `standards_subscription_arn`: a value this configuration makes available to whoever uses it (another module, a script, or the person running Terraform). `description` says: "ARN of the best-practices subscription." `value = aws_securityhub_standards_subscription.foundational.id` is the attribute `id` of the resource `aws_securityhub_standards_subscription.foundational` created by this module.

## Try it yourself

```bash
terraform version
```

Expect `Terraform v1.17.0` (yours may be newer).

```bash
terraform fmt -check -recursive infra; echo "exit $?"
```

Expect no file names and `exit 0`.

```bash
terraform -chdir=infra/environments/workload validate
```

Expect `Success! The configuration is valid.` (after `make plan` has run `init`).

```bash
python3 -c "
import json
for e in ('security', 'workload'):
    rc = json.load(open(f'build/{e}.json'))['resource_changes']
    print(e, len(rc), len({r['type'] for r in rc}))"
```

After `make plan`, expect `security 10 10` and `workload 51 26`: the archive environment would create 10 resources of 10 types, the workload environment 51 of 26 types.

```bash
terraform -chdir=infra/environments/workload providers | head -n 5
```

Expect a tree showing the `hashicorp/aws ~> 6.0` provider required by the root and by each module.

## Mistakes people make

- Committing `*.tfstate` (it can contain secrets) or `.terraform/`. Both are git-ignored here.
- Creating an access key in Terraform. The secret would sit in the state. The drill key is created by a script into a CLI profile.
- Applying while `plan_only = true`. The provider would skip real calls and the result would be meaningless.
- Applying the workload environment before the security environment: it needs the archive's bucket name and key ARN.
- Forgetting that `count = 0` removes the module and its resources on the next apply. That is what teardown relies on.
- Forgetting the provider lock file when sharing a repo, so machines install different provider versions.

## Check yourself

1. What does `terraform plan` do? *Compares the configuration with the state and the cloud and prints what it would change, without changing anything.*
2. Why is the same `alerting` module called three times? *A rule sees only its own Region, so each Region needs its own copy with its own provider.*
3. What does `count = var.enable_drill ? 1 : 0` do? *Creates the drill module only when the variable is true.*
4. How are the detections shared between Python and Terraform? *Both read the same JSON files; Terraform uses `fileset` and `jsondecode`.*
5. What does `~> 6.0` allow? *Any 6.x version from 6.0 up, not 7.*

## Further reading

- Terraform documentation (v1.17): <https://developer.hashicorp.com/terraform/docs>
- HCL language: <https://developer.hashicorp.com/terraform/language>
- CLI commands (`plan`, `show`, `validate`, `fmt`): <https://developer.hashicorp.com/terraform/cli/commands>

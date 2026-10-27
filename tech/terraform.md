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

### The shape of a configuration

From `infra/environments/workload/versions.tf`:

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

- `required_version`: refuse to run on an older Terraform.
- `required_providers`: which plug-in, from which registry address (`hashicorp/aws`), and which versions. `~> 6.0` means "6.0 or newer, but below 7".

### Detections are read from files

From `infra/environments/workload/main.tf`:

```hcl
  detections_dir = "${path.root}/../../../detections"

  detection_all = {
    for file in fileset(local.detections_dir, "d*.json") :
```

`path.root` is the folder of the environment. `fileset(folder, pattern)` lists the files that match (`d1-....json` to `d5-....json`). A `for` expression builds a **map** from them: for each file, the value is the detection read with `jsondecode(file(...))` and the key is its `id` ([json.md](json.md)). The detections are data, so adding a sixth is adding a file.

From `infra/environments/workload/main.tf`:

```hcl
  deployable       = { for id, d in local.detection_all : id => d if !contains(keys(d), "parameters") || local.honeytoken_ready }
```

A `for` with a filter. `keys(d)` lists the names in the detection; `contains(list, x)` asks whether `x` is in it. A detection with a `parameters` entry (D5, which needs the honeytoken's key id) is deployed only when `honeytoken_ready` is true. `!` is "not", `||` is "or".

From `infra/environments/workload/main.tf`:

```hcl
        pattern_json = replace(jsonencode(d.pattern), "__HONEYTOKEN_ACCESS_KEY_ID__", var.honeytoken_access_key_id)
```

`jsonencode` turns the pattern back into JSON text, and `replace(text, old, new)` fills the placeholder. In the offline plan `plan-only.tfvars` sets a fake key id, so every detection, including D5, appears in the plan.

### One module, three Regions

From `infra/environments/workload/main.tf`:

```hcl
module "alerting_global" {
  source    = "../../modules/alerting"
  providers = { aws = aws.global }
```

A **module call**. `source` is the folder. `providers = { aws = aws.global }` hands the module a *named copy* of the provider, here the one configured for `us-east-1`. The module's resources are then created in that Region. The same module is called three times, with different providers and different detections ([terraform-aws-provider.md](terraform-aws-provider.md)).

From `infra/environments/workload/main.tf`:

```hcl
  detections  = local.for_target["global"]
```

Which detections run where is decided by each file's `deployTo`. `for_target` was built earlier with a nested `for`, one map for each of `global`, `home` and `watch`.

### Optional modules

From `infra/environments/workload/main.tf`:

```hcl
module "drill" {
  source = "../../modules/drill"
  count  = var.enable_drill ? 1 : 0
```

`count` makes zero or more copies. `condition ? a : b` is the conditional expression: one copy when `enable_drill` is true, none otherwise. That is how the deliberate weakness exists only while the exercise runs. The copy is addressed as `module.drill[0]`, and the OPA rules recognize the drill by that name ([opa-rego.md](opa-rego.md)).

### Names, not references

From `infra/modules/drill/main.tf`:

```hcl
  user_arn = "arn:aws:iam::${var.account_id}:user/${var.user_name}"
```

`"...${var.account_id}..."` is **interpolation**: it pastes the variable into the text. The user's ARN is built from text and not read from the user resource, so a plan made without an account can show the policy that mentions it. The cost is explicit ordering with `depends_on`, which the drill uses.

### Policies written as data

From `infra/modules/log-archive/main.tf`:

```hcl
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
```

`jsonencode(...)` turns an HCL value into JSON text, because the cloud wants a policy as a JSON string. The `"2012-10-17"` is the policy language version.

### Offline-friendly settings

From `infra/environments/workload/variables.tf`:

```hcl
    condition     = can(regex("^[0-9]{12}$", var.workload_account_id))
    error_message = "workload_account_id must be 12 digits."
```

A **validation** rejects a bad value before anything is planned. `regex` raises an error when the text does not match, and `can(...)` turns "raises an error" into `false`.

The providers take a variable `plan_only`; when true they skip every call that needs an account ([terraform-aws-provider.md](terraform-aws-provider.md)). The values for an offline run are in `plan-only.tfvars`; real values are written to the git-ignored `sandbox.auto.tfvars` by the scripts. A file ending `.auto.tfvars` is loaded automatically.

### Commands in the Makefile

`make plan` loops over both environments with `init -backend=false`, `plan -var-file=plan-only.tfvars -out=...` and `show -json`, and `make validate` adds `fmt -check` and `validate` ([make.md](make.md)). `fmt -check` fails if any file would be re-formatted; `validate` checks that the configuration is well-formed and consistent without contacting any cloud.

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

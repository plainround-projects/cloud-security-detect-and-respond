# TFLint

## What it is

TFLint is a command-line **linter for Terraform**: it reads your `.tf` files and reports mistakes that `terraform validate` does not catch, such as an argument that is valid HCL but not valid for that AWS resource. It works through **rulesets** (plug-ins). This repository uses **TFLint 0.65.0** with the bundled `terraform` ruleset (0.15.0) and the `aws` ruleset **0.38.0**.

## Why this repository uses it

`terraform validate` checks structure. TFLint checks conventions and AWS-specific facts (for example an unused variable, a missing type, or an invalid instance setting), so problems appear at `make lint` and not at apply time in a real account.

## Where it appears

| Path | What it does |
| --- | --- |
| `.tflint.hcl` | the configuration: rulesets and module handling |
| `Makefile` | `tflint --init` and `tflint --recursive --config ...` in `make lint` |

## How it works underneath

TFLint parses the Terraform files itself. It loads the rulesets as separate plug-in programs and passes them the parsed configuration; each plug-in reports findings. `tflint --init` downloads plug-ins that are declared with a `source` (like the AWS one) into your home folder. It does not contact AWS.

## Walkthrough of this repository's use

TFLint is a **linter for Terraform**: it reads the `.tf` files and reports mistakes that `terraform validate` does not catch. It is configured by one file, `.tflint.hcl`, written in the same HCL language as the Terraform code ([terraform.md](terraform.md)). In HCL, a **block** has a type, optional quoted labels, and a body in curly braces; the body holds `name = value` lines called **attributes**. Every line of the file is shown below.

From `.tflint.hcl` (lines 1 to 3):

```hcl
config {
  call_module_type = "local"
}
```

A block of type `config` with no label: TFLint's own settings. `call_module_type = "local"` controls which **modules** (reusable folders of Terraform) TFLint looks inside when a configuration calls them. `"local"` means "check the modules that are folders in this repository", which is every module here. The other choices would also follow modules downloaded from the internet, which this repository does not use.

From `.tflint.hcl` (lines 5 to 8):

```hcl
plugin "terraform" {
  enabled = true
  preset  = "recommended"
}
```

A block of type `plugin` with the label `"terraform"`: this switches on the **built-in ruleset** for general Terraform hygiene (it ships inside TFLint, so it needs no download). `enabled = true` turns it on. `preset = "recommended"` chooses the group of rules that the ruleset's authors recommend, instead of every rule or none. Two of the rules in that group are the ones this repository meets daily: `terraform_typed_variables` reports a `variable` block that has no `type`, and `terraform_unused_declarations` reports a variable or local value that nothing uses. (The "Try it yourself" section shows the second one firing.) The group does not require a description on every variable; this repository adds descriptions by convention.

From `.tflint.hcl` (lines 10 to 14):

```hcl
plugin "aws" {
  enabled = true
  version = "0.38.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}
```

A second `plugin` block, labeled `"aws"`: the **AWS ruleset**, which knows the valid values of AWS resource arguments (for example it can tell that an instance type does not exist). It is not built in, so three attributes say how to get it. `enabled = true` turns it on. `version = "0.38.0"` pins the exact release, so every machine and the CI run the same rules. `source = "github.com/terraform-linters/tflint-ruleset-aws"` is where `tflint --init` downloads it from. Because the plug-in is downloaded, `make lint` runs `tflint --init` before the check.

From `Makefile` (lines 41 to 42):

```make
	tflint --init
	tflint --recursive --config $(CURDIR)/.tflint.hcl
```

These two lines in `make lint` run TFLint. `tflint --init` downloads the plug-ins named in `.tflint.hcl` (only the AWS ruleset). `tflint --recursive --config $(CURDIR)/.tflint.hcl` lints every folder that contains Terraform files: `--recursive` descends into the environment folders and each module folder. `--config` names the settings file, and `$(CURDIR)` (the current folder, supplied by `make`) makes the path absolute, because TFLint changes into each folder while it recurses and a relative path would then be wrong. TFLint prints nothing and exits 0 when it finds nothing, so `make lint` continues; any finding makes it exit with a non-zero code and `make` stops.

## Try it yourself

```bash
tflint --version
```

Expect `TFLint version 0.65.0`, then the `aws` ruleset line (`ruleset.aws (0.38.0)`) and the bundled `terraform` ruleset.

```bash
tflint --recursive --config $(pwd)/.tflint.hcl; echo "exit $?"
```

Expect no findings and `exit 0`.

```bash
printf '\nvariable "unused" {\n  type = string\n}\n' >> infra/modules/budget/variables.tf
tflint --recursive --config $(pwd)/.tflint.hcl
git checkout infra
```

Expect `1 issue(s) found:` and `Warning: [Fixable] variable "unused" is declared but not used (terraform_unused_declarations)`. The last line undoes the experiment.

## Mistakes people make

- Not running `tflint --init`, so the AWS rules silently do not run.
- Pointing `--config` at a relative path and running in recursive mode.
- Treating TFLint as a security scanner. It checks correctness and style; the security scan is [checkov.md](checkov.md).

## Check yourself

1. What does TFLint add to `terraform validate`? *Rules for conventions and for AWS-specific argument values.*
2. What does `tflint --init` do? *Downloads the declared plug-in rulesets.*
3. What does `--recursive` do? *Checks every folder with Terraform files.*
4. Why pin the `aws` ruleset version? *So the same rules apply on every machine and in CI.*
5. Does TFLint contact AWS? *No.*

## Further reading

- TFLint: <https://github.com/terraform-linters/tflint> (0.65)
- Configuration: <https://github.com/terraform-linters/tflint/blob/master/docs/user-guide/config.md>
- AWS ruleset: <https://github.com/terraform-linters/tflint-ruleset-aws> (0.38.0)

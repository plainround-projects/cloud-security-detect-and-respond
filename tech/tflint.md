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

From `.tflint.hcl`:

```hcl
config {
  call_module_type = "local"
}
```

`call_module_type = "local"` makes TFLint also check the modules the configuration calls when they are local folders (all of this repository's modules are).

From `.tflint.hcl`:

```hcl
plugin "terraform" {
  enabled = true
  preset  = "recommended"
}
```

The built-in ruleset for general Terraform hygiene. The `recommended` preset turns on the rules the TFLint authors suggest, including `terraform_typed_variables` (every variable has a `type`) and `terraform_unused_declarations` (a variable or local that nothing uses is reported). It does not demand a description on every variable; the modules here carry descriptions by convention.

From `.tflint.hcl`:

```hcl
plugin "aws" {
  enabled = true
  version = "0.38.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}
```

The AWS ruleset: it knows the valid values for AWS resource arguments. `version` pins it so everyone gets the same rules; `source` says where `tflint --init` downloads it from.

From `Makefile`:

```make
	tflint --init
	tflint --recursive --config $(CURDIR)/.tflint.hcl
```

`--init` installs the plug-ins. `--recursive` checks every folder that contains Terraform files (the environment and each module). `--config` points at the file with an absolute path, because TFLint changes folders while recursing.

TFLint prints nothing when it finds nothing, and exits 0. That is why every module in this repository has typed and described variables and outputs.

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

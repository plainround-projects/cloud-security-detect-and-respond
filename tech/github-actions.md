# GitHub Actions

## What it is

GitHub Actions is GitHub's built-in automation. You describe a **workflow** in a YAML file; GitHub starts a fresh virtual machine (a **runner**) whenever a trigger happens (a push, a pull request) and runs your steps on it. It is how this repository checks itself on every change without anyone's laptop being involved.

## Why this repository uses it

The project rule is that CI mirrors what a reader does locally. The workflow installs the tools at pinned versions and runs the same `make` targets, so a green check on GitHub means the same thing as a green run on your machine.

## Where it appears

| Path | What it does |
| --- | --- |
| `.github/workflows/ci.yml` | the workflow: one job, twelve steps |

## How it works underneath

GitHub finds `.yml` files in `.github/workflows/`. On a trigger it allocates a clean runner (`ubuntu-latest`), then runs the job's steps in order in the same folder checkout. A step is either a **ready-made action** (`uses:`, a reusable program published on GitHub) or a **shell command** (`run:`). If any step exits non-zero, the job fails and later steps do not run. Nothing is kept between runs.

## Walkthrough of this repository's use

This is the only workflow file in the repository, and every line of it is shown below, in file order. The format of the file is YAML; read [yaml.md](yaml.md) if the indentation or the dashes look strange.

**The vocabulary.** A **workflow** is one YAML file under `.github/workflows/`; GitHub reads every such file. An **event** is something that happens to the repository (a push of commits, a pull request). A **job** is a list of **steps** that runs on one fresh machine, called a **runner**; GitHub creates the machine, runs the steps and deletes the machine. A **step** is either a command to run (`run:`) or a ready-made, shared piece of automation called an **action** (`uses:`). An action is a repository on GitHub that anyone can reference by its owner, name and version, for example `actions/checkout@v4`: the `@v4` is a **tag**, a name that points to one released version of that action.

From `.github/workflows/ci.yml` (line 1):

```yaml
name: ci
```

`name: ci` is the label shown for this workflow in the Actions tab of the repository and in the list of checks on a pull request.

From `.github/workflows/ci.yml` (line 3):

```yaml
on: [push, pull_request]
```

`on: [push, pull_request]` lists the **events** that start the workflow. `push` fires when commits are pushed to any branch. `pull_request` fires when a pull request is opened or updated (a pull request is a proposal to merge one branch into another). So the checks run both on your own branch and on a proposed change.

From `.github/workflows/ci.yml` (lines 5 to 8):

```yaml
jobs:
  check:
    name: Lint, unit tests, policy tests, credential-free plans, detection replay, dependency audit
    runs-on: ubuntu-latest
```

`jobs:` lists the jobs; this workflow has one, with the identifier `check`. Its `name:` is the human-readable description shown in the interface. `runs-on: ubuntu-latest` chooses the runner: a virtual machine that GitHub provides, running the current Ubuntu Linux image. A job with no `needs:` starts at once; with one job there is nothing to wait for. The file sets no `permissions:`, no `timeout-minutes:`, no `strategy:` (matrix) and no `cache:`, so the defaults apply: the repository's default permission for the automatic token, GitHub's default job time limit, one runner, and a fresh download of every tool on every run.

From `.github/workflows/ci.yml` (line 9):

```yaml
    steps:
```

`steps:` is the ordered list of steps. They run one after another on the same runner and share its disk, so what one step installs the next can use. If any step fails (its command exits with a non-zero code), the job stops there and is marked failed.

From `.github/workflows/ci.yml` (line 10):

```yaml
      - uses: actions/checkout@v4
```

`actions/checkout@v4` is the official action that **copies the repository's files onto the runner**. A fresh runner is empty, so without this step there would be nothing to test.

From `.github/workflows/ci.yml` (lines 11 to 13):

```yaml
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
```

`actions/setup-python@v5` installs a chosen Python and puts it first on the `PATH` (the list of folders the shell searches for programs). `with:` passes **inputs** to the action; `python-version: "3.12"` asks for Python 3.12, the lowest version the project supports (`requires-python = ">=3.12"`). The Makefile then creates the virtual environment from it ([make.md](make.md)).

From `.github/workflows/ci.yml` (lines 14 to 17):

```yaml
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.17.0"
          terraform_wrapper: false
```

`hashicorp/setup-terraform@v3` installs Terraform. `terraform_version: "1.17.0"` pins the exact version the project was verified with. `terraform_wrapper: false` turns off the action's optional wrapper script. The wrapper would capture Terraform's output into the step's outputs; switching it off leaves the plain `terraform` program, so commands such as `terraform show -json ... > file` write exactly what Terraform prints ([terraform.md](terraform.md)).

From `.github/workflows/ci.yml` (lines 18 to 20):

```yaml
      - uses: terraform-linters/setup-tflint@v4
        with:
          tflint_version: v0.65.0
```

`terraform-linters/setup-tflint@v4` installs `tflint`, the Terraform linter ([tflint.md](tflint.md)). `tflint_version: v0.65.0` pins the version.

From `.github/workflows/ci.yml` (lines 21 to 23):

```yaml
      - uses: open-policy-agent/setup-opa@v2
        with:
          version: 1.21.4
```

`open-policy-agent/setup-opa@v2` installs `opa`, the policy engine ([opa-rego.md](opa-rego.md)). `version: 1.21.4` pins the version.

From `.github/workflows/ci.yml` (line 24):

```yaml
      - run: pipx install checkov==3.3.30
```

`run:` executes a command in a shell on the runner. `pipx install checkov==3.3.30` installs the security scanner `checkov` at exactly version 3.3.30. `pipx` is a tool that installs a Python **command-line program** in its own private environment, so its many dependencies cannot clash with the project's ([checkov.md](checkov.md)). Checkov is not in the lock files for that reason.

From `.github/workflows/ci.yml` (lines 25 to 30):

```yaml
      - run: make lint
      - run: make test
      - run: make validate
      - run: make demo-drill
      - run: make audit
      - run: make test-e2e
```

The last 6 steps run the project's own commands, each as `make TARGET`. They are the same commands a person runs locally, so "passes on my machine" and "passes in CI" mean the same thing. They run in this order, and the first failing one stops the job:

- `make lint` runs every static check (linters, type checker, import rules, Terraform format, Terraform lint, security scan, policy format, shell lint) as described in [make.md](make.md).
- `make test` runs the unit tests with coverage and the policy tests.
- `make validate` validates the Terraform, makes the credential-free plan(s) and runs the rules and the replay against them.
- `make demo-drill` replays the rehearsal archive: detections, timeline, measured times, archive integrity.
- `make audit` checks the pinned libraries for known vulnerabilities (needs network access, which the runner has).
- `make test-e2e` runs the end-to-end tests, which start `make` as a sub-process.

No step gets a secret or a cloud credential: the plan is made with placeholder values and nothing is deployed, so the workflow needs no secrets configured in GitHub.

## Try it yourself

```bash
sed -n 1,6p .github/workflows/ci.yml
```

Expect the workflow name, the trigger and the first lines of the job.

```bash
grep -c "uses:" .github/workflows/ci.yml; grep -c "run:" .github/workflows/ci.yml
```

Expect `5` and `7`: five ready-made actions and seven shell commands.

```bash
make lint test validate audit
```

The local equivalent of the job (CI also runs `demo-drill` and `test-e2e`).

## Mistakes people make

- Using an unpinned action (`@main`) and having the workflow change under you. This workflow pins major versions and exact tool versions.
- Passing real cloud credentials to a workflow that does not need them. The offline plan uses none.
- Letting CI and local commands drift apart. Here both call `make`.

## Check yourself

1. What starts a workflow? *The triggers in `on:`, here pushes and pull requests.*
2. What is a runner? *The fresh virtual machine that executes the job.*
3. What is the difference between `uses:` and `run:`? *`uses:` runs a published action; `run:` runs a shell command.*
4. Why pin versions? *So the check does not change meaning when a tool updates.*
5. Why does the job need no secrets? *The Terraform plan is made without cloud credentials.*

## Further reading

- GitHub Actions documentation: <https://docs.github.com/en/actions>
- Workflow syntax: <https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions>
- `actions/checkout` v4: <https://github.com/actions/checkout>; `actions/setup-python` v5: <https://github.com/actions/setup-python>; `hashicorp/setup-terraform` v3: <https://github.com/hashicorp/setup-terraform>

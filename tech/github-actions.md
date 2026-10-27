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

From `.github/workflows/ci.yml`:

```yaml
on: [push, pull_request]
```

Run on every push and on every pull request.

From `.github/workflows/ci.yml`:

```yaml
      - uses: actions/checkout@v4
```

Downloads the repository onto the runner. `@v4` is the version of the action.

From `.github/workflows/ci.yml`:

```yaml
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
```

Installs Python 3.12 (the oldest version the project supports; local runs use 3.13).

From `.github/workflows/ci.yml`:

```yaml
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.17.0"
          terraform_wrapper: false
```

Installs the exact Terraform. `terraform_wrapper: false` stops the action from wrapping the command in a script that would change its output.

From `.github/workflows/ci.yml`:

```yaml
      - uses: terraform-linters/setup-tflint@v4
        with:
          tflint_version: v0.65.0
      - uses: open-policy-agent/setup-opa@v2
        with:
          version: 1.21.4
      - run: pipx install checkov==3.3.30
```

Installs [TFLint](tflint.md) and [OPA](opa-rego.md) at the pinned versions, and Checkov ([checkov.md](checkov.md)) with `pipx`, a tool that installs a Python program in its own isolated environment. ShellCheck is already present on the runner.

From `.github/workflows/ci.yml`:

```yaml
      - run: make lint
      - run: make test
      - run: make validate
      - run: make demo-drill
      - run: make audit
      - run: make test-e2e
```

The same commands as in the README; see [make.md](make.md). The Terraform plan inside `make validate` needs no credentials, so no secret is configured in GitHub.

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

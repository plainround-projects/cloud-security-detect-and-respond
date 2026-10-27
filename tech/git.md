# Git

## What it is

Git is a version-control tool: it records the history of a project as a series of **commits**, each a snapshot of all tracked files plus a message. You can see what changed, when and why, and go back. A **repository** is the folder that git tracks (it keeps its history in a hidden `.git` folder). A `.gitignore` file lists files git must never track.

## Why this repository uses it

Each project here is its own repository so it can be pushed to GitHub on its own. The history is part of the deliverable: small commits with messages that say *why* (`feat(infra): ...`, `test: ...`). The `.gitignore` also protects the project from the worst mistake in a security repository: committing something that must stay local (credentials files, Terraform state, evidence collected from a real account).

## Where it appears

| Path | What it does with git |
| --- | --- |
| `.git/` | the history (not in the file listing) |
| `.gitignore` | files git must not track |
| `infra/environments/sandbox/.terraform.lock.hcl` | tracked on purpose: the provider lock ([terraform.md](terraform.md)) |
| `.github/workflows/ci.yml` | runs on pushes to GitHub ([github-actions.md](github-actions.md)) |

## How it works underneath

Git stores each version of each file by its content hash. A commit points to a **tree** (the folder contents at that moment) and to its **parent** commit, which forms the history chain. `git add` moves changes into the **staging area** (the next commit's contents); `git commit` writes a commit from it. `git status` compares the working folder, the staging area and the last commit. A file matching `.gitignore` is invisible to `git status` and `git add`.

## Walkthrough of this repository's use

From `.gitignore`:

```text
.venv/
__pycache__/
*.pyc
*.egg-info/
build/
dist/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.import_linter_cache/
.coverage
```

These are local, generated things: the virtual environment, Python's compiled caches, build output (`build/` holds the plan files), and the caches and data files of [pytest.md](pytest.md), [mypy.md](mypy.md), [ruff.md](ruff.md), [import-linter.md](import-linter.md) and [coverage.md](coverage.md). A trailing `/` means "a folder". `*` matches any characters.

From `.gitignore`:

```text
.env
.terraform/
*.tfstate
*.tfstate.*
*.tfplan
infra/environments/sandbox/sandbox.auto.tfvars
evidence/
```

- `.env` holds personal values (see `.env.example` for the template).
- `.terraform/` is downloaded plugins; `*.tfstate*` is Terraform's record of what it created (it can contain secrets); `*.tfplan` is a saved plan.
- `sandbox.auto.tfvars` is written by `scripts/01-deploy.sh` with your real account id; it must not be committed.
- `evidence/` is the output collected from a real account.

The lock file `.terraform.lock.hcl` is *not* ignored: it must be committed so everyone installs the same provider.

**Commit messages.** The project uses *semantic commits*: a type, a scope, a colon, a summary (`feat(infra): add the hardened workload...`). The body explains why. `git log --oneline` shows the first line of each.

## Try it yourself

```bash
git log --oneline | sed -n 1,4p
```

Expect the latest commit subjects, such as `docs: add the README, architecture, detections, runbook and decision records`.

```bash
git check-ignore -v .venv build/plan.json infra/environments/sandbox/sandbox.auto.tfvars
```

Expect one line per path naming the `.gitignore` line that ignores it, such as `.gitignore:1:.venv/	.venv`.

```bash
git ls-files | grep -vc '^tech/'
```

Expect `136`: the count of tracked files before the `tech/` folder was added.

```bash
git status --short
```

Expect no output on a clean tree.

## Mistakes people make

- Committing generated or secret files. `.gitignore` is the guard; check `git status` before `git add`.
- Using `git add .` blindly. Add the specific paths you changed.
- Forgetting that `.gitignore` does not remove a file that was already committed.
- Messages like "fix" or "update". They do not say why.

## Check yourself

1. What is a commit? *A snapshot of the tracked files with a message and a pointer to its parent.*
2. Why is `*.tfstate` ignored? *State can contain secrets and belongs to one deployment.*
3. Why is `.terraform.lock.hcl` tracked? *So every machine installs the same provider version.*
4. What does a trailing `/` in `.gitignore` mean? *The pattern matches folders.*
5. What does `git status --short` print on a clean tree? *Nothing.*

## Further reading

- Pro Git book: <https://git-scm.com/book/en/v2>
- `.gitignore` patterns: <https://git-scm.com/docs/gitignore>

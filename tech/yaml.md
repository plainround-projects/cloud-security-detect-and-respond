# YAML

## What it is

YAML is a text format for structured data, like JSON, but written with indentation instead of braces. A line `key: value` is a setting; a nested group is indented; a list item starts with `- `. This repository has one YAML file: the GitHub Actions workflow. It follows YAML 1.2 as GitHub reads it.

## Why this repository uses it

GitHub Actions ([github-actions.md](github-actions.md)) requires its workflows to be written in YAML. The file tells GitHub which steps to run on each push.

## Where it appears

| Path | What it holds |
| --- | --- |
| `.github/workflows/ci.yml` | the CI workflow: name, trigger, job, steps |

## How it works underneath

A YAML parser reads the file line by line and builds nested maps (name to value) and lists. **Indentation is the structure**: two lines with the same indentation are siblings; a deeper line belongs to the line above. Tabs are not allowed for indentation, only spaces. A plain value like `ubuntu-latest` is text; `"3.12"` in quotes forces text (without the quotes, `3.12` would be read as the number 3.12 and `3.10` as 3.1).

## Walkthrough of this repository's use

From `.github/workflows/ci.yml`:

```yaml
name: ci

on: [push, pull_request]

jobs:
  check:
```

- `name: ci` labels the workflow.
- `on: [push, pull_request]` is a list written inline: run on every push and on every pull request.
- `jobs:` is a map; `check:` is the name of the only job, nested one level in.

From `.github/workflows/ci.yml`:

```yaml
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
```

- `steps:` is a list; each `- ` starts one step.
- `uses:` runs a ready-made action. `with:` is a map of that action's inputs.
- `python-version: "3.12"` is quoted so it stays the text `3.12`.

From `.github/workflows/ci.yml`:

```yaml
      - run: make lint
```

`run:` executes a shell command. The editor settings in `.editorconfig` give YAML a two-space indent (see [editorconfig.md](editorconfig.md)).

## Try it yourself

```bash
sed -n 1,8p .github/workflows/ci.yml
```

Expect the lines quoted above; count the spaces to see the structure. YAML is read here only by GitHub; Python's standard library has no YAML parser.

```bash
ruby -ryaml -e 'puts YAML.load_file(".github/workflows/ci.yml")["jobs"]["check"]["steps"].length'
```

If Ruby is installed (it is on macOS), expect `12`: the number of steps in the job.

## Mistakes people make

- Mixing tabs and spaces, or inconsistent indentation. The structure silently changes or the parse fails.
- Leaving `3.12` unquoted, which a YAML parser reads as a number.
- Forgetting the space after the colon (`key:value` is one piece of text).

## Check yourself

1. What shows nesting in YAML? *Indentation with spaces.*
2. What does `- ` at the start of a line mean? *A list item.*
3. Why is `"3.12"` quoted? *To keep it as text and not the number 3.12.*
4. What does `on: [push, pull_request]` mean? *Run the workflow on pushes and pull requests.*
5. Where is YAML used in this repository? *Only in `.github/workflows/ci.yml`.*

## Further reading

- YAML 1.2.2 specification: <https://yaml.org/spec/1.2.2/>
- GitHub's workflow syntax: <https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions>

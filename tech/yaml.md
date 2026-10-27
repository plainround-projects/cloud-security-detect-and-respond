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

This is the only YAML file in the repository. Every line is shown below, in file order. Read the next paragraph first: the whole file is written in the format it describes.

**The YAML format in one paragraph.** YAML stores structured data as plain text, and **indentation is the structure**. A line `key: value` is one entry of a **mapping** (a set of named values). A line that starts with `- ` is one item of a **sequence** (an ordered list). Entries that start in the same column are siblings; a deeper-indented line belongs to the line above it. Only spaces may be used to indent, never tabs. A value on the same line as its key is a **scalar** (text, number or true/false). A list can also be written on one line in square brackets, `[a, b]`, which is called the **flow style**. Quotes around a value force it to be text: `"3.12"` is the text three-point-twelve, whereas an unquoted `3.12` would be read as a number (and `3.10` would become `3.1`, which is wrong). A line that starts with `#` is a comment. Which keys are allowed, and what they mean, is decided by the program that reads the file, not by YAML; here that program is GitHub Actions ([github-actions.md](github-actions.md)).

From `.github/workflows/ci.yml` (line 1):

```yaml
name: ci
```

A mapping entry at the top level. The key is `name` and the value is the scalar `ci`: the label GitHub shows for this workflow in its list of runs.

From `.github/workflows/ci.yml` (line 3):

```yaml
on: [push, pull_request]
```

The key `on` has a **flow-style sequence** as its value: two items, `push` and `pull_request`, on one line. They are the events that start the workflow (what each means is in [github-actions.md](github-actions.md)).

From `.github/workflows/ci.yml` (lines 5 to 8):

```yaml
jobs:
  check:
    name: Lint, unit tests, policy tests, credential-free plans, detection replay, dependency audit
    runs-on: ubuntu-latest
```

`jobs:` has no value on its line, because its value is the indented mapping below it. The next line, indented by two spaces, is `check:`: a key whose value is another mapping, indented by four spaces. That mapping has three entries: `name:` (a scalar: a long label), `runs-on:` (the scalar `ubuntu-latest`) and `steps:`. Because `name` and `runs-on` sit in the same column, they are siblings of `steps`. The word `check` is chosen by the author; it is the identifier of the job.

From `.github/workflows/ci.yml` (line 9):

```yaml
    steps:
```

`steps:` is followed on the next lines by a block-style **sequence**: every step starts with `- ` (a hyphen and a space) at the same indentation. The value of `steps` is therefore a list, and each list item is itself a mapping.

From `.github/workflows/ci.yml` (line 10):

```yaml
      - uses: actions/checkout@v4
```

The first list item is a mapping with one entry: key `uses`, value `actions/checkout@v4` (a single scalar; the `@` has no meaning to YAML).

From `.github/workflows/ci.yml` (lines 11 to 13):

```yaml
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
```

The second item has two entries. The hyphen sits on the line of the first entry (`uses`), and the second entry, `with:`, is indented to line up under `uses` (eight spaces), which is what makes it part of the same item. `with:` has a nested mapping whose single entry is `python-version`, and its value `"3.12"` is quoted so that YAML keeps it as text.

From `.github/workflows/ci.yml` (lines 14 to 17):

```yaml
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.17.0"
          terraform_wrapper: false
```

Same shape: an item with `uses`, and `with` holding a mapping of two entries. `"1.17.0"` is quoted text. `terraform_wrapper: false` is a **boolean**: unquoted `false` is the truth value, not the text "false".

From `.github/workflows/ci.yml` (lines 18 to 20):

```yaml
      - uses: terraform-linters/setup-tflint@v4
        with:
          tflint_version: v0.65.0
```

An item whose `with` mapping has one entry. `v0.65.0` has no quotes and does not need them: YAML reads it as text because of the letter `v`.

From `.github/workflows/ci.yml` (lines 21 to 23):

```yaml
      - uses: open-policy-agent/setup-opa@v2
        with:
          version: 1.21.4
```

An item whose `with` mapping has one entry, `version: 1.21.4`. Unquoted, a value with two dots is read as text, not a number.

From `.github/workflows/ci.yml` (line 24):

```yaml
      - run: pipx install checkov==3.3.30
```

An item with the key `run` instead of `uses`. The value is the whole rest of the line, `pipx install checkov==3.3.30`, read as one text scalar (the `==` is not special in YAML).

From `.github/workflows/ci.yml` (lines 25 to 30):

```yaml
      - run: make lint
      - run: make test
      - run: make validate
      - run: make demo-drill
      - run: make audit
      - run: make test-e2e
```

The remaining 6 items all have the same one-entry shape: `- run: ` followed by a shell command. The commands are `make lint`, `make test`, `make validate`, `make demo-drill`, `make audit`, `make test-e2e`. They are separate list items, so they run one after another in this order.

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

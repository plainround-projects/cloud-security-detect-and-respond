# import-linter

## What it is

import-linter is a command-line tool that checks which Python modules import which other modules, against rules you write down. A rule is called a **contract**. If any import breaks a contract, the tool lists the offending import chain and exits with an error. This repository pins **import-linter 2.15** (it uses a library called `grimp` 3.18 to build the import graph).

## Why this repository uses it

The project's design rule is: the domain (detections, patterns, the timeline, containment rules) depends on nothing; the application depends on the domain; the infrastructure and interfaces depend on both; nothing depends on the interfaces. A rule that only lives in a README gets broken. import-linter makes `make lint` fail when someone makes the domain import a file reader. The second contract matters most here: the rules that decide *what is an attack* must be testable without any cloud library, so `boto3` may not appear in them.

## Where it appears

| Path | What it does with import-linter |
| --- | --- |
| `pyproject.toml` | `[tool.importlinter]` and two contracts |
| `Makefile` | `make lint` runs `lint-imports` |
| `.import_linter_cache/` | cache (ignored by git) |

## How it works underneath

import-linter reads every Python file in the named package and records each `import` statement. That gives a directed graph: an arrow from module A to module B means "A imports B". It then checks each contract against the graph. For indirect imports it follows chains (A imports B, B imports C), so hiding a forbidden import behind a helper does not help.

## Walkthrough of this repository's use

From `pyproject.toml`:

```toml
[tool.importlinter]
root_package = "detect_respond"
include_external_packages = true
```

`root_package` names the package to analyze. `include_external_packages = true` also puts installed libraries (such as `boto3`) into the graph, which the "forbidden" contract below needs.

**Contract 1: layers.**

From `pyproject.toml`:

```toml
[[tool.importlinter.contracts]]
name = "Layers: interfaces -> infrastructure -> application -> domain, never upward"
type = "layers"
layers = [
    "detect_respond.interfaces",
    "detect_respond.infrastructure",
    "detect_respond.application",
    "detect_respond.domain",
]
```

`[[...]]` (double brackets) adds one more item to a list of tables in TOML ([toml.md](toml.md)). A `layers` contract lists modules from highest to lowest. A higher layer may import a lower one; a lower layer may never import a higher one. So `domain` cannot import `application`, and nothing may import `interfaces`.

**Contract 2: forbidden.**

From `pyproject.toml`:

```toml
type = "forbidden"
source_modules = ["detect_respond.domain", "detect_respond.application"]
forbidden_modules = ["boto3", "botocore"]
```

The domain and application layers may not import the AWS libraries, directly or through a chain. Only `infrastructure` imports `boto3` ([boto3.md](boto3.md)), and the application sees it only as the `Revoker` port.

### Every setting, one by one

import-linter reads the table `[tool.importlinter]` for its general settings and one `[[tool.importlinter.contracts]]` entry for each rule. A **contract** is a rule about which module may import which, checked against the real `import` lines of the code. Every key this repository sets:

From `pyproject.toml` (line 78):

```toml
[tool.importlinter]
```

The header of the general table.

From `pyproject.toml` (line 79):

```toml
root_package = "detect_respond"
```

`root_package = "detect_respond"`: the one top-level package to analyze. Everything below it is read; contract module names must start with it (or be an external package).

From `pyproject.toml` (line 80):

```toml
include_external_packages = true
```

`include_external_packages = true`: put installed libraries (such as `boto3`) into the import graph too. By default only the project's own packages are in it, and a contract that names `boto3` could not see any import of it.

From `pyproject.toml` (line 82):

```toml
[[tool.importlinter.contracts]]
```

The header of contract number 1.

From `pyproject.toml` (line 83):

```toml
name = "Layers: interfaces -> infrastructure -> application -> domain, never upward"
```

`name`: the text printed in the report next to KEPT or BROKEN. It is also the one-line statement of the rule.

From `pyproject.toml` (line 84):

```toml
type = "layers"
```

`type = "layers"`: which kind of rule this is. `layers`: modules are stacked from highest to lowest; a higher one may import a lower one, never the other way round.

From `pyproject.toml` (lines 85 to 90):

```toml
layers = [
    "detect_respond.interfaces",
    "detect_respond.infrastructure",
    "detect_respond.application",
    "detect_respond.domain",
]
```

`layers`: the stack, **highest first**: `detect_respond.interfaces`, `detect_respond.infrastructure`, `detect_respond.application`, `detect_respond.domain`. Reading it top to bottom: the command line may use infrastructure, infrastructure may use the application layer, the application layer may use the domain, and no step back up is allowed.

From `pyproject.toml` (line 92):

```toml
[[tool.importlinter.contracts]]
```

The header of contract number 2.

From `pyproject.toml` (line 93):

```toml
name = "Domain and application know nothing about AWS"
```

`name`: the text printed in the report next to KEPT or BROKEN. It is also the one-line statement of the rule.

From `pyproject.toml` (line 94):

```toml
type = "forbidden"
```

`type = "forbidden"`: which kind of rule this is. `forbidden`: the listed source modules must not import the listed forbidden modules, neither directly nor through a chain of other modules.

From `pyproject.toml` (line 95):

```toml
source_modules = ["detect_respond.domain", "detect_respond.application"]
```

`source_modules`: the modules that are held to the rule: `detect_respond.domain`, `detect_respond.application`. Everything below each of them is held to it as well.

From `pyproject.toml` (line 96):

```toml
forbidden_modules = ["boto3", "botocore"]
```

`forbidden_modules`: what the source modules must never import: `boto3`, `botocore`. These are the AWS client libraries, so only the infrastructure layer may talk to AWS.

## Try it yourself

```bash
.venv/bin/lint-imports
```

Expect `Contracts: 2 kept, 0 broken.` with the two contract names marked `KEPT`.

To see a contract break, make the domain import the AWS library and undo it:

```bash
echo "import boto3" >> src/detect_respond/domain/errors.py
.venv/bin/lint-imports | grep -E "BROKEN|boto3"
git checkout src/detect_respond/domain/errors.py
```

Expect `Domain and application know nothing about AWS BROKEN` and the import chain that caused it (`detect_respond.domain.errors -> boto3`). The `git checkout` restores the file. Try `echo "from detect_respond.application import ports" >> src/detect_respond/domain/errors.py` for the layers contract: the report says `detect_respond.domain is not allowed to import detect_respond.application`.

## Mistakes people make

- Listing layers from low to high. The order is highest first.
- Forgetting `include_external_packages` and then wondering why a "forbidden" rule about a library never triggers.
- Testing a rule only when it passes. Break it once on purpose (as above) to see that it can fail.

## Check yourself

1. What is a contract? *One rule about imports, checked against the import graph.*
2. In a `layers` contract, may `domain` import `application`? *No; lower layers cannot import higher ones.*
3. Why is `boto3` in `forbidden_modules`? *So domain and application stay free of cloud libraries and can be tested without a cloud.*
4. How many contracts does this repository have? *Two: layers, and forbidden libraries.*
5. Does import-linter run the code? *No; it reads import statements.*

## Further reading

- import-linter documentation: <https://import-linter.readthedocs.io/en/stable/> (version 2.15)
- Contract types: <https://import-linter.readthedocs.io/en/stable/contract_types.html>

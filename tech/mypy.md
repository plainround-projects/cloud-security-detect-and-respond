# mypy

## What it is

mypy is a **static type checker** for Python. "Static" means it reads your code without running it. It uses the **type hints** you wrote (`def f(a: int) -> str`) to find places where a value of the wrong kind is passed or returned. This repository pins **mypy 2.4.0**.

## Why this repository uses it

The checks in this project decide whether an AWS call is allowed. A wrong type (a `str` where a list was meant) could turn "denied" into "allowed" quietly. mypy in `strict` mode makes such mistakes show up in `make lint` before any test runs.

## Where it appears

| Path | What it does with mypy |
| --- | --- |
| `pyproject.toml` | `[tool.mypy]` and two override blocks |
| `Makefile` | `make lint` runs `mypy` |
| `.mypy_cache/` | mypy's cache (ignored by git) |

## How it works underneath

mypy parses all files, builds a map of every function, class and variable and their declared types, then walks each function body checking that every operation fits those types. It follows imports to other files in the project. For libraries without type information it needs help (see the override below). It never runs the program; a bug that no hint describes is invisible to it.

## Walkthrough of this repository's use

From `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
files = ["src", "tests", "scripts"]
explicit_package_bases = true
mypy_path = ["src"]
```

- `python_version`: check as if running on 3.12.
- `strict = true`: turns on the strictest group of checks: every function needs type hints, no implicit `Any`, no unused ignore comments, and more.
- `files`: what to check when you run bare `mypy`.
- `mypy_path` and `explicit_package_bases`: tell mypy that `src/` is the root where packages such as `detect_respond` start, so it names modules correctly.

From `pyproject.toml`:

```toml
[[tool.mypy.overrides]]
module = ["boto3", "boto3.*", "botocore", "botocore.*"]
ignore_missing_imports = true
```

`boto3` (see [boto3.md](boto3.md)) ships without type information. This block says: for those modules, do not complain that no types were found. The values from boto3 are then treated as `Any`, which is why the code keeps them inside the infrastructure layer.

From `pyproject.toml`:

```toml
[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false
disallow_incomplete_defs = false
disallow_untyped_calls = false
```

Test functions are named for behavior and take pytest fixtures, so requiring a hint on each one adds noise. These three switches relax strictness for the `tests` package only.

A typical hint in the source: `def verify_digest(digest: Mapping[str, Any], read_content: Callable[[str], bytes | None]) -> DigestResult:`. mypy checks every call of `verify_digest` against it, and checks that the function returns a `DigestResult`.

## Try it yourself

```bash
.venv/bin/mypy --version
```

Expect `mypy 2.4.0 (compiled: yes)`.

```bash
.venv/bin/mypy
```

Expect `Success: no issues found in 36 source files`.

```bash
printf 'def f(a: int) -> str:\n    return a\n' > /tmp/demo_mypy.py
.venv/bin/mypy --strict /tmp/demo_mypy.py
```

Expect `error: Incompatible return value type (got "int", expected "str")  [return-value]`.

## Mistakes people make

- Adding `# type: ignore` to silence an error. In this repository `strict` reports unused ignores, and the fix is to correct the type (for example, `calls: list[tuple[str, ...]] = []`).
- Using `Any` to make errors disappear. It switches checking off for that value.
- Believing hints change behavior. They do not; Python ignores them at run time.

## Check yourself

1. Does mypy run the program? *No; it only reads the code and hints.*
2. What does `strict = true` change? *It enables the strictest set of checks, including a hint on every function.*
3. Why is there an override for `boto3`? *boto3 has no type information, so missing-import errors are switched off for it.*
4. Why are tests allowed untyped functions? *Names and fixtures already say what they test; hints add noise there.*
5. What is `mypy_path = ["src"]` for? *It tells mypy where the package roots are.*

## Further reading

- mypy 2.4 documentation: <https://mypy.readthedocs.io/en/stable/>
- Configuration file: <https://mypy.readthedocs.io/en/stable/config_file.html>

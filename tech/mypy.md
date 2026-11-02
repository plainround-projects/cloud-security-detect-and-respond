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
- `strict = true`: turns on the strictest group of checks. In mypy 2.4 it switches on 13 options: `disallow_any_generics` (a container such as `list` must say what it holds), `disallow_subclassing_any` (no class may inherit from something of unknown type), `disallow_untyped_calls` (a typed function may not call an untyped one), `disallow_untyped_defs` (every function needs type hints), `disallow_incomplete_defs` (no function may be half-annotated), `check_untyped_defs` (also check the inside of functions that have no hints), `disallow_untyped_decorators` (a decorator must be typed), `warn_redundant_casts` (report a cast that changes nothing), `warn_unused_ignores` (report a `# type: ignore` comment that is not needed), `warn_return_any` (report a function that returns an untyped value where a type was promised), `no_implicit_reexport` (a name imported into a module is not automatically one of its public names), `strict_equality` (report comparisons between types that can never be equal) and `extra_checks` (a few additional strict rules).
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

### Every setting, one by one

mypy reads the table `[tool.mypy]` and any number of `[[tool.mypy.overrides]]` entries (double brackets add one more item to a list of tables). Every key this repository sets:

From `pyproject.toml` (line 44):

```toml
[tool.mypy]
```

The header of the main mypy table.

From `pyproject.toml` (line 45):

```toml
python_version = "3.12"
```

`python_version`: the Python version to check against; mypy uses the standard library definitions of that version and reports syntax newer than it.

From `pyproject.toml` (line 46):

```toml
strict = true
```

`strict = true`: switch on the whole group of strict checks (listed in the walkthrough above). One word instead of thirteen lines of settings, and a new strict check added in a later mypy release is picked up automatically.

From `pyproject.toml` (line 47):

```toml
files = ["src", "tests", "scripts"]
```

`files`: what to check when mypy runs with no arguments: every `.py` file under these folders.

From `pyproject.toml` (line 48):

```toml
explicit_package_bases = true
```

`explicit_package_bases = true`: tell mypy that a folder named in `mypy_path` is the **base** from which module names are counted, instead of letting it guess from `__init__.py` files. Without it a file such as `src/pkg/a.py` could be seen as the module `src.pkg.a` as well as `pkg.a`, and mypy would report duplicate modules.

From `pyproject.toml` (line 49):

```toml
mypy_path = ["src"]
```

`mypy_path`: extra folders where mypy looks for modules, like Python's import path. `src` is where the packages live (the "src layout").

From `pyproject.toml` (line 51):

```toml
[[tool.mypy.overrides]]
```

The header of one override: settings that apply only to the modules named in its `module` key, on top of the main table.

From `pyproject.toml` (line 52):

```toml
module = ["boto3", "boto3.*", "botocore", "botocore.*"]
```

`module`: which modules this override is about: `boto3`, `boto3.*`, `botocore`, `botocore.*`. A name with `.*` at the end means "that package and everything below it", so `boto3` and `boto3.*` together cover the package and its submodules.

From `pyproject.toml` (line 53):

```toml
ignore_missing_imports = true
```

`ignore_missing_imports = true`: when mypy cannot find type information for these modules, do not report an error; treat what they provide as `Any` (no checking). The AWS libraries do not ship type information, so without this every `import boto3` would be an error.

From `pyproject.toml` (line 56):

```toml
[[tool.mypy.overrides]]
```

The header of one override: settings that apply only to the modules named in its `module` key, on top of the main table.

From `pyproject.toml` (line 57):

```toml
module = ["tests.*"]
```

`module`: which modules this override is about: `tests.*`. A name with `.*` at the end means "that package and everything below it", so `boto3` and `boto3.*` together cover the package and its submodules.

From `pyproject.toml` (line 58):

```toml
disallow_untyped_defs = false
```

`disallow_untyped_defs = false`: switch off, for these modules only, the strict check that forbids a function with no type hints at all. Test functions are named for the behavior they check and take pytest fixtures, so a hint on each adds noise and no safety.

From `pyproject.toml` (line 59):

```toml
disallow_incomplete_defs = false
```

`disallow_incomplete_defs = false`: switch off, for these modules only, the strict check that forbids a function with hints on some parameters but not all. Test functions are named for the behavior they check and take pytest fixtures, so a hint on each adds noise and no safety.

From `pyproject.toml` (line 60):

```toml
disallow_untyped_calls = false
```

`disallow_untyped_calls = false`: switch off, for these modules only, the strict check that forbids a call to a function that has no type hints. Test functions are named for the behavior they check and take pytest fixtures, so a hint on each adds noise and no safety.

**Suppressions in the code.** A comment `# type: ignore[code]` at the end of a line tells mypy "do not report the error named in brackets on this line". Under `strict`, mypy also reports a suppression that is no longer needed (`warn_unused_ignores`). This repository uses it in these places:

- `src/detect_respond/interfaces/cli.py` line 127: `def _run(args: argparse.Namespace):  # type: ignore[no-untyped-def]`. The code in brackets limits the silence to the error `no-untyped-def`: the function has no type hints.
- `tests/unit/detect_respond/test_response.py` line 202: `assert Finding.from_asff({**asff("a", "HIGH"), "Resources": []}).resource == ""  # type: ignore[union-attr]`. The code in brackets limits the silence to the error `union-attr`: the value might be `None` (or another type) that has no such attribute.
- `tests/unit/detect_respond/test_cli_and_plan.py` line 221: `module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]`. The code in brackets limits the silence to the error `arg-type`: the argument might not have the type the function expects.
- `tests/unit/detect_respond/test_cli_and_plan.py` line 223: `spec.loader.exec_module(module)  # type: ignore[union-attr]`. The code in brackets limits the silence to the error `union-attr`: the value might be `None` (or another type) that has no such attribute.

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

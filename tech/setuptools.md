# setuptools

## What it is

setuptools is the library that knows how to turn a Python project into something pip can install. When `pip install -e .` runs, pip asks a **build backend** to prepare the project; here the backend is setuptools. The version is not pinned in a lock (it is only needed while building); `pyproject.toml` asks for `setuptools>=75`.

## Why this repository uses it

The repository has one package under `src/` (`detect_respond`) and one command (`detect-respond`). Installing the project makes the packages importable everywhere in the venv, and creates the command. setuptools is the standard, plain choice for that.

## Where it appears

| Path | What it does with setuptools |
| --- | --- |
| `pyproject.toml` | `[build-system]` names setuptools; `[tool.setuptools.packages.find]` says where packages are |

## How it works underneath

pip reads `[build-system]` first. It creates a temporary isolated environment, installs what `requires` lists, then calls the named `build-backend`. For an editable install the backend writes a small link into the venv's `site-packages` that points at `src/`. It also writes the installed **metadata** (name, version, dependencies, entry points).

## Walkthrough of this repository's use

From `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"
```

`requires` lists what the build needs. `build-backend` names the Python object pip calls to do the build.

From `pyproject.toml`:

```toml
[tool.setuptools.packages.find]
where = ["src"]
```

setuptools searches the folder `src` for packages (folders with `__init__.py`). This is the "src layout": the importable code is not at the repository root, so tests cannot accidentally import the source folder instead of the installed package.

From `pyproject.toml`:

```toml
[project.scripts]
detect-respond = "detect_respond.interfaces.cli:main"
```

This creates a command named `detect-respond` in `.venv/bin/`. It imports `detect_respond.interfaces.cli` and calls `main()`.

### Every setting, one by one

`pyproject.toml` has three groups of tables that setuptools and pip read: `[build-system]` (how to build), `[project]` (what the project is) and `[tool.setuptools...]` (settings private to setuptools). Every key this repository sets, in file order:

From `pyproject.toml` (line 1):

```toml
[build-system]
```

The header of the table that says how to build the project.

From `pyproject.toml` (line 2):

```toml
requires = ["setuptools>=75"]
```

`requires`: what must be installed before the build can start. `setuptools>=75` means "setuptools, version 75 or newer". The operators of a version requirement: `>=` at least, `<` below, `==` exactly, `,` joins two conditions that must both hold.

From `pyproject.toml` (line 3):

```toml
build-backend = "setuptools.build_meta"
```

`build-backend`: the Python object pip calls to run the build, written `module.object`. `setuptools.build_meta` is setuptools' implementation of the standard build interface.

From `pyproject.toml` (line 5):

```toml
[project]
```

The header of the table with the project's identity and requirements.

From `pyproject.toml` (line 6):

```toml
name = "cloud-security-detect-and-respond"
```

`name`: the name the project is installed under and would have on a package index: `cloud-security-detect-and-respond`. Not the same as the import name of the package, which comes from the folder under `src`.

From `pyproject.toml` (line 7):

```toml
version = "0.1.0"
```

`version = "0.1.0"`: the release number (major, minor, patch). It is shown by `pip list` and written into the installed metadata.

From `pyproject.toml` (line 8):

```toml
description = "Detection and response for a cloud account: detections as code, a timeline rebuilt from the logs, and containment from the evidence."
```

`description`: one sentence for package listings and for `pip show`.

From `pyproject.toml` (line 9):

```toml
readme = "README.md"
```

`readme = "README.md"`: the file whose text becomes the long description of the package.

From `pyproject.toml` (line 10):

```toml
requires-python = ">=3.12"
```

`requires-python = ">=3.12"`: the Python versions the project supports. pip refuses to install it on an older Python, and the tools in this file (ruff `target-version`, mypy `python_version`) match it.

From `pyproject.toml` (line 11):

```toml
license = { text = "MIT" }
```

`license = { text = "MIT" }`: the licence, given inline as text. The braces make a small table in one line (an **inline table**). The full text is in the `LICENSE` file.

From `pyproject.toml` (line 12):

```toml
authors = [{ name = "Sumit Srivastava" }]
```

`authors`: a list of people, each an inline table with a `name` (and optionally an `email`).

From `pyproject.toml` (line 13):

```toml
dependencies = ["boto3>=1.35,<2"]
```

`dependencies`: the libraries the **running** program needs. `boto3>=1.35,<2` means "boto3 1.35 or newer but below 2.0" ([boto3.md](boto3.md)): new features of the 1.x line are welcome, an incompatible 2.0 is not. pip installs these with the project.

From `pyproject.toml` (line 15):

```toml
[project.optional-dependencies]
```

The header of the table of optional groups.

From `pyproject.toml` (lines 16 to 23):

```toml
dev = [
    "pytest>=8,<10",
    "pytest-cov>=5",
    "ruff>=0.6",
    "mypy>=1.11",
    "import-linter>=2.0",
    "pip-audit>=2.7",
]
```

`dev`: a group named `dev` of libraries needed to **work on** the project, not to run it. pip installs them only when asked, as `pip install -e ".[dev]"` (the name in the brackets is the group). Each entry:
- `pytest>=8,<10`: the test runner ([pytest.md](pytest.md)); the requirement after the name says which versions are accepted.
- `pytest-cov>=5`: the plug-in that connects pytest to coverage.py ([coverage.md](coverage.md)); the requirement after the name says which versions are accepted.
- `ruff>=0.6`: the linter and formatter ([ruff.md](ruff.md)); the requirement after the name says which versions are accepted.
- `mypy>=1.11`: the type checker ([mypy.md](mypy.md)); the requirement after the name says which versions are accepted.
- `import-linter>=2.0`: the import-rule checker ([import-linter.md](import-linter.md)); the requirement after the name says which versions are accepted.
- `pip-audit>=2.7`: the scanner for known vulnerabilities in dependencies ([pip-audit.md](pip-audit.md)); the requirement after the name says which versions are accepted.

From `pyproject.toml` (line 25):

```toml
[project.scripts]
```

The header of the table that makes commands.

From `pyproject.toml` (line 26):

```toml
detect-respond = "detect_respond.interfaces.cli:main"
```

`detect-respond = "detect_respond.interfaces.cli:main"`: when the project is installed, pip creates a command `detect-respond` in the environment's `bin` folder. The text on the right is `module:function`: the command imports `detect_respond.interfaces.cli` and calls `main()`; its return value becomes the exit code.

From `pyproject.toml` (line 28):

```toml
[tool.setuptools.packages.find]
```

The header of the table that tells setuptools how to find the packages.

From `pyproject.toml` (line 29):

```toml
where = ["src"]
```

`where = ["src"]`: search for packages (folders with an `__init__.py`) only inside `src`. This is the "src layout": the importable code is not at the repository root, so a test cannot import the source folder by accident instead of the installed package.

## Try it yourself

```bash
.venv/bin/detect-respond --help
```

Expect the usage text with the commands `scan`, `drill`, `review`, `contain`, `verify-archive`, `posture` and `audit-rules`.

```bash
.venv/bin/python -c "import detect_respond; print(detect_respond.__file__)"
```

Expect a path under `src/detect_respond/` — the editable link.

```bash
ls .venv/lib/python3.13/site-packages | grep -i cloud_security
```

Expect the editable-install marker files for this project.

## Mistakes people make

- Putting packages at the repository root and importing the wrong copy in tests. The `src` layout avoids it.
- Forgetting `__init__.py` in a new folder, so `find` does not see it as a package.
- Expecting `pip install -e .` to install dev tools. Those come from the lock file.

## Check yourself

1. What does `build-backend` do? *Names the program pip calls to build or install the project.*
2. Why is the code in `src/`? *So imports in tests come from the installed package, not the folder.*
3. How does the `detect-respond` command exist? *`[project.scripts]` makes pip create it at install time.*
4. What does `packages.find` do? *Looks for packages under `where`.*
5. Where do libraries get pinned? *In the lock files, not in setuptools settings.*

## Further reading

- setuptools documentation: <https://setuptools.pypa.io/en/stable/>
- `pyproject.toml` specification: <https://packaging.python.org/en/latest/specifications/pyproject-toml/>

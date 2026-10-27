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

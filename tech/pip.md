# pip, virtual environments and the lock files

## What it is

**pip** is the program that installs Python libraries from the Python Package Index (PyPI), the public shelf of Python packages. A **virtual environment** is a folder (here `.venv/`) with its own interpreter and its own installed libraries. A **lock file** is a text file that lists the exact version of every library to install, so every machine gets the same ones. This repository uses **pip 26.2.2** (the version that came with the Python 3.13 venv on the verification machine) and two lock files: `requirements.lock` and `requirements-dev.lock`.

## Why this repository uses it

A security project must be reproducible and must not install something unexpected. Each lock file pins every library and every transitive library (a library that another library needs) to one version, and records the **hash** (a fingerprint) of each downloadable file. pip with `--require-hashes` refuses to install a file whose fingerprint does not match.

## Where it appears

| Path | What it does |
| --- | --- |
| `requirements.lock` | the libraries the function needs at run time (boto3 and what it needs) |
| `requirements-dev.lock` | the run-time libraries plus the development tools (pytest, ruff, mypy and so on) |
| `Makefile` | the `$(STAMP)` target creates `.venv` and installs from the dev lock |
| `.github/workflows/ci.yml` | CI runs `make`, which does the same install |

## How it works underneath

`python -m venv .venv` copies (or links) the interpreter into `.venv/bin/` and creates an empty folder for libraries. `pip install` downloads a **wheel** (a ready-to-unpack archive) or a source archive from PyPI, checks it, and unpacks it into the venv's `site-packages` folder. A **hash** is the SHA-256 fingerprint of a file: change one byte and the fingerprint changes. `pip install -e .` ("editable") installs this project itself by linking to the source folder, so edits take effect without reinstalling.

## Walkthrough of this repository's use

From `Makefile`:

```make
$(STAMP): requirements-dev.lock pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -q --require-hashes -r requirements-dev.lock
	$(VENV)/bin/pip install -q --no-deps -e .
	touch $@
```

- The first line is a Make rule (see [make.md](make.md)): the file `.venv/.installed` is rebuilt whenever either lock file or `pyproject.toml` is newer than it.
- `-m venv .venv` creates the virtual environment.
- `-q` means quiet. `--require-hashes` makes pip refuse any requirement without a hash in the file, and any file whose hash does not match. `-r` reads requirements from the file.
- `--no-deps -e .` installs this project in editable mode and tells pip not to look for dependencies: they are already installed from the lock.
- `touch $@` creates the stamp file so Make knows the install is done (`$@` means the rule's target).

A lock entry looks like this (shortened):

From `requirements.lock`:

```text
boto3==1.43.119 \
    # via cloud-security-detect-and-respond (pyproject.toml)
```

`==1.43.119` pins the exact version. The backslash continues the line. The indented `--hash=sha256:...` lines (many per library: one per downloadable file for each operating system) list the allowed fingerprints. The `# via` comments say why a library is present.

The file was made by [uv](uv.md), not written by hand. The first line says so.

## Try it yourself

```bash
.venv/bin/pip --version
```

Expect `pip 26.2.2 from .../.venv/lib/python3.13/site-packages/pip (python 3.13)`.

```bash
.venv/bin/pip show cloud-security-detect-and-respond | sed -n 1,3p
```

Expect the project name, `Version: 0.1.0` and its summary: the editable install.

```bash
.venv/bin/pip list | sed -n 1,5p
```

Expect a table of installed libraries; `boto3 1.43.119` is among them.

```bash
grep -c "^    --hash" requirements.lock
```

Prints `14`: the number of fingerprints the run-time lock holds.

## Mistakes people make

- Installing with plain `pip install boto3`, which takes whatever version is newest today. Use the lock.
- Editing a lock file by hand. Regenerate it with `uv pip compile` instead (see [uv.md](uv.md)).
- Running pip outside the venv and changing the system Python. Use `.venv/bin/pip`.
- Forgetting that `--require-hashes` needs every dependency listed. That is why the lock includes transitive ones.

## Check yourself

1. What is a lock file for? *To pin every library to one version so installs are identical.*
2. What does `--require-hashes` do? *Refuses to install any file whose fingerprint is not listed.*
3. What does `-e .` do? *Installs this project in editable mode, linked to its source folder.*
4. Why is `--no-deps` used on the second install? *The dependencies are already installed from the hashed lock.*
5. What does `touch $@` do in the Makefile? *Creates the stamp file that records the install is up to date.*

## Further reading

- pip 26.2 documentation: <https://pip.pypa.io/en/stable/>
- Secure installs and hash-checking mode: <https://pip.pypa.io/en/stable/topics/secure-installs/>
- Virtual environments: <https://docs.python.org/3.12/library/venv.html>

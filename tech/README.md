# Technology notes

One file for every technology this repository uses, written for a reader who has never met any of them. Each file explains what the technology is, why the lesson needs it, where it appears here, how it works underneath, then walks through this repository's own files line by line, with commands you can run and questions to check yourself.

The repository is detection and response for a cloud account: detections written as data (one JSON file each), a tamper-resistant log archive in a second account, a timeline rebuilt from the logs, two measured times (to detect, to contain) and a containment step. See the [README](../README.md) for the lesson and [ARCHITECTURE.md](../ARCHITECTURE.md) for the design.

## If you have ten minutes

1. [aws-eventbridge.md](aws-eventbridge.md): how a detection is a rule, a pattern and a target, and why there are three copies of it.
2. [aws-cloudtrail.md](aws-cloudtrail.md): the audit log, the digests that prove it was not changed, and why it leaves the account.
3. [aws-iam.md](aws-iam.md): the weakness the drill plants, and the policy that contains it.

## Reading order

**The language and its building blocks**

| File | Role in this repository |
| --- | --- |
| [python.md](python.md) | the language of `src/`, `tests/` and the fixture generator |
| [json.md](json.md) | the format of detections, audit records, digests, findings and plans |
| [toml.md](toml.md) | `pyproject.toml`, the project's single settings file |
| [setuptools.md](setuptools.md) | turns the source folders into an installable package and a command |
| [pip.md](pip.md) | installs from the hash-pinned lock files into `.venv` |
| [uv.md](uv.md) | regenerates the lock files |
| [boto3.md](boto3.md) | how containment calls IAM |

**Quality checks and tests**

| File | Role |
| --- | --- |
| [pytest.md](pytest.md) | runs the tests |
| [coverage.md](coverage.md) | measures which lines the tests ran |
| [ruff.md](ruff.md) | lints and formats the Python |
| [mypy.md](mypy.md) | checks the type hints |
| [import-linter.md](import-linter.md) | enforces the layering rule and keeps AWS libraries out of the rules |
| [pip-audit.md](pip-audit.md) | checks pinned libraries for known vulnerabilities |

**Infrastructure as code and policy as code**

| File | Role |
| --- | --- |
| [terraform.md](terraform.md) | describes the cloud resources in two accounts; produces the offline plans |
| [terraform-aws-provider.md](terraform-aws-provider.md) | the plug-in that knows AWS, its Region aliases, and how plans work without credentials |
| [tflint.md](tflint.md) | lints the Terraform |
| [checkov.md](checkov.md) | scans the Terraform for security weaknesses |
| [opa-rego.md](opa-rego.md) | policy rules on both plans, with tests |

**The AWS services the lesson builds**

| File | Role |
| --- | --- |
| [aws-iam.md](aws-iam.md) | the drill's weakness and the deny-before-now containment policy |
| [aws-sts.md](aws-sts.md) | temporary credentials, session names and "who am I" |
| [aws-s3.md](aws-s3.md) | the locked log archive |
| [aws-kms.md](aws-kms.md) | the archive key held by the security account |
| [aws-cloudtrail.md](aws-cloudtrail.md) | the audit log and its digest files |
| [aws-eventbridge.md](aws-eventbridge.md) | the detection rules, per Region |
| [aws-sns.md](aws-sns.md) | the topics that email the alerts |
| [aws-config.md](aws-config.md) | records configuration for the posture controls |
| [aws-security-hub.md](aws-security-hub.md) | the findings behind the posture baseline |
| [aws-budgets.md](aws-budgets.md) | the cost alarm |
| [aws-cli.md](aws-cli.md) | the command-line tool the runbook uses |

**Shell, build and automation**

| File | Role |
| --- | --- |
| [bash.md](bash.md) | the runbook scripts under `scripts/` |
| [unix-tools.md](unix-tools.md) | `date`, `awk`, `sed`, `tee` and friends inside those scripts |
| [shellcheck.md](shellcheck.md) | lints the scripts |
| [make.md](make.md) | the short commands (`make validate`, `make demo-drill`, ...) |
| [github-actions.md](github-actions.md) | runs the same commands on every push |
| [yaml.md](yaml.md) | the format of the workflow file |

**Housekeeping**

| File | Role |
| --- | --- |
| [git.md](git.md) | history, and what is kept out of it |
| [editorconfig.md](editorconfig.md) | whitespace rules for editors |
| [markdown-and-mermaid.md](markdown-and-mermaid.md) | the documentation format, the generated review and the diagram |

Every quoted block introduced by "From `path`" is copied line for line from that file in this repository. If you change the file, update the note.

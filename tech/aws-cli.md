# The AWS command-line interface (AWS CLI)

## What it is

The AWS CLI is the official command-line program for calling AWS: `aws <service> <operation> --option value`. Each command makes the same API call that a program library or the console would, and prints the answer, by default as JSON. This repository's scripts assume **AWS CLI version 2** (verified with 2.34.23).

## Why this repository uses it

The runbook is a drill with two accounts, and the CLI is how a person works in each: deploy, check the archive, plant the weakness, attack, contain, collect. A CLI call is also the plainest proof of a claim: "an administrator cannot delete a log file" is shown by running the delete and reading the refusal. The CLI also has commands the Python code cannot replace, such as `cloudtrail validate-logs`, which checks the provider's signature on the digest files.

## Where it appears

| Path | What it does with the CLI |
| --- | --- |
| `scripts/lib.sh` | `sts get-caller-identity` to prove which account a profile belongs to |
| `scripts/03-verify-archive.sh` | `sns create-topic`, `s3 ls`, `s3api delete-object`, `cloudtrail validate-logs` |
| `scripts/04-drill-setup.sh` | `iam create-access-key`, `configure set` for the `drill` profile, `iam list-*` |
| `scripts/05-posture-baseline.sh` | `securityhub get-findings` |
| `scripts/07-drill-attack.sh` | `sts assume-role` and the attacker's calls |
| `scripts/09-collect-and-measure.sh` | `s3 sync` of the archive to a local folder |
| `scripts/10-teardown.sh` | `iam delete-access-key`, `resourcegroupstaggingapi get-resources` |

## How it works underneath

The CLI reads a **profile** (named settings and credentials, from `~/.aws/` files) or environment variables, builds the API request from your command, signs it and prints the response. Useful switches: `--query` filters the JSON answer with a small query language called JMESPath; `--output text` prints values separated by tabs; `--region` picks the region; `help` after any command shows its manual. Errors print the AWS error code and message, for example `An error occurred (AccessDenied) when calling the DeleteObject operation: ...`, and the program exits with a non-zero code, which scripts read. The environment variable `AWS_PROFILE` chooses the profile for every command in a shell.

## Walkthrough of this repository's use

From `scripts/lib.sh`:

```bash
  export AWS_PROFILE="${!profile_var}"
  identity="$(aws sts get-caller-identity --query '[Account,Arn]' --output text)"
```

`use_account` sets `AWS_PROFILE` for the rest of the script (the account to work in), then asks STS who that is ([aws-sts.md](aws-sts.md)). If the answer is not the account the person named, the script stops ([bash.md](bash.md)). Two accounts, two profiles, one guard.

From `scripts/03-verify-archive.sh`:

```bash
version="$(aws s3api list-object-versions --bucket "$bucket" --prefix "$key" --query 'Versions[0].VersionId' --output text)"
```

`s3api` maps one-to-one onto API operations (`aws s3` has friendlier copy commands). `--query 'Versions[0].VersionId'` takes the first version's id. The next line tries `s3api delete-object --bucket ... --key ... --version-id ...` and the script requires the answer to contain `AccessDenied` ([aws-s3.md](aws-s3.md)).

From `scripts/04-drill-setup.sh`:

```bash
  read -r key_id secret < <(aws iam create-access-key --user-name "$DRILL_USER" --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)
  aws configure set aws_access_key_id "$key_id" --profile drill
```

Creates the drill user's key and stores it straight into the CLI profile `drill`. The secret is never printed or written to a project file; `unset secret` follows. `aws configure set NAME VALUE --profile P` writes one setting to the credentials file.

From `scripts/05-posture-baseline.sh`:

```bash
aws securityhub get-findings --region "$REGION" --max-items 1000 \
```

Reads the open findings; the filter that follows is a JSON string given as the argument `--filters` ([aws-security-hub.md](aws-security-hub.md)). The output is saved with `tee` and counted.

From `scripts/09-collect-and-measure.sh`:

```bash
aws s3 sync "s3://$(archive_bucket)/AWSLogs/" "${EVIDENCE_DIR}/archive/AWSLogs/" --only-show-errors
```

`s3 sync` copies only what is new or changed. The archive is then read by Python from this local folder, so the analysis needs no cloud access.

From `scripts/10-teardown.sh`:

```bash
aws resourcegroupstaggingapi get-resources --region "$REGION" --tag-filters Key=project,Values=detect-and-respond \
```

Lists every resource that still carries the project tag, found by the default tag the provider adds ([terraform-aws-provider.md](terraform-aws-provider.md)).

## Try it yourself

```bash
aws --version
```

Expect `aws-cli/2.` followed by the version (verified with 2.34.23).

```bash
aws cloudtrail validate-logs help | sed -n 1,4p
```

Opens the manual for `validate-logs` (the first lines are the page title, printed with backspace characters). No account is needed to read it.

```bash
f=$(mktemp)
env -u AWS_PROFILE AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_EC2_METADATA_DISABLED=true aws s3 cp "$f" s3://example-bucket-xyz/a.txt --dryrun
rm "$f"
```

Expect a line starting `(dryrun) upload:` and ending `to s3://example-bucket-xyz/a.txt`. `--dryrun` shows what a copy would do without calling AWS, so it needs no credentials.

```bash
env -u AWS_PROFILE AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_EC2_METADATA_DISABLED=true aws sts get-caller-identity >/dev/null 2>&1; echo "exit $?"
```

Expect `exit 253` (or another non-zero code): a CLI call without credentials fails, and the exit code says so.

## Mistakes people make

- Running a script against the wrong account. `use_account` checks first.
- Leaving the attacker's `AWS_PROFILE=drill` set in your shell and then running responder commands as the attacker. `07-drill-attack.sh` exports it only inside the script.
- Printing a secret or session token to the terminal. They are secrets until they expire.
- Using `delete-access-key` where `update-access-key --status Inactive` would do. Deleting destroys evidence.
- Forgetting `--query` and parsing JSON by hand with `grep`.

## Check yourself

1. What does `--query` do? *Filters the JSON answer with a JMESPath expression.*
2. How does a script choose the account to act on? *By setting `AWS_PROFILE`, then checking the account with `sts get-caller-identity`.*
3. What is the difference between `aws s3` and `aws s3api`? *`s3` has friendly copy commands; `s3api` maps one-to-one onto API operations.*
4. Why does `09-collect-and-measure.sh` sync the archive locally? *So the analysis in Python runs on files with no cloud access.*
5. What does a non-zero exit code from the CLI usually mean? *The call failed, for example refused with `AccessDenied`.*

## Further reading

- AWS CLI v2 user guide: <https://docs.aws.amazon.com/cli/latest/userguide/>
- Command reference: <https://docs.aws.amazon.com/cli/latest/reference/>
- JMESPath (the `--query` language): <https://jmespath.org/>

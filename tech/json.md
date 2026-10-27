# JSON

## What it is

JSON (JavaScript Object Notation) is a text format for structured data. It has only a few building blocks: **objects** (`{ "key": value }`, a set of named values), **arrays** (`[a, b, c]`, an ordered list), strings in double quotes, numbers, `true`, `false` and `null`. Almost every language can read and write it, and so can AWS.

## Why this repository uses it

Detection and response is the reading of JSON. The audit log is JSON, the detection rules are JSON, the event pattern that a rule uses is JSON, the digest files that prove the log was not changed are JSON, the posture findings are JSON and so is the Terraform plan. In this repository the detections are *data*: one JSON file each, read by the Python matcher, replayed by the tests and deployed unchanged by Terraform.

## Where it appears

| Path | What it holds |
| --- | --- |
| `detections/d1-*.json` to `d5-*.json` | the five detections: id, title, severity, first step, where they run and the event pattern |
| `fixtures/drill/AWSLogs/` | the synthetic audit archive: log files and digest files, as compressed JSON (`.json.gz`) |
| `fixtures/drill/alerts.json` | when each alert reached the responder |
| `fixtures/posture/*.json` | posture findings in the security service's format (`{"Findings": [...]}`) and the accepted risks |
| `docs/posture-acceptances.json` | accepted risks with a reason |
| `build/security.json`, `build/workload.json` (generated) | `terraform show -json` output of each environment |
| `src/detect_respond/domain/events.py` | parses an audit record |
| `src/detect_respond/infrastructure/` | `log_archive.py`, `files.py` and `plan_audit.py` read the files above |
| `infra/environments/workload/main.tf` | `jsondecode(file(...))` loads the detection files ([terraform.md](terraform.md)) |
| `policy/detection.rego` | uses `json.unmarshal` on policy text ([opa-rego.md](opa-rego.md)) |

## How it works underneath

JSON is only text. A program **parses** the text into its own structures (in Python, a `dict` for an object and a `list` for an array) and later **serializes** structures back to text. Two details matter here. Keys must be in double quotes. An AWS policy or an event pattern is often carried as a *string inside* JSON (Terraform stores a rule's `event_pattern` as one string attribute), so it must be parsed a second time.

## Walkthrough of this repository's use

**A detection is a JSON file.**

From `detections/d1-new-long-lived-credential.json`:

```json
  "id": "D1",
  "title": "new long-lived credential",
  "severity": "high",
```

Metadata for people and for the alert text. The rest of the file holds `firstStep`, `prevention`, `deployTo` (which Regions the rule runs in) and the `pattern`.

From `detections/d1-new-long-lived-credential.json`:

```json
    "detail": {
      "eventSource": [
        "iam.amazonaws.com"
      ],
      "eventName": [
        "CreateAccessKey",
        "CreateLoginProfile"
      ]
    }
```

The **event pattern**: a field matches when its value is *one of* the listed values (every value is in a list). Nested objects mirror the event's own shape. See [aws-eventbridge.md](aws-eventbridge.md) for the pattern language.

**A placeholder inside a pattern.**

From `detections/d5-honeytoken-used.json`:

```json
  "parameters": [
    "__HONEYTOKEN_ACCESS_KEY_ID__"
  ],
```

Detection D5 cannot be complete until the honeytoken's key id is known. The file names the placeholder, and the code and the Terraform replace it. Until it is replaced, the detection never fires.

**An audit record.** The fields the code reads are `eventID`, `eventTime`, `eventName`, `eventSource`, `awsRegion`, `userIdentity` (who, with the `arn` and `accessKeyId`), `sourceIPAddress`, `userAgent`, an optional `errorCode`, and `requestParameters`.

From `src/detect_respond/domain/events.py`:

```python
        if "CloudTrailEvent" in record:
            record = json.loads(record["CloudTrailEvent"])
```

The command `aws cloudtrail lookup-events` wraps each record as a JSON *string* in a field called `CloudTrailEvent`. The code unwraps it with a second `json.loads`.

**A digest file.** It lists, for each log file, its path (`s3Object`) and its SHA-256 fingerprint (`hashValue`), and is how `verify-archive` notices tampering ([aws-cloudtrail.md](aws-cloudtrail.md)).

From `src/detect_respond/domain/digest.py`:

```python
    entries = digest.get("logFiles", [])
```

**Compressed JSON.** The archive stores files as `.json.gz`.

From `src/detect_respond/infrastructure/log_archive.py`:

```python
    opener = gzip.open if path.suffix == ".gz" else open
```

A function can be stored in a variable: `opener` is either `gzip.open` or `open`, and the next line uses it the same way for both. The mode `"rt"` means "read as text".

**Terraform reads the same files.**

From `infra/environments/workload/main.tf`:

```hcl
    jsondecode(file("${local.detections_dir}/${file}")).id => jsondecode(file("${local.detections_dir}/${file}"))
```

`file()` reads the text, `jsondecode()` turns it into a value and `.id` takes the detection's id. So the pattern that Python tested is the pattern Terraform deploys, and `audit-rules` checks that the plan agrees ([aws-eventbridge.md](aws-eventbridge.md)).

**Python's `json` module.** `json.loads(text)` turns text into data, `json.load(file)` reads from an open file, `json.dumps(data)` turns data into text.

## Try it yourself

```bash
python3 -c "import json, glob; d = [json.load(open(p)) for p in sorted(glob.glob('detections/d*.json'))]; print([(x['id'], x['severity']) for x in d])"
```

Expect `[('D1', 'high'), ('D2', 'critical'), ('D3', 'critical'), ('D4', 'medium'), ('D5', 'critical')]`.

```bash
python3 -m json.tool detections/d5-honeytoken-used.json | sed -n 1,5p
```

Expect the file pretty-printed, starting `{`, `"id": "D5",`, `"title": "honeytoken used",`.

```bash
.venv/bin/python -m detect_respond verify-archive --archive fixtures/drill; echo "exit $?"
```

Expect `digest 1: 3 files checked, 0 changed, 0 missing`, then `every logged file matches its digest` and `exit 0`: the digest file's fingerprints match the three log files.

```bash
python3 -c "import json; json.loads('{\"a\": 1,}')"
```

Expect an error (`Illegal trailing comma before end of object`): a trailing comma is not valid JSON.

## Mistakes people make

- A trailing comma or a comment. JSON allows neither.
- Single quotes. Only double quotes are valid.
- Forgetting that an event pattern or a policy inside a Terraform plan is a string, and reading it as an object.
- Comparing JSON text instead of parsed data. Key order and spacing differ; compare the parsed values.
- Forgetting that every value in an event pattern is in a list, even a single one.

## Check yourself

1. What are the two container types in JSON? *Objects (named values) and arrays (ordered lists).*
2. Why is a detection a data file and not code? *So the same pattern is tested in Python and deployed unchanged by Terraform.*
3. What does a digest file hold? *The path and SHA-256 fingerprint of every log file it covers.*
4. What is the `CloudTrailEvent` field? *A JSON string holding the whole record, which `lookup-events` adds around each record.*
5. What does `.json.gz` mean? *JSON text compressed with gzip.*

## Further reading

- JSON specification (ECMA-404): <https://www.json.org/json-en.html>
- Python `json` module (3.12): <https://docs.python.org/3.12/library/json.html>
- Terraform `jsondecode`: <https://developer.hashicorp.com/terraform/language/functions/jsondecode>

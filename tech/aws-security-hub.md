# AWS Security Hub

## What it is

Security Hub collects **security findings** in one place. A finding is a record that says "this resource fails this control" (or that something suspicious happened), with a severity from LOW to CRITICAL, a title and the affected resource. A **standard** is a list of controls to check; this repository subscribes to AWS Foundational Security Best Practices. Findings use one shared JSON format, the **AWS Security Finding Format** (ASFF).

## Why this repository uses it

The lesson's third step is a **posture baseline**: before the incident, count the open critical and high findings, fix what matters, and for every finding you accept, write a reason. That makes "the account was weak in these ways and we knew" a recorded decision and not a surprise. Security Hub produces the findings; this repository's Python reads them and does the counting.

## Where it appears

| Path | What it does |
| --- | --- |
| `infra/modules/posture/main.tf` | enables Security Hub and subscribes to the standard |
| `scripts/05-posture-baseline.sh` | `aws securityhub get-findings` into `before.json` and `after.json` |
| `src/detect_respond/domain/posture.py` | parses a finding and computes the baseline |
| `fixtures/posture/` | synthetic findings before and after fixing, and the accepted risks |
| `docs/posture-acceptances.json` | accepted risks, each with a reason and a date |

## How it works underneath

Security Hub evaluates controls with the help of Config's records ([aws-config.md](aws-config.md)); the first full scan takes minutes to hours. Each finding has a `Compliance.Status` (`PASSED` or `FAILED`) and a `Workflow.Status` (`NEW`, `NOTIFIED`, `SUPPRESSED`, `RESOLVED`). A finding that someone fixed becomes `PASSED`; one a person decides to ignore is `SUPPRESSED`.

## Walkthrough of this repository's use

From `infra/modules/posture/main.tf`:

```hcl
resource "aws_securityhub_account" "this" {
  depends_on = [aws_config_configuration_recorder_status.this]
}
```

Turns Security Hub on for the account, after the recorder is on.

From `infra/modules/posture/main.tf`:

```hcl
  standards_arn = "arn:aws:securityhub:${var.region}::standards/aws-foundational-security-best-practices/v/1.0.0"
```

Subscribes to the standard. After this, the controls of the standard produce findings.

From `src/detect_respond/domain/posture.py`:

```python
        if raw.get("Compliance", {}).get("Status") != "FAILED":
            return None
        if raw.get("Workflow", {}).get("Status") in {"SUPPRESSED", "RESOLVED"}:
            return None
```

Only an *open failure* counts. A finding that passed, or that someone resolved or suppressed, is dropped. `raw.get("Compliance", {})` returns an empty dictionary when the key is missing, so `.get("Status")` still works.

From `src/detect_respond/domain/posture.py`:

```python
    critical = tuple(f.finding_id for f in open_after if f.severity == "CRITICAL")
    reasonless = tuple(sorted(fid for fid, a in accepted_ids.items() if not a.reason.strip()))
```

The two numbers that decide success: critical findings still open after fixing, and acceptances that have no reason. `a.reason.strip()` is empty for a reason made of spaces only. The baseline "meets done-when" only if both lists are empty.

From `scripts/05-posture-baseline.sh`:

```bash
aws securityhub get-findings --region "$REGION" --max-items 1000 \
```

Reads the open findings (the script's filter keeps `FAILED`, `NEW` or `NOTIFIED`, `ACTIVE`) and saves them as the before or after file ([aws-cli.md](aws-cli.md)).

## Try it yourself

```bash
.venv/bin/python -m detect_respond posture --findings fixtures/posture --accepted fixtures/posture/accepted.json; echo "exit $?"
```

Expect a table with a row for each severity: `critical` has 2 at the start and 0 after fixing, `high` has 7 at the start, 2 after fixing and 5 accepted with a reason, and `exit 0`.

```bash
python3 -c "
import json
print(len(json.load(open('fixtures/posture/before.json'))['Findings']), len(json.load(open('fixtures/posture/after.json'))['Findings']))"
```

Expect `9 7`: nine findings at the start, seven left after fixing (of which five are accepted).

## Mistakes people make

- Reading the first scan too early. It takes minutes to hours.
- Accepting a risk with no reason. The tool counts a reasonless acceptance as a failure.
- Counting `PASSED` findings. Only `FAILED` ones are open.
- Fixing the number instead of the weakness: a suppressed finding disappears from the count but is still a weakness.
- Leaving Security Hub on. It bills while it exists.

## Check yourself

1. What is a finding? *A record that a resource fails a control, with a severity and the resource.*
2. Which findings does the baseline count? *Failed ones that are not suppressed or resolved.*
3. What makes the baseline meet "done when"? *No critical finding is left open, and every acceptance has a reason.*
4. Why does Security Hub need Config? *Its controls evaluate resource configuration recorded by Config.*
5. What is ASFF? *The shared JSON format for Security Hub findings.*

## Further reading

- Security Hub user guide: <https://docs.aws.amazon.com/securityhub/latest/userguide/>
- ASFF: <https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-findings-format.html>
- Terraform `aws_securityhub_account` (provider 6.x): <https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_account>

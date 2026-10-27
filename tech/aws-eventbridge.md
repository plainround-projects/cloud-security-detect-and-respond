# Amazon EventBridge (rules, patterns, targets)

## What it is

EventBridge is the AWS service that routes **events**: small JSON messages saying that something happened. AWS services emit events automatically; the ones that matter here are "an API call was made", which come from the audit log ([aws-cloudtrail.md](aws-cloudtrail.md)). A **rule** watches the events of one Region. It has an **event pattern** (a JSON description of the events it wants) and one or more **targets** (what to do with a match, here: publish to a notification topic, [aws-sns.md](aws-sns.md)). In Terraform and the CLI, the rule is still called `aws_cloudwatch_event_rule`, a name from before EventBridge existed.

## Why this repository uses it

A detection is only useful if it reaches a person in minutes. EventBridge rules are the fast path: when an API call matching a pattern happens, the alert is sent within about a minute, without waiting for the audit log files to arrive in the archive. The detections are the rules. The slower, complete path is `detect-respond scan`, which runs the same patterns over the archive.

## Where it appears

| Path | What it does |
| --- | --- |
| `detections/*.json` | the patterns, one file per detection ([json.md](json.md)) |
| `infra/modules/alerting/main.tf` | one rule and one target per detection, a topic, a key |
| `infra/environments/workload/main.tf` | one `alerting` module per Region, and which detection runs where |
| `src/detect_respond/domain/pattern.py` | the pattern language in Python, for replay and tests |
| `src/detect_respond/domain/events.py` | `envelope()`: the event as EventBridge delivers it |
| `src/detect_respond/infrastructure/plan_audit.py` | checks that the rules in the plan are the detections in `detections/` |
| `policy/detection.rego` | rules: every rule has a target, D1 to D4 are deployed, D4 sees read-only calls |

## How it works underneath

EventBridge only sees the events of the Region where the rule lives. That is why this repository has three copies of the alerting module: one in `us-east-1`, where IAM events arrive (IAM is a global service whose events are delivered there), one in the home Region, and one in a Region the account never uses, to catch a call there. A rule matches an event when **every field of the pattern** is satisfied. Each pattern value is a list of alternatives, and the field matches when the event's value is one of them. Besides exact values, a pattern can use `prefix`, `suffix`, `anything-but` and `exists`. For each match, EventBridge can reshape the event with an **input transformer** before it reaches the target: it pulls named values out of the event by path and pastes them into a template.

By default a rule on API-call events sees *write* management events only (create, change, delete); the read-only calls (list, describe) are left out. A rule state of `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS` asks for the read-only ones too.

## Walkthrough of this repository's use

From `infra/modules/alerting/main.tf`:

```hcl
resource "aws_cloudwatch_event_rule" "detection" {
  for_each = var.detections

  name = "${var.name}-${lower(each.key)}"
  # The pattern is the detection file, unchanged, so what the tests replay is what runs.
  event_pattern = each.value.pattern_json
  description   = "${each.key}: ${each.value.title}"
  state         = each.value.state
}
```

`for_each` creates one rule per detection given to this Region. The name ends in the lower-case detection id (`detect-global-d1`), which the audit relies on. `event_pattern` is the detection's pattern as JSON text. `state` is `ENABLED` or, for a detection with `includeReadOnly`, the all-management-events state.

From `infra/environments/workload/main.tf`:

```hcl
        state        = try(d.includeReadOnly, false) ? "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS" : "ENABLED"
```

`try(x, default)` returns the default if `x` does not exist. So only D4, which needs read-only calls (an attacker "looking around" in a Region, see [json.md](json.md)), gets the wider state.

From `infra/modules/alerting/main.tf`:

```hcl
resource "aws_cloudwatch_event_target" "alert" {
  for_each = var.detections

  rule = aws_cloudwatch_event_rule.detection[each.key].name
  arn  = aws_sns_topic.alerts.arn
```

The target connects a rule to the topic. A rule with no target alerts nobody, and the OPA policy denies that.

From `infra/modules/alerting/main.tf`:

```hcl
    input_paths = local.alert_paths
```

The **input transformer** first extracts values by path. The map `alert_paths` has entries such as `who = "$.detail.userIdentity.arn"` and `name = "$.detail.eventName"`: `$` is the whole event, and `.detail` is the audit record inside it.

From `infra/modules/alerting/main.tf`:

```hcl
    input_template = format("\"%s\"", replace(
```

Then it pastes the values into a template: `<who>` in `alert-template.txt` becomes the extracted value. Terraform fills the other placeholders (`{id}`, `{severity}`) when it deploys. The template is wrapped in quotes with `format` and newlines become `\n`, because the template must itself be a JSON string. The Python side does the same fill-in in `render_alert`, so the alert text can be tested without a cloud.

From `src/detect_respond/domain/events.py`:

```python
            "detail-type": "AWS API Call via CloudTrail",
```

`envelope()` wraps an audit record the way EventBridge delivers it: the record becomes the `detail`, with `source` (`aws.iam`), `detail-type` and `region` around it. Detection patterns are written against that shape, and the matcher is run on it.

From `src/detect_respond/infrastructure/plan_audit.py`:

```python
                if rule.pattern != expected:
                    problems.append(f"{detection.detection_id} in {rule.module} differs from detections/")
```

`audit-rules` compares each deployed rule's pattern with the detection file, and checks that each detection is deployed where its `deployTo` says. That closes the gap between "tested" and "running".

## Try it yourself

```bash
.venv/bin/python -m detect_respond audit-rules --plan build/workload.json; echo "exit $?"
```

After `make plan`, expect `the plan deploys exactly the detections in detections/` and `exit 0`.

```bash
python3 -c "
import json
p = json.load(open('build/workload.json'))
r = [x for x in p['resource_changes'] if x['type'] == 'aws_cloudwatch_event_rule']
print(sorted((x['change']['after']['name'], x['change']['after']['state']) for x in r))"
```

Expect five rules: `detect-global-d1`, `detect-global-d3` and `detect-global-d5` (state `ENABLED`), `detect-home-d2` (`ENABLED`) and `detect-watch-d4` with `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS`.

```bash
.venv/bin/python -c "
from detect_respond.domain.events import AuditEvent
e = AuditEvent.from_record({'eventID': 'e1', 'eventTime': '2026-10-22T11:03:42Z', 'eventName': 'CreateAccessKey', 'eventSource': 'iam.amazonaws.com', 'awsRegion': 'us-east-1'})
env = e.envelope()
print(env['source'], env['detail-type'], env['region'])"
```

Expect `aws.iam AWS API Call via CloudTrail us-east-1`.

```bash
.venv/bin/python -m detect_respond scan --archive fixtures/drill | head -n 4
```

Expect the start of the first alert: `ALERT D1: new long-lived credential`, `severity: high`, a time and the caller. The alert is produced from the same pattern and template that the deployed rule uses.

## Mistakes people make

- Expecting one rule to cover every Region. A rule sees its own Region only; IAM events arrive in `us-east-1`.
- Forgetting that a default rule misses read-only calls. A detection about "looking around" must opt in.
- Writing a pattern value without a list around it. Every value is a list of alternatives.
- Deploying a rule with no target, or a target whose topic does not allow EventBridge to publish. The alert never arrives and nothing fails loudly.
- Testing the pattern in one language and deploying a hand-copied one in another. Here the file is shared, and `audit-rules` checks the copy.

## Check yourself

1. What does an EventBridge rule consist of? *An event pattern and one or more targets.*
2. Why are there three alerting modules? *A rule sees only its own Region: `us-east-1` for IAM events, the home Region, and an unused Region.*
3. What does `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS` add? *Read-only management events, which a default rule does not see.*
4. What does the input transformer do? *Extracts values from the event by path and pastes them into the alert template.*
5. What does `audit-rules` check? *That the deployed rule patterns equal the detection files and each is deployed where it should be.*

## Further reading

- EventBridge user guide: <https://docs.aws.amazon.com/eventbridge/latest/userguide/>
- Event patterns: <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html>
- Terraform `aws_cloudwatch_event_rule` (provider 6.x): <https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_rule>

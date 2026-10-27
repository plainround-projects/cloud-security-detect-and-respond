# Open Policy Agent and Rego

## What it is

**Open Policy Agent (OPA)** is a command-line tool (and server) that evaluates **policies** against data. **Rego** is the language the policies are written in. You give OPA a policy file and some input data (here, a JSON file), and it answers questions such as "which rules are broken?". This repository uses OPA **1.21.4**, where the modern Rego syntax (`if`, `contains`, `in`) is the default, and every Rego file says `import rego.v1`.

## Why this repository uses it

"Policy as code" is part of the lesson's method: rules about *shape* should be machine-checked, not remembered. The policy file `policy/detection.rego` says things like "the archive must be locked in compliance mode", "the trail must cover every Region", "a rule with no target alerts nobody" and "PowerUserAccess is allowed only on the drill role". It runs on the Terraform plan of **both** environments before anything is built. The Python code answers the other half (does the rule that is deployed equal the rule that was tested?); both read the same plan.

## Where it appears

| Path | What it does |
| --- | --- |
| `policy/detection.rego` | the rules; the set `deny` collects one message per violation |
| `policy/detection_test.rego` | 31 tests: an allow case for each environment and a deny case for each rule |
| `Makefile` | `opa test`, `opa eval`, `opa fmt`, `opa check` |

## How it works underneath

OPA loads the Rego files and the input JSON into memory. Rego is **declarative**: you do not write steps; you write conditions that must all be true for a rule to hold. A rule like `deny contains msg if { ... }` adds `msg` to the set `deny` for every way the body can be satisfied. Inside a body, each line is a condition (all must hold); `some x in list` tries each element. If no combination satisfies a body, the rule contributes nothing. OPA does not run side effects; it only computes values.

## Walkthrough of this repository's use

From `policy/detection.rego`:

```rego
package detection

import rego.v1
```

`package` names the policy (its results are at `data.detection`). `import rego.v1` turns on the current syntax rules.

From `policy/detection.rego`:

```rego
planned(type) := {rc | some rc in input.resource_changes; rc.type == type; rc.change.after != null}
```

A **function** that returns a **set comprehension**: the set of all resources `rc` in the plan (`input` is the plan JSON) whose type matches and which still exist after the change (`after != null`; a resource being deleted has `after` equal to null).

From `policy/detection.rego`:

```rego
archive_buckets := {rc.change.after.bucket | some rc in planned("aws_s3_bucket"); rc.change.after.object_lock_enabled == true}
```

Which buckets are archives? Those created with Object Lock. Every archive rule starts from this set, so the same rules apply to a second archive bucket without changes. The security plan has one; the workload plan has none, and the rules about archives simply have nothing to check there.

From `policy/detection.rego`:

```rego
locked_in_compliance_mode(name) if {
	some rc in planned("aws_s3_bucket_object_lock_configuration")
	rc.change.after.bucket == name
	some rule in rc.change.after.rule
	some retention in rule.default_retention
	retention.mode == "COMPLIANCE"
	retention.days >= 1
}
```

A boolean helper. Read from the top: some lock configuration exists for this bucket, it has a rule with a default retention, in `COMPLIANCE` mode, for at least one day. The nested objects are lists in the plan JSON (a Terraform block that can repeat), which is why `some ... in` is used at each level.

From `policy/detection.rego`:

```rego
deny contains msg if {
	some name in archive_buckets
	not locked_in_compliance_mode(name)
	msg := sprintf("bucket %s: Object Lock must be in compliance mode with a retention of at least one day", [name])
}
```

`not` is negation: the rule fires for an archive that does **not** satisfy the helper. `:=` assigns once and `sprintf` builds the text. A missing lock configuration also fires, because the helper cannot be satisfied without one; the test `test_an_archive_with_no_lock_configuration_is_denied` proves it.

From `policy/detection.rego`:

```rego
trail_only(statement) if {
	statement.Principal.Service == "cloudtrail.amazonaws.com"
	statement.Condition.StringEquals["aws:SourceArn"]
}
```

"Only the workload account's trail may write": every Allow on the archive must name the CloudTrail service and pin the trail by `aws:SourceArn`. A bare field such as `statement.Condition.StringEquals["aws:SourceArn"]` is a condition: it must exist.

From `policy/detection.rego`:

```rego
	local := {bucket.change.after.bucket | some bucket in planned("aws_s3_bucket")}
	rc.change.after.s3_bucket_name in local
```

A trail that delivers to a bucket created in the *same plan* is a trail that keeps its logs in its own environment. The rule denies it with `the logs must go to a bucket outside this account`. The workload environment passes because its log bucket is only a name given by variable.

From `policy/detection.rego`:

```rego
known_or_set(rc, attribute) if rc.change.after[attribute] != null

known_or_set(rc, attribute) if rc.change.after_unknown[attribute] == true
```

Two bodies, so either makes it true. A value that Terraform cannot know yet (a key id that does not exist until apply) is listed under `after_unknown`, so it does not look missing. The rules for the trail's key and the topic's key use it.

From `policy/detection.rego`:

```rego
in_drill(rc) if startswith(rc.address, "module.drill")
```

The drill's deliberate weakness is allowed only where the address starts with `module.drill`. Other rules say, for example, `not in_drill(rc)` before complaining about a switched-off Block Public Access, or about an IAM user. This is the fence around the weakness.

From `policy/detection.rego`:

```rego
	some type in {"aws_iam_role", "aws_iam_user"}
	some rc in planned(type)
	in_drill(rc)
	not rc.change.after.tags.purpose
```

A positive requirement inside the fence: drill identities must carry the `purpose` tag so the teardown can find them.

**Tests.** From `policy/detection_test.rego`:

```rego
test_the_archive_is_allowed if {
	count(detection.deny) == 0 with input as {"resource_changes": archive}
}
```

A rule whose name starts with `test_` is a test. `with input as X` replaces the input for that one evaluation: here, a small hand-written plan for the archive (`archive`, defined in the same file). A test passes when its body is true. The matching deny case is `test_an_archive_without_object_lock_in_compliance_mode_is_denied`, which swaps the lock for one in `GOVERNANCE` mode and asserts that a message mentioning "compliance mode" appears (with the helper `denied_with`).

**The Makefile.**

From `Makefile`:

```make
	  opa eval --fail-defined --format pretty -d policy -i $(BUILD)/$$env.json 'data.detection.deny[_]' || exit 1; \
```

`eval` evaluates a query. `-d policy` loads the folder; `-i FILE` gives the input. The query `data.detection.deny[_]` means "every message in the set". `--fail-defined` exits non-zero if the query returns anything, so any violation fails `make check`. It runs once for each environment ([make.md](make.md)).

From `Makefile`:

```make
	opa fmt --list --fail policy
	opa check --strict policy
```

`fmt --list --fail` names files that are not formatted and fails; `check --strict` parses everything and reports unused variables and similar mistakes.

## Try it yourself

```bash
opa version | sed -n 1p
```

Expect `Version: 1.21.4`.

```bash
opa test policy
```

Expect `PASS: 31/31`.

```bash
opa eval -d policy -i build/security.json 'data.detection.deny' --format pretty
opa eval -d policy -i build/workload.json 'data.detection.deny' --format pretty
```

After `make plan`, expect `[]` twice: both plans break no rule.

```bash
python3 - <<'E'
import json
p = json.load(open('build/workload.json'))
for r in p['resource_changes']:
    if r['type'] == 'aws_cloudtrail':
        r['change']['after']['is_multi_region_trail'] = False
json.dump(p, open('/tmp/weak-workload.json', 'w'))
E
opa eval -d policy -i /tmp/weak-workload.json 'data.detection.deny' --format pretty; rm /tmp/weak-workload.json
```

Expect one message: `module.central_trail.aws_cloudtrail.central: the trail must cover every Region`. You weakened a copy of the plan, and the policy named the resource and the rule.

## Mistakes people make

- Forgetting that all lines of a body must hold (they are an AND). To say OR, write two rules or two function bodies.
- A rule that can never fire because of a wrong field name, so everything "passes". The deny tests prove each rule can fire.
- Confusing `=` (unification) and `:=` (assign). Use `:=`.
- Treating a value that is "known after apply" as missing. Use `known_or_set`.
- Treating `null` as false. A bare condition such as `rc.change.after.field` succeeds when the value is `null`, because `null` is a defined value; only `false` and "undefined" fail it. This policy compares with `!= null` explicitly in `planned`.

## Check yourself

1. What is `deny` here? *A set of message strings; one per rule violation.*
2. What does `some rc in planned(...)` do? *Tries each resource in turn.*
3. What does `with input as X` do in a test? *Replaces the input for that evaluation.*
4. How does the policy keep the drill's weakness fenced in? *`in_drill(rc)` tests for the address prefix `module.drill`; the rules about public buckets, users and administrator rights make an exception only there.*
5. Why does `make check` use `--fail-defined`? *To exit non-zero as soon as any violation exists.*

## Further reading

- OPA documentation (1.21): <https://www.openpolicyagent.org/docs>
- Rego language reference: <https://www.openpolicyagent.org/docs/policy-language>
- Policy testing: <https://www.openpolicyagent.org/docs/policy-testing>

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

This note shows **every line** of the policy file and of its test file, in file order, and explains each rule. Read this section first; it explains the language the file is written in.

**What a policy is here.** A policy is a set of rules that look at a piece of data and say what is wrong with it. The data is the **plan**: the JSON file that `terraform show -json` writes, which lists every cloud resource Terraform *would* create ([terraform.md](terraform.md), [json.md](json.md)). OPA reads the policy and the plan, and answers questions about them. It never changes anything.

**Rego, the language.** Rego is *declarative*: a rule is a list of conditions, and the rule holds only if **all** the conditions on its lines are true, like a row of "and"s. There are no steps and no loops in the usual sense. The words you will meet:

- `package name` names a group of rules; the results are found at `data.name`. `import rego.v1` turns on the current version of the language.
- `input` is the data OPA was given (the plan).
- `x := value` gives a name to a value, once. `==` compares two values, and a bare expression such as `rc.change.after.enable_key_rotation` is a condition that holds when the value exists and is not `false`.
- `some rc in collection` means "try every item of the collection, one after another, as `rc`". The lines that follow are tested for each item; every item that satisfies all of them produces a result.
- A **set** is a collection without order or repeats, written `{a, b}`. A **set comprehension** `{x | some x in things; condition}` builds a set from the items that pass a condition.
- `deny contains msg if { ... }` is a **rule that adds to a set**. Every way of satisfying the body adds one message `msg` to the set called `deny`. After OPA runs, `deny` is the list of everything that is wrong. If it is empty, the plan passes.
- `not condition` holds when the condition does **not** hold.
- A **function** is written `name(arguments) := value if { ... }` or, for a yes/no answer, `name(arguments) if { ... }`. When the same function name appears twice, it is true if **either** definition is true: that is how "or" is written.
- `sprintf("%s: text", [value])` builds a string, `contains`, `startswith`, `endswith` and `regex.match` test strings, `json.unmarshal(text)` turns JSON text into data, and `object.get(object, key, default)` reads a key with a fallback.
- A line that starts with `#` is a comment.

**Tests.** A rule whose name starts with `test_` is a unit test, run by `opa test`. `with input as X` replaces the input for one check, so each test can describe its own small plan.

### `policy/detection.rego`: the rules

From `policy/detection.rego` (lines 1 to 3):

```rego
# Guardrails for the detection and response layer, evaluated on `terraform show -json` output of either environment.
# Every rule has a deny test and an allow test in detection_test.rego.
package detection
```

The comment above the definition says: "Guardrails for the detection and response layer, evaluated on `terraform show -json` output of either environment. Every rule has a deny test and an allow test in detection_test.rego.". Names the policy. Its rules and results live under `data.detection`, which is why the Makefile queries `data.detection.deny`.

From `policy/detection.rego` (line 5):

```rego
import rego.v1
```

Switches on the current Rego syntax (`if`, `contains`, `in`). Every Rego file in this repository starts with it.

From `policy/detection.rego` (line 7):

```rego
planned(type) := {rc | some rc in input.resource_changes; rc.type == type; rc.change.after != null}
```

A function that returns a **set comprehension**: the set of all resources `rc` in the plan (`input.resource_changes` is the plan's list of changes) whose `type` matches the argument and which still exist after the change. `rc.change.after != null` matters: for a resource that the plan would delete, `after` is `null`, and this removes it. Every rule below starts from `planned("some_type")`.

From `policy/detection.rego` (line 9):

```rego
as_list(value) := value if is_array(value)
```

Two definitions of one function begin here. This first one says: if the value is already an array (a list), the answer is the value itself.

From `policy/detection.rego` (line 11):

```rego
as_list(value) := [value] if not is_array(value)
```

The second definition: if the value is **not** an array, wrap it in a one-item list. Together they make "a policy statement may be one object or a list of them" always come out as a list.

From `policy/detection.rego` (line 13):

```rego
statements(document) := as_list(document.Statement)
```

Takes a parsed policy document and returns its `Statement` entry as a list (a policy lists its permissions under `Statement`; see [aws-iam.md](aws-iam.md)).

From `policy/detection.rego` (line 15):

```rego
in_drill(rc) if startswith(rc.address, "module.drill")
```

True when the resource's address starts with `module.drill`, that is, when it is part of the drill module. The deliberate, temporary weakness is allowed only there; other rules say `not in_drill(rc)` before they complain.

From `policy/detection.rego` (line 17):

```rego
known_or_set(rc, attribute) if rc.change.after[attribute] != null
```

Two definitions of `known_or_set`, which accepts an attribute that is set **or** not yet known. The first: the attribute has a value in the plan (`rc.change.after[attribute]` reads a field whose name is in the variable).

From `policy/detection.rego` (line 19):

```rego
known_or_set(rc, attribute) if rc.change.after_unknown[attribute] == true
```

The second definition: Terraform lists in `after_unknown` the values it cannot know until the resource exists (for example a key id). Such an attribute is "known after apply" and counts as set, so it does not look missing.

From `policy/detection.rego` (line 21):

```rego
public_principal(statement) if statement.Principal == "*"
```

Two definitions of `public_principal`. The first: the statement's `Principal` is the single value `"*"`, which means everyone.

From `policy/detection.rego` (line 23):

```rego
public_principal(statement) if "*" in as_list(statement.Principal.AWS)
```

The second: `Principal` is an object whose `AWS` entry (a value or a list, made a list by `as_list`) contains `"*"`, which also means everyone.

From `policy/detection.rego` (line 25):

```rego
# ---- The archive (security environment) -------------------------------------------------------------------------
```

A comment for the reader: ---- The archive (security environment) -------------------------------------------------------------------------

From `policy/detection.rego` (line 27):

```rego
archive_buckets := {rc.change.after.bucket | some rc in planned("aws_s3_bucket"); rc.change.after.object_lock_enabled == true}
```

The set of archive buckets: the names of the planned buckets that were created with Object Lock (`object_lock_enabled == true`). Every archive rule starts from this set. The security plan has one; the workload plan has none, and the archive rules then have nothing to check there.

From `policy/detection.rego` (lines 29 to 36):

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

True when the bucket `name` has a lock configuration with a default retention in `COMPLIANCE` mode of **at least one day** ([aws-s3.md](aws-s3.md)). Reading from the top: some planned lock configuration is for this bucket, it has a rule, the rule has a default retention (each level is a list in the plan, hence `some ... in`), the mode is `COMPLIANCE` and `days >= 1`.

From `policy/detection.rego` (lines 38 to 46):

```rego
has_deny_on_delete(name) if {
	some rc in planned("aws_s3_bucket_policy")
	rc.change.after.bucket == name
	some statement in statements(json.unmarshal(rc.change.after.policy))
	statement.Effect == "Deny"
	public_principal(statement)
	"s3:DeleteObject" in as_list(statement.Action)
	"s3:DeleteObjectVersion" in as_list(statement.Action)
}
```

True when the bucket's policy contains a statement that **denies deleting objects and versions to everyone**: the effect is `Deny`, the principal is public (`public_principal`, meaning everyone), and the action list includes both `s3:DeleteObject` and `s3:DeleteObjectVersion`.

From `policy/detection.rego` (lines 48 to 53):

```rego
versioned(name) if {
	some rc in planned("aws_s3_bucket_versioning")
	rc.change.after.bucket == name
	some configuration in rc.change.after.versioning_configuration
	configuration.status == "Enabled"
}
```

True when the bucket `name` has versioning enabled: some planned `aws_s3_bucket_versioning` resource is for this bucket, and one of the items in its `versioning_configuration` list has `status == "Enabled"`. (Terraform blocks that can repeat appear as lists in the plan, which is why `some configuration in ...` is used.)

From `policy/detection.rego` (lines 55 to 62):

```rego
protected(name) if {
	some rc in planned("aws_s3_bucket_public_access_block")
	rc.change.after.bucket == name
	rc.change.after.block_public_acls
	rc.change.after.ignore_public_acls
	rc.change.after.block_public_policy
	rc.change.after.restrict_public_buckets
}
```

True when the bucket called `name` has all four Block Public Access switches on ([aws-s3.md](aws-s3.md)). It looks through the planned `aws_s3_bucket_public_access_block` resources for one whose `bucket` equals `name`, and then requires each of the four settings to be true (each line is a condition that must hold).

From `policy/detection.rego` (lines 64 to 70):

```rego
encrypted_with_kms(name) if {
	some rc in planned("aws_s3_bucket_server_side_encryption_configuration")
	rc.change.after.bucket == name
	some rule in rc.change.after.rule
	some encryption in rule.apply_server_side_encryption_by_default
	encryption.sse_algorithm == "aws:kms"
}
```

True when the bucket `name` has a server-side encryption configuration whose default rule uses the algorithm `aws:kms`, that is, a key from the key service and not the plain default. The nested `some` lines step through the lists inside the plan.

From `policy/detection.rego` (lines 72 to 76):

```rego
deny contains msg if {
	some name in archive_buckets
	not locked_in_compliance_mode(name)
	msg := sprintf("bucket %s: Object Lock must be in compliance mode with a retention of at least one day", [name])
}
```

For every archive bucket: if it is not locked in compliance mode, add a message. A missing lock configuration also fires, because the helper cannot be satisfied without one.

From `policy/detection.rego` (lines 78 to 82):

```rego
deny contains msg if {
	some name in archive_buckets
	not has_deny_on_delete(name)
	msg := sprintf("bucket %s: the policy must deny deleting objects and versions to every principal", [name])
}
```

For every archive bucket: if its policy has no deny on delete, add a message.

From `policy/detection.rego` (lines 84 to 88):

```rego
deny contains msg if {
	some name in archive_buckets
	not versioned(name)
	msg := sprintf("bucket %s: versioning must be enabled (Object Lock needs it)", [name])
}
```

For every archive bucket: if it is not versioned, add a message. Object Lock works on versions.

From `policy/detection.rego` (lines 90 to 94):

```rego
deny contains msg if {
	some name in archive_buckets
	not protected(name)
	msg := sprintf("bucket %s: Block Public Access must be fully on", [name])
}
```

For every archive bucket: if it is not fully protected, add a message.

From `policy/detection.rego` (lines 96 to 100):

```rego
deny contains msg if {
	some name in archive_buckets
	not encrypted_with_kms(name)
	msg := sprintf("bucket %s: the archive must be encrypted with a customer-managed key", [name])
}
```

For every archive bucket: if it is not encrypted with a key from the key service, add a message ([aws-kms.md](aws-kms.md)).

From `policy/detection.rego` (lines 102 to 110):

```rego
# Only the workload account's trail may write: every Allow on the archive names the CloudTrail service and pins the trail.
deny contains msg if {
	some rc in planned("aws_s3_bucket_policy")
	rc.change.after.bucket in archive_buckets
	some statement in statements(json.unmarshal(rc.change.after.policy))
	statement.Effect == "Allow"
	not trail_only(statement)
	msg := sprintf("%s: statement %s allows something other than the one trail, pinned by aws:SourceArn", [rc.address, object.get(statement, "Sid", "(no Sid)")])
}
```

The comment above the definition says: "Only the workload account's trail may write: every Allow on the archive names the CloudTrail service and pins the trail.". The comment above says: only the workload account's trail may write. For every statement of an archive bucket's policy that **allows** something, if it is not a trail-only statement (`not trail_only(statement)`), add a message.

From `policy/detection.rego` (lines 112 to 115):

```rego
trail_only(statement) if {
	statement.Principal.Service == "cloudtrail.amazonaws.com"
	statement.Condition.StringEquals["aws:SourceArn"]
}
```

True when the statement's principal is the CloudTrail service **and** the statement has a condition on `aws:SourceArn`, that is, it is pinned to one trail. A bare field such as `statement.Condition.StringEquals["aws:SourceArn"]` is a condition: it must exist.

From `policy/detection.rego` (lines 117 to 121):

```rego
deny contains msg if {
	some rc in planned("aws_kms_key")
	not rc.change.after.enable_key_rotation
	msg := sprintf("%s: key rotation must be on", [rc.address])
}
```

For every planned key: if rotation is not enabled, add a message. `not` holds when the value is missing or false ([aws-kms.md](aws-kms.md)).

From `policy/detection.rego` (line 123):

```rego
# ---- The trail and the detections (workload environment) --------------------------------------------------------
```

A comment for the reader: ---- The trail and the detections (workload environment) --------------------------------------------------------

From `policy/detection.rego` (lines 125 to 129):

```rego
deny contains msg if {
	some rc in planned("aws_cloudtrail")
	not rc.change.after.is_multi_region_trail
	msg := sprintf("%s: the trail must cover every Region", [rc.address])
}
```

The section comment above says the next rules are about the trail and the detections in the workload environment. For every planned trail: if it is not multi-region, add a message ([aws-cloudtrail.md](aws-cloudtrail.md)).

From `policy/detection.rego` (lines 131 to 135):

```rego
deny contains msg if {
	some rc in planned("aws_cloudtrail")
	not rc.change.after.enable_log_file_validation
	msg := sprintf("%s: log file validation must be on", [rc.address])
}
```

For every planned trail: if log file validation is off, add a message.

From `policy/detection.rego` (lines 137 to 142):

```rego
deny contains msg if {
	some rc in planned("aws_cloudtrail")
	local := {bucket.change.after.bucket | some bucket in planned("aws_s3_bucket")}
	rc.change.after.s3_bucket_name in local
	msg := sprintf("%s: the logs must go to a bucket outside this account, not to %s", [rc.address, rc.change.after.s3_bucket_name])
}
```

`local := {...}` builds the set of bucket names that this plan creates (a set comprehension over the planned buckets). If the trail's `s3_bucket_name` is **in** that set, the logs stay inside this environment, and a message is added. A trail whose bucket is only a name given by a variable passes, because the bucket belongs to the other account.

From `policy/detection.rego` (lines 144 to 148):

```rego
deny contains msg if {
	some rc in planned("aws_cloudtrail")
	not rc.change.after.s3_bucket_name
	msg := sprintf("%s: the trail needs a log bucket", [rc.address])
}
```

For every planned trail: if it names no bucket (`not rc.change.after.s3_bucket_name`), add a message.

From `policy/detection.rego` (lines 150 to 154):

```rego
deny contains msg if {
	some rc in planned("aws_cloudtrail")
	not known_or_set(rc, "kms_key_id")
	msg := sprintf("%s: the logs must be encrypted with a key held by the security account", [rc.address])
}
```

For every planned trail: if the key is neither set nor "known after apply" (`not known_or_set(rc, "kms_key_id")`), add a message.

From `policy/detection.rego` (lines 156 to 159):

```rego
rule_has_target(rc) if {
	some target in planned("aws_cloudwatch_event_target")
	target.change.after.rule == rc.change.after.name
}
```

True when some planned rule target points at this rule: the target's `rule` equals the rule's `name`.

From `policy/detection.rego` (lines 161 to 165):

```rego
deny contains msg if {
	some rc in planned("aws_cloudwatch_event_rule")
	not rule_has_target(rc)
	msg := sprintf("%s: a rule with no target alerts nobody", [rc.address])
}
```

For every planned event rule: if `not rule_has_target(rc)`, add a message ([aws-eventbridge.md](aws-eventbridge.md)).

From `policy/detection.rego` (lines 167 to 171):

```rego
deny contains msg if {
	some rc in planned("aws_sns_topic")
	not known_or_set(rc, "kms_master_key_id")
	msg := sprintf("%s: the alert topic must be encrypted", [rc.address])
}
```

For every planned alert topic: if its key is neither set nor "known after apply", add a message ([aws-sns.md](aws-sns.md)).

From `policy/detection.rego` (line 173):

```rego
required_detections := {"d1", "d2", "d3", "d4"}
```

The set of the four detection ids that every environment with rules must deploy (D5 is optional: it needs the honeytoken).

From `policy/detection.rego` (lines 175 to 180):

```rego
deny contains msg if {
	count(planned("aws_cloudwatch_event_rule")) > 0
	some id in required_detections
	not detection_deployed(id)
	msg := sprintf("detection %s is not deployed by any rule", [upper(id)])
}
```

If the plan has at least one event rule (`count(...) > 0`), then for every required detection id that is not deployed (`not detection_deployed(id)`), add a message. `upper(id)` writes the id in capitals for the message.

From `policy/detection.rego` (lines 182 to 185):

```rego
detection_deployed(id) if {
	some rc in planned("aws_cloudwatch_event_rule")
	endswith(rc.change.after.name, sprintf("-%s", [id]))
}
```

True when some planned event rule's name ends with `-<id>` (for example `-d1`). The rule names are built that way by the alerting module.

From `policy/detection.rego` (lines 187 to 192):

```rego
deny contains msg if {
	some rc in planned("aws_cloudwatch_event_rule")
	endswith(rc.change.after.name, "-d4")
	rc.change.after.state != "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"
	msg := sprintf("%s: D4 must also see read-only management events", [rc.address])
}
```

For every rule whose name ends in `-d4`: if its state is not `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS`, add a message. D4 (a call in an unused Region) is often made of read-only calls, which a default rule does not see.

From `policy/detection.rego` (line 194):

```rego
# ---- Credentials and the fenced-in weakness --------------------------------------------------------------------
```

A comment for the reader: ---- Credentials and the fenced-in weakness --------------------------------------------------------------------

From `policy/detection.rego` (lines 196 to 199):

```rego
deny contains msg if {
	some rc in planned("aws_iam_access_key")
	msg := sprintf("%s: an access key would sit in the state; scripts create the drill and honeytoken keys", [rc.address])
}
```

Any planned `aws_iam_access_key` adds a message: its secret would be stored in the Terraform state. The drill and honeytoken keys are created by scripts instead.

From `policy/detection.rego` (lines 201 to 205):

```rego
deny contains msg if {
	some rc in planned("aws_iam_role_policy_attachment")
	rc.change.after.policy_arn == "arn:aws:iam::aws:policy/AdministratorAccess"
	msg := sprintf("%s: AdministratorAccess is never attached by code", [rc.address])
}
```

For every planned policy attachment whose policy is `AdministratorAccess`, add a message.

From `policy/detection.rego` (lines 207 to 212):

```rego
deny contains msg if {
	some rc in planned("aws_iam_role_policy_attachment")
	rc.change.after.policy_arn == "arn:aws:iam::aws:policy/PowerUserAccess"
	not in_drill(rc)
	msg := sprintf("%s: PowerUserAccess is allowed only on the drill role", [rc.address])
}
```

For every planned policy attachment of `PowerUserAccess`: if it is not inside the drill module (`not in_drill(rc)`), add a message.

From `policy/detection.rego` (lines 214 to 220):

```rego
deny contains msg if {
	some rc in planned("aws_s3_bucket_public_access_block")
	not in_drill(rc)
	some flag in ["block_public_acls", "ignore_public_acls", "block_public_policy", "restrict_public_buckets"]
	not rc.change.after[flag]
	msg := sprintf("%s: %s is off outside the drill module", [rc.address, flag])
}
```

For every planned Block Public Access resource outside the drill: `some flag in [...]` tries each of the four setting names, and if a setting is off (`not rc.change.after[flag]`), add a message that names it.

From `policy/detection.rego` (lines 222 to 226):

```rego
deny contains msg if {
	some rc in planned("aws_iam_user")
	not in_drill(rc)
	msg := sprintf("%s: IAM users exist only inside the drill module", [rc.address])
}
```

For every planned IAM user outside the drill, add a message.

From `policy/detection.rego` (lines 228 to 234):

```rego
deny contains msg if {
	some type in {"aws_iam_role", "aws_iam_user"}
	some rc in planned(type)
	in_drill(rc)
	not rc.change.after.tags.purpose
	msg := sprintf("%s: drill identities must carry the tag purpose so the teardown can find them", [rc.address])
}
```

For every planned role or user **inside** the drill: if it has no `purpose` tag, add a message, so the teardown can find it.

From `policy/detection.rego` (lines 236 to 243):

```rego
deny contains msg if {
	some type, attribute in {"aws_s3_bucket_policy": "policy", "aws_iam_role": "assume_role_policy", "aws_sns_topic_policy": "policy"}
	some rc in planned(type)
	some statement in statements(json.unmarshal(rc.change.after[attribute]))
	statement.Effect == "Allow"
	public_principal(statement)
	msg := sprintf("%s: statement %s grants access to every principal", [rc.address, object.get(statement, "Sid", "(no Sid)")])
}
```

The pair syntax `some type, attribute in {...}` walks a small table: for each (resource type, field that holds a policy) pair, it looks at every planned resource of that type, parses the policy text in that field, and for every Allow statement checks `public_principal`. So the listed kinds of policy are all covered by one rule, and a statement that grants access to everyone adds a message that names the resource and the statement.

From `policy/detection.rego` (line 245):

```rego
# ---- Posture ---------------------------------------------------------------------------------------------------
```

A comment for the reader: ---- Posture ---------------------------------------------------------------------------------------------------

From `policy/detection.rego` (lines 247 to 251):

```rego
deny contains msg if {
	count(planned("aws_securityhub_standards_subscription")) > 0
	count(planned("aws_config_configuration_recorder_status")) == 0
	msg := "Security Hub controls need AWS Config recording; enable the recorder"
}
```

The section comment above says the next rule is about posture. If at least one Security Hub standards subscription is planned and **no** recorder-status resource is, add a message. The message is a plain string (no `sprintf`) because it names no resource ([aws-config.md](aws-config.md), [aws-security-hub.md](aws-security-hub.md)).

### `policy/detection_test.rego`: the tests

Every test follows one pattern: take a good plan (`archive` or `workload`), break exactly one thing, and assert that the matching rule fires (a "deny" test), or assert that nothing fires (an "allow" test). The helper definitions come first, then the tests in file order.

From `policy/detection_test.rego` (line 1):

```rego
package detection_test
```

Names the **test** policy. It is a separate package from the policy it tests, and it imports that policy with the next line.

From `policy/detection_test.rego` (lines 3 to 4):

```rego
import data.detection
import rego.v1
```

Makes the policy under test available by name, so the tests can read its `deny` set.

From `policy/detection_test.rego` (line 6):

```rego
change(address, type, after) := {"address": address, "type": type, "change": {"actions": ["create"], "after": after, "after_unknown": {}}}
```

Builds one entry of the plan's `resource_changes` list: the `address`, the `type`, and a `change` that says the action is `create` and what the resource looks like `after` it. `after_unknown` is empty. The tests use it so they do not need a real plan file.

From `policy/detection_test.rego` (line 8):

```rego
document(statements) := json.marshal({"Version": "2012-10-17", "Statement": statements})
```

Builds a policy document as **JSON text**: `json.marshal` turns data into text, and the document has the fixed `Version` (the policy language version) and the list of `Statement`s given. The plan stores policies as text, so the tests must too.

From `policy/detection_test.rego` (line 10):

```rego
bucket := "detect-archive-000000000001"
```

A constant: the archive bucket's name in the test data.

From `policy/detection_test.rego` (line 12):

```rego
trail_arn := "arn:aws:cloudtrail:eu-west-1:000000000000:trail/central-trail"
```

A constant: the full name (ARN) of the trail in the test data.

From `policy/detection_test.rego` (lines 14 to 17):

```rego
archive_policy := document([
	{"Sid": "TrailWrites", "Effect": "Allow", "Principal": {"Service": "cloudtrail.amazonaws.com"}, "Action": "s3:PutObject", "Resource": "*", "Condition": {"StringEquals": {"aws:SourceArn": trail_arn}}},
	{"Sid": "NobodyDeletes", "Effect": "Deny", "Principal": {"AWS": "*"}, "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"], "Resource": "*"},
])
```

The good archive bucket policy, as JSON text: one statement that lets the trail write, pinned to the trail by `aws:SourceArn`, and one that denies deleting objects and versions to everyone.

From `policy/detection_test.rego` (lines 19 to 27):

```rego
archive := [
	change("module.log_archive.aws_s3_bucket.archive", "aws_s3_bucket", {"bucket": bucket, "object_lock_enabled": true}),
	change("module.log_archive.aws_s3_bucket_object_lock_configuration.archive", "aws_s3_bucket_object_lock_configuration", {"bucket": bucket, "rule": [{"default_retention": [{"mode": "COMPLIANCE", "days": 1}]}]}),
	change("module.log_archive.aws_s3_bucket_versioning.archive", "aws_s3_bucket_versioning", {"bucket": bucket, "versioning_configuration": [{"status": "Enabled"}]}),
	change("module.log_archive.aws_s3_bucket_public_access_block.archive", "aws_s3_bucket_public_access_block", {"bucket": bucket, "block_public_acls": true, "ignore_public_acls": true, "block_public_policy": true, "restrict_public_buckets": true}),
	change("module.log_archive.aws_s3_bucket_server_side_encryption_configuration.archive", "aws_s3_bucket_server_side_encryption_configuration", {"bucket": bucket, "rule": [{"apply_server_side_encryption_by_default": [{"sse_algorithm": "aws:kms"}]}]}),
	change("module.log_archive.aws_s3_bucket_policy.archive", "aws_s3_bucket_policy", {"bucket": bucket, "policy": archive_policy}),
	change("module.archive_key.aws_kms_key.this", "aws_kms_key", {"enable_key_rotation": true}),
]
```

The **good archive plan**: the bucket with Object Lock, the lock configuration in compliance mode, versioning, Block Public Access, KMS encryption, the policy above and a key with rotation. Every archive deny test starts from this list and breaks one thing.

From `policy/detection_test.rego` (line 29):

```rego
detection_rule(id, state) := change(sprintf("module.alerting_global.aws_cloudwatch_event_rule.detection[\"%s\"]", [upper(id)]), "aws_cloudwatch_event_rule", {"name": sprintf("detect-global-%s", [id]), "state": state})
```

Builds a planned event rule for a detection id and a state.

From `policy/detection_test.rego` (line 31):

```rego
detection_target(id) := change(sprintf("module.alerting_global.aws_cloudwatch_event_target.alert[\"%s\"]", [upper(id)]), "aws_cloudwatch_event_target", {"rule": sprintf("detect-global-%s", [id])})
```

Builds the planned target that connects such a rule to the alert topic.

From `policy/detection_test.rego` (lines 33 to 53):

```rego
workload := array.concat(
	[
		change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": true, "enable_log_file_validation": true, "s3_bucket_name": bucket, "kms_key_id": "arn:aws:kms:eu-west-1:000000000001:key/x"}),
		change("module.alerting_global.aws_sns_topic.alerts", "aws_sns_topic", {"kms_master_key_id": "alias/x"}),
		detection_rule("d1", "ENABLED"),
		detection_rule("d2", "ENABLED"),
		detection_rule("d3", "ENABLED"),
		detection_rule("d4", "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"),
		detection_target("d1"),
		detection_target("d2"),
		detection_target("d3"),
		detection_target("d4"),
		change("module.posture[0].aws_securityhub_standards_subscription.foundational", "aws_securityhub_standards_subscription", {"standards_arn": "x"}),
		change("module.posture[0].aws_config_configuration_recorder_status.this", "aws_config_configuration_recorder_status", {"is_enabled": true}),
		change("module.drill[0].aws_iam_user.drill", "aws_iam_user", {"name": "drill-user", "tags": {"purpose": "incident-drill"}}),
		change("module.drill[0].aws_iam_role.broad", "aws_iam_role", {"name": "drill-broad-role", "tags": {"purpose": "incident-drill"}, "assume_role_policy": document([{"Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::000000000000:user/drill-user"}, "Action": "sts:AssumeRole"}])}),
		change("module.drill[0].aws_iam_role_policy_attachment.power_user", "aws_iam_role_policy_attachment", {"policy_arn": "arn:aws:iam::aws:policy/PowerUserAccess"}),
		change("module.drill[0].aws_s3_bucket_public_access_block.data", "aws_s3_bucket_public_access_block", {"block_public_acls": false, "ignore_public_acls": false, "block_public_policy": false, "restrict_public_buckets": false}),
	],
	[],
)
```

The **good workload plan**: the trail, an encrypted alert topic, rules and targets for D1 to D4, the posture subscription with its recorder, and the drill's identities, tagged and fenced. `array.concat(a, b)` joins two lists (the second is empty here).

From `policy/detection_test.rego` (line 55):

```rego
without(resources, type) := {"resource_changes": [rc | some rc in resources; rc.type != type]}
```

Returns a plan made of the given resources with every resource of one type removed.

From `policy/detection_test.rego` (line 57):

```rego
replace_type(resources, type, extra) := {"resource_changes": array.concat([rc | some rc in resources; rc.type != type], extra)}
```

Returns a plan made of the given resources with the resources of one type replaced by the extra ones.

From `policy/detection_test.rego` (line 59):

```rego
plus(resources, extra) := {"resource_changes": array.concat(resources, extra)}
```

Returns a plan made of the given resources plus extra ones.

From `policy/detection_test.rego` (lines 61 to 64):

```rego
denied_with(messages, fragment) if {
	some message in messages
	contains(message, fragment)
}
```

A helper used by almost every test. It is true when **some message** in the given set contains the given text: `some message in messages` tries each message, and `contains(message, fragment)` tests whether the text occurs in it. The tests use it to say "this rule fired" without depending on the whole sentence.

From `policy/detection_test.rego` (lines 66 to 68):

```rego
test_the_archive_is_allowed if {
	count(detection.deny) == 0 with input as {"resource_changes": archive}
}
```

A test: **the archive is allowed**. It asserts that `deny` is **empty**: this configuration breaks no rule (an "allow" case). For this test the input is a plan written out in full inside the test.

From `policy/detection_test.rego` (lines 70 to 72):

```rego
test_the_workload_is_allowed if {
	count(detection.deny) == 0 with input as {"resource_changes": workload}
}
```

A test: **the workload is allowed**. It asserts that `deny` is **empty**: this configuration breaks no rule (an "allow" case). For this test the input is a plan written out in full inside the test.

From `policy/detection_test.rego` (lines 74 to 77):

```rego
test_an_archive_without_object_lock_in_compliance_mode_is_denied if {
	governance := change("x", "aws_s3_bucket_object_lock_configuration", {"bucket": bucket, "rule": [{"default_retention": [{"mode": "GOVERNANCE", "days": 1}]}]})
	denied_with(detection.deny, "compliance mode") with input as replace_type(archive, "aws_s3_bucket_object_lock_configuration", [governance])
}
```

A test: **an archive without object lock in compliance mode is denied**. It asserts that some message of `deny` contains "compliance mode" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `governance`.

From `policy/detection_test.rego` (lines 79 to 81):

```rego
test_an_archive_with_no_lock_configuration_is_denied if {
	denied_with(detection.deny, "compliance mode") with input as without(archive, "aws_s3_bucket_object_lock_configuration")
}
```

A test: **an archive with no lock configuration is denied**. It asserts that some message of `deny` contains "compliance mode" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with every resource of one type **removed** (`without(...)`).

From `policy/detection_test.rego` (lines 83 to 86):

```rego
test_an_archive_whose_policy_lets_deletes_through_is_denied if {
	soft := document([{"Sid": "TrailWrites", "Effect": "Allow", "Principal": {"Service": "cloudtrail.amazonaws.com"}, "Action": "s3:PutObject", "Resource": "*", "Condition": {"StringEquals": {"aws:SourceArn": trail_arn}}}])
	denied_with(detection.deny, "deny deleting objects") with input as replace_type(archive, "aws_s3_bucket_policy", [change("x", "aws_s3_bucket_policy", {"bucket": bucket, "policy": soft})])
}
```

A test: **an archive whose policy lets deletes through is denied**. It asserts that some message of `deny` contains "deny deleting objects" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `soft`.

From `policy/detection_test.rego` (lines 88 to 91):

```rego
test_a_delete_deny_that_names_one_principal_only_is_denied if {
	narrow := document([{"Sid": "NobodyDeletes", "Effect": "Deny", "Principal": {"AWS": "arn:aws:iam::000000000001:root"}, "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"], "Resource": "*"}])
	denied_with(detection.deny, "deny deleting objects") with input as replace_type(archive, "aws_s3_bucket_policy", [change("x", "aws_s3_bucket_policy", {"bucket": bucket, "policy": narrow})])
}
```

A test: **a delete deny that names one principal only is denied**. It asserts that some message of `deny` contains "deny deleting objects" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `narrow`.

From `policy/detection_test.rego` (lines 93 to 95):

```rego
test_an_archive_without_versioning_is_denied if {
	denied_with(detection.deny, "versioning") with input as without(archive, "aws_s3_bucket_versioning")
}
```

A test: **an archive without versioning is denied**. It asserts that some message of `deny` contains "versioning" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with every resource of one type **removed** (`without(...)`).

From `policy/detection_test.rego` (lines 97 to 99):

```rego
test_an_archive_without_block_public_access_is_denied if {
	denied_with(detection.deny, "Block Public Access") with input as without(archive, "aws_s3_bucket_public_access_block")
}
```

A test: **an archive without block public access is denied**. It asserts that some message of `deny` contains "Block Public Access" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with every resource of one type **removed** (`without(...)`).

From `policy/detection_test.rego` (lines 101 to 104):

```rego
test_an_archive_with_default_encryption_is_denied if {
	aes := change("x", "aws_s3_bucket_server_side_encryption_configuration", {"bucket": bucket, "rule": [{"apply_server_side_encryption_by_default": [{"sse_algorithm": "AES256"}]}]})
	denied_with(detection.deny, "customer-managed key") with input as replace_type(archive, "aws_s3_bucket_server_side_encryption_configuration", [aes])
}
```

A test: **an archive with default encryption is denied**. It asserts that some message of `deny` contains "customer-managed key" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `aes`.

From `policy/detection_test.rego` (lines 106 to 112):

```rego
test_an_archive_policy_that_lets_the_account_root_write_is_denied if {
	loose := document([
		{"Sid": "Anyone", "Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::000000000001:root"}, "Action": "s3:PutObject", "Resource": "*"},
		{"Sid": "NobodyDeletes", "Effect": "Deny", "Principal": {"AWS": "*"}, "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"], "Resource": "*"},
	])
	denied_with(detection.deny, "one trail, pinned") with input as replace_type(archive, "aws_s3_bucket_policy", [change("x", "aws_s3_bucket_policy", {"bucket": bucket, "policy": loose})])
}
```

A test: **an archive policy that lets the account root write is denied**. It asserts that some message of `deny` contains "one trail, pinned" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `loose`.

From `policy/detection_test.rego` (lines 114 to 120):

```rego
test_a_trail_service_grant_without_the_source_arn_pin_is_denied if {
	unpinned := document([
		{"Sid": "TrailWrites", "Effect": "Allow", "Principal": {"Service": "cloudtrail.amazonaws.com"}, "Action": "s3:PutObject", "Resource": "*"},
		{"Sid": "NobodyDeletes", "Effect": "Deny", "Principal": {"AWS": "*"}, "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"], "Resource": "*"},
	])
	denied_with(detection.deny, "one trail, pinned") with input as replace_type(archive, "aws_s3_bucket_policy", [change("x", "aws_s3_bucket_policy", {"bucket": bucket, "policy": unpinned})])
}
```

A test: **a trail service grant without the source arn pin is denied**. It asserts that some message of `deny` contains "one trail, pinned" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `unpinned`.

From `policy/detection_test.rego` (lines 122 to 124):

```rego
test_a_key_without_rotation_is_denied if {
	denied_with(detection.deny, "rotation") with input as replace_type(archive, "aws_kms_key", [change("module.archive_key.aws_kms_key.this", "aws_kms_key", {"enable_key_rotation": false})])
}
```

A test: **a key without rotation is denied**. It asserts that some message of `deny` contains "rotation" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`).

From `policy/detection_test.rego` (lines 126 to 129):

```rego
test_a_trail_for_one_region_is_denied if {
	one := change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": false, "enable_log_file_validation": true, "s3_bucket_name": bucket, "kms_key_id": "k"})
	denied_with(detection.deny, "every Region") with input as replace_type(workload, "aws_cloudtrail", [one])
}
```

A test: **a trail for one region is denied**. It asserts that some message of `deny` contains "every Region" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `one`.

From `policy/detection_test.rego` (lines 131 to 134):

```rego
test_a_trail_without_log_file_validation_is_denied if {
	unvalidated := change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": true, "enable_log_file_validation": false, "s3_bucket_name": bucket, "kms_key_id": "k"})
	denied_with(detection.deny, "log file validation") with input as replace_type(workload, "aws_cloudtrail", [unvalidated])
}
```

A test: **a trail without log file validation is denied**. It asserts that some message of `deny` contains "log file validation" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `unvalidated`.

From `policy/detection_test.rego` (lines 136 to 140):

```rego
test_a_trail_that_logs_into_a_bucket_of_the_same_account_is_denied if {
	local := change("module.logs.aws_s3_bucket.local", "aws_s3_bucket", {"bucket": "local-logs"})
	trail := change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": true, "enable_log_file_validation": true, "s3_bucket_name": "local-logs", "kms_key_id": "k"})
	denied_with(detection.deny, "outside this account") with input as replace_type(workload, "aws_cloudtrail", [trail]).resource_changes + [local]
}
```

A test: **a trail that logs into a bucket of the same account is denied**. It asserts that some message of `deny` contains "outside this account" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `local`, `trail`.

From `policy/detection_test.rego` (lines 142 to 145):

```rego
test_a_trail_with_no_log_bucket_is_denied if {
	none := change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": true, "enable_log_file_validation": true, "kms_key_id": "k"})
	denied_with(detection.deny, "needs a log bucket") with input as replace_type(workload, "aws_cloudtrail", [none])
}
```

A test: **a trail with no log bucket is denied**. It asserts that some message of `deny` contains "needs a log bucket" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `none`.

From `policy/detection_test.rego` (lines 147 to 150):

```rego
test_a_trail_without_a_key_is_denied if {
	unkeyed := change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": true, "enable_log_file_validation": true, "s3_bucket_name": bucket})
	denied_with(detection.deny, "held by the security account") with input as replace_type(workload, "aws_cloudtrail", [unkeyed])
}
```

A test: **a trail without a key is denied**. It asserts that some message of `deny` contains "held by the security account" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `unkeyed`.

From `policy/detection_test.rego` (lines 152 to 154):

```rego
test_a_rule_with_no_target_is_denied if {
	denied_with(detection.deny, "alerts nobody") with input as workload + [detection_rule("d5", "ENABLED")]
}
```

A test: **a rule with no target is denied**. It asserts that some message of `deny` contains "alerts nobody" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is built by a helper from the good plan, with the change this test needs.

From `policy/detection_test.rego` (lines 156 to 158):

```rego
test_an_unencrypted_alert_topic_is_denied if {
	denied_with(detection.deny, "must be encrypted") with input as replace_type(workload, "aws_sns_topic", [change("module.alerting_global.aws_sns_topic.alerts", "aws_sns_topic", {"name": "t"})])
}
```

A test: **an unencrypted alert topic is denied**. It asserts that some message of `deny` contains "must be encrypted" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`).

From `policy/detection_test.rego` (lines 160 to 163):

```rego
test_an_alert_topic_whose_key_is_known_after_apply_is_allowed if {
	unknown := {"address": "module.alerting_global.aws_sns_topic.alerts", "type": "aws_sns_topic", "change": {"actions": ["create"], "after": {"name": "t"}, "after_unknown": {"kms_master_key_id": true}}}
	count(detection.deny) == 0 with input as replace_type(workload, "aws_sns_topic", [unknown])
}
```

A test: **an alert topic whose key is known after apply is allowed**. It asserts that `deny` is **empty**: this configuration breaks no rule (an "allow" case). For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `unknown`.

From `policy/detection_test.rego` (lines 165 to 168):

```rego
test_a_missing_detection_is_denied if {
	no_d3 := {"resource_changes": [rc | some rc in workload; not endswith(object.get(rc.change.after, "name", ""), "-d3"); not endswith(object.get(rc.change.after, "rule", ""), "-d3")]}
	denied_with(detection.deny, "detection D3 is not deployed") with input as no_d3
}
```

A test: **a missing detection is denied**. It asserts that some message of `deny` contains "detection D3 is not deployed" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is built by a helper from the good plan, with the change this test needs. Local values built first: `no_d3`.

From `policy/detection_test.rego` (lines 170 to 173):

```rego
test_d4_without_the_read_only_rule_state_is_denied if {
	plain := {"resource_changes": [rc | some rc in workload; rc.change.after.name != "detect-global-d4"]}
	denied_with(detection.deny, "read-only") with input as plain.resource_changes + [detection_rule("d4", "ENABLED")]
}
```

A test: **d4 without the read only rule state is denied**. It asserts that some message of `deny` contains "read-only" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is built by a helper from the good plan, with the change this test needs. Local values built first: `plain`.

From `policy/detection_test.rego` (lines 175 to 177):

```rego
test_an_access_key_in_the_state_is_denied if {
	denied_with(detection.deny, "state") with input as workload + [change("module.drill[0].aws_iam_access_key.k", "aws_iam_access_key", {"user": "drill-user"})]
}
```

A test: **an access key in the state is denied**. It asserts that some message of `deny` contains "state" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is built by a helper from the good plan, with the change this test needs.

From `policy/detection_test.rego` (lines 179 to 182):

```rego
test_administrator_access_attached_by_code_is_denied if {
	admin := change("module.drill[0].aws_iam_role_policy_attachment.admin", "aws_iam_role_policy_attachment", {"policy_arn": "arn:aws:iam::aws:policy/AdministratorAccess"})
	denied_with(detection.deny, "never attached by code") with input as workload + [admin]
}
```

A test: **administrator access attached by code is denied**. It asserts that some message of `deny` contains "never attached by code" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is built by a helper from the good plan, with the change this test needs. Local values built first: `admin`.

From `policy/detection_test.rego` (lines 184 to 187):

```rego
test_power_user_access_outside_the_drill_is_denied if {
	power := change("module.app.aws_iam_role_policy_attachment.power", "aws_iam_role_policy_attachment", {"policy_arn": "arn:aws:iam::aws:policy/PowerUserAccess"})
	denied_with(detection.deny, "only on the drill role") with input as workload + [power]
}
```

A test: **power user access outside the drill is denied**. It asserts that some message of `deny` contains "only on the drill role" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is built by a helper from the good plan, with the change this test needs. Local values built first: `power`.

From `policy/detection_test.rego` (lines 189 to 192):

```rego
test_block_public_access_off_outside_the_drill_is_denied if {
	off := change("module.app.aws_s3_bucket_public_access_block.x", "aws_s3_bucket_public_access_block", {"block_public_acls": true, "ignore_public_acls": true, "block_public_policy": false, "restrict_public_buckets": true})
	denied_with(detection.deny, "block_public_policy is off") with input as workload + [off]
}
```

A test: **block public access off outside the drill is denied**. It asserts that some message of `deny` contains "block_public_policy is off" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is built by a helper from the good plan, with the change this test needs. Local values built first: `off`.

From `policy/detection_test.rego` (lines 194 to 197):

```rego
test_an_iam_user_outside_the_drill_is_denied if {
	user := change("module.app.aws_iam_user.x", "aws_iam_user", {"name": "someone", "tags": {"purpose": "x"}})
	denied_with(detection.deny, "only inside the drill module") with input as workload + [user]
}
```

A test: **an iam user outside the drill is denied**. It asserts that some message of `deny` contains "only inside the drill module" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is built by a helper from the good plan, with the change this test needs. Local values built first: `user`.

From `policy/detection_test.rego` (lines 199 to 202):

```rego
test_a_drill_identity_without_the_purpose_tag_is_denied if {
	untagged := change("module.drill[0].aws_iam_user.drill", "aws_iam_user", {"name": "drill-user", "tags": {}})
	denied_with(detection.deny, "purpose") with input as replace_type(workload, "aws_iam_user", [untagged])
}
```

A test: **a drill identity without the purpose tag is denied**. It asserts that some message of `deny` contains "purpose" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with the resources of one type replaced by the ones built for this test (`replace_type(...)`). Local values built first: `untagged`.

From `policy/detection_test.rego` (lines 204 to 207):

```rego
test_a_public_alert_topic_policy_is_denied if {
	open := document([{"Sid": "Open", "Effect": "Allow", "Principal": "*", "Action": "sns:Publish", "Resource": "*"}])
	denied_with(detection.deny, "every principal") with input as workload + [change("module.alerting_global.aws_sns_topic_policy.alerts", "aws_sns_topic_policy", {"policy": open})]
}
```

A test: **a public alert topic policy is denied**. It asserts that some message of `deny` contains "every principal" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is built by a helper from the good plan, with the change this test needs. Local values built first: `open`.

From `policy/detection_test.rego` (lines 209 to 211):

```rego
test_security_hub_without_the_config_recorder_is_denied if {
	denied_with(detection.deny, "AWS Config recording") with input as without(workload, "aws_config_configuration_recorder_status")
}
```

A test: **security hub without the config recorder is denied**. It asserts that some message of `deny` contains "AWS Config recording" (`denied_with` is defined at the top of the file and is true when some message contains the given text); in other words, the rule that guards against this case fires. For this test the input is the good plan with every resource of one type **removed** (`without(...)`).

From `policy/detection_test.rego` (lines 213 to 216):

```rego
test_resources_the_plan_deletes_are_ignored if {
	deleted := {"address": "aws_iam_access_key.old", "type": "aws_iam_access_key", "change": {"actions": ["delete"], "after": null}}
	count(detection.deny) == 0 with input as workload + [deleted]
}
```

A test: **resources the plan deletes are ignored**. It asserts that `deny` is **empty**: this configuration breaks no rule (an "allow" case). For this test the input is built by a helper from the good plan, with the change this test needs. Local values built first: `deleted`.

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

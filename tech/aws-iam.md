# AWS IAM (Identity and Access Management)

## What it is

IAM is the part of AWS that decides **who may do what**. A **principal** is someone or something that can make a request: a person, a program or an AWS service. A **user** is a long-lived identity that can hold **access keys** (a key id and a secret). A **role** is an identity with permissions that a principal can temporarily *assume*; assuming gives short-lived credentials. A **policy** is a JSON document that lists **statements**: each says Allow or Deny, for which **actions** (such as `iam:CreateAccessKey`), on which **resources** (identified by an ARN, an Amazon Resource Name), and optionally under which **conditions**. An **inline policy** is written directly on a role or user.

## Why this repository uses it

IAM is both the thing attacked and the tool of the defense. The drill plants a deliberate weakness: a user with a long-lived key that can assume an over-privileged role. The attacker's calls are IAM calls (`CreateAccessKey`, a policy attachment). Containment is an IAM change: a policy that denies every session of the role issued before now, plus switching the user's keys off. The OPA rules fence the weakness in so it exists only inside the drill.

## Where it appears

| Path | What it does with IAM |
| --- | --- |
| `infra/modules/drill/main.tf` | the drill user, the broad role, its trust policy and the honeytoken user |
| `src/detect_respond/domain/containment.py` | builds the deny-all-before-now policy and the revocation plan |
| `src/detect_respond/infrastructure/boto_revoker.py` | applies it through the IAM API ([boto3.md](boto3.md)) |
| `detections/d1-*.json`, `d3-*.json` | detections on new keys and on administrator grants |
| `policy/detection.rego` | rules: no access keys in code, no administrator attachment, `PowerUserAccess` and IAM users only in the drill |
| `scripts/04-drill-setup.sh`, `scripts/08-contain.sh` | create the drill key; contain |

## How it works underneath

Every request is checked in a fixed order. If any applicable statement says **Deny**, the answer is *denied* (an **explicit deny**). Otherwise, if some applicable statement says **Allow**, it is allowed. Otherwise it is denied by default (an **implicit deny**). A role has a **trust policy** (who may assume it) and **permission policies** (what it may do). Credentials from a role are temporary ([aws-sts.md](aws-sts.md)). When a policy is changed, the change takes effect for requests made afterwards, including requests made by sessions that already exist, because permissions are checked at each call. A **condition key** such as `aws:TokenIssueTime` records facts about the request; here, when the caller's credentials were issued.

## Walkthrough of this repository's use

From `infra/modules/drill/main.tf`:

```hcl
resource "aws_iam_role_policy_attachment" "power_user" {
  role       = aws_iam_role.broad.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}
```

The weakness: far more permission than the role needs. `PowerUserAccess` is a policy AWS maintains (a **managed policy**) that allows almost everything except managing IAM. It exists in the plan only inside the drill module; the rule `PowerUserAccess is allowed only on the drill role` denies it anywhere else.

From `infra/modules/drill/main.tf`:

```hcl
      Action   = "iam:CreateAccessKey"
      Resource = local.user_arn
```

`PowerUserAccess` leaves out IAM, so a second statement lets the role mint a key for the drill user only. That is what allows detection D1 to fire on a call that *succeeds*, as in the lesson's timeline.

From `infra/modules/drill/main.tf`:

```hcl
      Principal = { AWS = local.user_arn }
      Action    = "sts:AssumeRole"
```

The role's trust policy: only the drill user may assume it. The user's own policy allows one thing, assuming that role.

From `infra/modules/drill/main.tf`:

```hcl
  tags = { purpose = "incident-drill" }
```

Every drill identity carries the tag `purpose`, so the teardown can find them, and the OPA rule insists on it.

From `src/detect_respond/domain/containment.py`:

```python
                "Effect": "Deny",
                "Action": "*",
                "Resource": "*",
                "Condition": {"DateLessThan": {"aws:TokenIssueTime": stamp}},
```

The containment policy. It denies **every action on every resource** to any caller whose credentials were issued **before** `stamp`, the moment of containment. The attacker's existing session was issued earlier, so every next call is refused. A new session, issued after the moment, is not affected: the role can be used again once the cause is fixed. An explicit Deny beats the role's `PowerUserAccess` Allow.

From `src/detect_respond/domain/containment.py`:

```python
POLICY_NAME = "deny-all-before-now"
```

The inline policy's name. Using the same name each time means a second run replaces the policy instead of piling up another.

From `src/detect_respond/domain/containment.py`:

```python
    stamp = moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
```

The time is converted to UTC and written in the format IAM expects. A local time zone here would shift the deny window by hours.

From `policy/detection.rego`:

```rego
	msg := sprintf("%s: IAM users exist only inside the drill module", [rc.address])
```

Tenants of this lesson use roles. An IAM user (the source of long-lived keys) is allowed in the plan only inside `module.drill`, and the user's access key is never created by Terraform, because it would sit in the state file: `scripts/04-drill-setup.sh` creates it and stores it only in the AWS CLI profile `drill`.

### Every argument of every AWS resource in this repository

A Terraform `resource` block describes one thing to create. Inside it, each line `name = value` is an **argument** and each `name { ... }` is a **nested block** (a group of arguments for one part of the resource). The column "Kind" says whether the AWS provider requires the argument, whether it is optional, whether it opens a nested block, or whether it is a Terraform **meta-argument** that works on every resource. In "Kind", `required` and `optional` were read from the provider's own schema (version 6.70.0, the one in the lock file), so they are not guesses. A path such as `rule.expiration.days` means the argument `days` inside the nested block `expiration` inside the nested block `rule`. Names that contain `var.` or `local.` or `module.` are values that come from elsewhere in the code ([terraform.md](terraform.md)).

#### `aws_iam_role`

Declared in `infra/modules/drill/main.tf` lines 31 to 46 (`broad`); `infra/modules/posture/main.tf` lines 94 to 106 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `assume_role_policy` | required | The **trust policy**: who may assume the role ([aws-sts.md](aws-sts.md)). The role's permissions are separate. | `jsonencode({ Version = "2012-10-17" Statement = [{ Sid = "OnlyTheDr...` / `jsonencode({ Version = "2012-10-17" Statement = [{ Effect = "Allow"...` |
| `name` | optional | The name of the role; it appears in the role's ARN. | `var.role_name` / `"${var.name}-config-recorder"` |
| `tags` | optional | Labels (key and value text) attached to the resource. They cost nothing and do nothing by themselves; people and scripts find and group resources by them, and the provider's `default_tags` add the project-wide ones. | `{ purpose = "incident-drill" }` |
| `depends_on` | meta-argument | A Terraform **meta-argument** (it works on every resource and is not sent to AWS): create this resource only after the listed ones. Terraform normally works out the order from references; `depends_on` states an order that no reference shows, for example a policy that must exist before a service first writes. | `[aws_iam_user.drill]` |

#### `aws_iam_role_policy`

Declared in `infra/modules/drill/main.tf` lines 56 to 69 (`mint_a_key_for_the_drill_user`); `infra/modules/posture/main.tf` lines 113 to 135 (`deliver`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `name` | optional | The name of this inline policy within the role. | `"create-access-key-for-the-drill-user"` / `"deliver-to-the-config-bucket"` |
| `policy` | required | The permissions, as JSON text: what the role may do. See [aws-iam.md](aws-iam.md). | `jsonencode({ Version = "2012-10-17" Statement = [{ Sid = "CreateAKe...` / `jsonencode({ Version = "2012-10-17" Statement = [ { Sid = "CheckThe...` |
| `role` | required | The role the policy is embedded in (by name). | `aws_iam_role.broad.name` / `aws_iam_role.config.name` |

#### `aws_iam_role_policy_attachment`

Declared in `infra/modules/drill/main.tf` lines 49 to 52 (`power_user`); `infra/modules/posture/main.tf` lines 108 to 111 (`config`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `policy_arn` | required | The ARN of an existing managed policy (one that is not embedded in the role). | `"arn:aws:iam::aws:policy/PowerUserAccess"` / `"arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"` |
| `role` | required | The role to attach the managed policy to. | `aws_iam_role.broad.name` / `aws_iam_role.config.name` |

#### `aws_iam_user`

Declared in `infra/modules/drill/main.tf` lines 8 to 12 (`drill`); `infra/modules/drill/main.tf` lines 108 to 114 (`honeytoken`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `name` | required | The name of the IAM user (a long-lived identity, used here only for the drill). | `var.user_name` / `"honeytoken-svc"` |
| `tags` | optional | Labels (key and value text) attached to the resource. They cost nothing and do nothing by themselves; people and scripts find and group resources by them, and the provider's `default_tags` add the project-wide ones. | `{ purpose = "incident-drill" }` / `{ purpose = "honeytoken" }` |
| `count` | meta-argument | A Terraform meta-argument: make this many copies (here 0 or 1, which switches the resource on or off with a variable). | `var.enable_honeytoken ? 1 : 0` |

#### `aws_iam_user_policy`

Declared in `infra/modules/drill/main.tf` lines 15 to 29 (`assume_broad_role`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `name` | optional | The name of the inline policy. | `"assume-the-drill-role"` |
| `policy` | required | The policy document as JSON text, written in HCL with `jsonencode(...)` ([json.md](json.md)). | `jsonencode({ Version = "2012-10-17" Statement = [{ Sid = "AssumeOnl...` |
| `user` | required | The user the policy is embedded in. | `aws_iam_user.drill.name` |

## Try it yourself

```bash
.venv/bin/python -m detect_respond contain --access-key-id AKIADRILLEXAMPLE0001 | cut -c1-110
```

Expect `dry run, nothing changed; to do it, add --apply:` and then two commands: `aws iam put-role-policy --role-name drill-broad-role --policy-name deny-all-before-now ...` and `aws iam update-access-key --user-name drill-user --access-key-id AKIADRILLEXAMPLE0001 --status Inactive`. Nothing was sent anywhere.

```bash
.venv/bin/python -c "
from datetime import UTC, datetime
from detect_respond.domain.containment import deny_sessions_before
print(deny_sessions_before(datetime(2026, 10, 22, 11, 9, 48, tzinfo=UTC))['Statement'][0]['Condition'])"
```

Expect `{'DateLessThan': {'aws:TokenIssueTime': '2026-10-22T11:09:48Z'}}`.

```bash
opa test policy -v | grep -c "power_user\|administrator\|access_key\|iam_user"
```

Expect `4`: the tests that deny an access key in code, administrator access, `PowerUserAccess` outside the drill and an IAM user outside the drill.

## Mistakes people make

- Revoking only the access key. Role sessions already issued stay valid until they expire; the deny-before-now policy is what stops them.
- Deleting the key instead of deactivating it. Deletion destroys evidence.
- Writing the cut-off time in local time.
- Attaching `AdministratorAccess` "to get going". The rules reject it everywhere, and detection D3 watches for it.
- Letting Terraform create an access key. The secret would be stored in the state file.

## Check yourself

1. What is the order of an IAM decision? *Any explicit deny wins; otherwise one allow is enough; otherwise implicit deny.*
2. What does `aws:TokenIssueTime` let the containment policy do? *Deny only sessions whose credentials were issued before the moment of containment.*
3. Why must containment also act on the role and not only the key? *The attacker holds a role session; deactivating the user's key does not end it.*
4. Why do drill identities carry a `purpose` tag? *So teardown can find them.*
5. Why does the Terraform not create the drill user's access key? *The secret would be stored in the state file.*

## Further reading

- IAM user guide: <https://docs.aws.amazon.com/IAM/latest/UserGuide/>
- Policy evaluation logic: <https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html>
- Revoking role sessions: <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_revoke-sessions.html>

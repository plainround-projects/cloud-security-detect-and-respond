# AWS Config

## What it is

AWS Config records the **configuration of your resources over time**: what a bucket's settings were, when they changed, and what they changed from. A **configuration recorder** watches the resources and a **delivery channel** writes snapshots and history to an S3 bucket. Config can also judge configurations against rules, and other services (here Security Hub, [aws-security-hub.md](aws-security-hub.md)) use its records to do the same.

## Why this repository uses it

The posture part of the lesson asks: how weak is this account right now, and what has changed? Security Hub's controls evaluate resource settings, and they need Config's records to do so. Without the recorder the controls cannot be checked, which is why the OPA policy denies a plan that enables Security Hub without the recorder.

## Where it appears

| Path | What it does |
| --- | --- |
| `infra/modules/posture/main.tf` | the recorder, its role, the delivery channel, its bucket and the recorder switch |
| `policy/detection.rego` | rule: Security Hub controls need the Config recorder |
| `infra/environments/workload/variables.tf` | `enable_posture` turns the whole module on or off (default on) |

## How it works underneath

The recorder needs a role it can assume (a trust policy for `config.amazonaws.com`) and permission to write to the bucket. It can record all supported resource types, including global ones such as IAM. The delivery channel must exist before the recorder is switched on, and switching on is a separate resource (`recorder_status`). Config bills per recorded configuration change, so leaving it on in a sandbox costs money every day.

## Walkthrough of this repository's use

From `infra/modules/posture/main.tf`:

```hcl
resource "aws_iam_role_policy_attachment" "config" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}
```

The recorder's role gets AWS's own managed policy for reading resource settings. A managed policy is a policy AWS maintains. The role's trust statement names only the Config service, and only for this account (`aws:SourceAccount`).

From `infra/modules/posture/main.tf`:

```hcl
        Resource  = "arn:aws:s3:::${local.config_bucket}/AWSLogs/${var.account_id}/Config/*"
```

The extra policy `deliver-to-the-config-bucket` lets the role write snapshots under one prefix of one bucket, and only with the condition `bucket-owner-full-control`.

From `infra/modules/posture/main.tf`:

```hcl
  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
```

Record every supported resource type, including the global ones.

From `infra/modules/posture/main.tf`:

```hcl
resource "aws_config_configuration_recorder_status" "this" {
  name       = aws_config_configuration_recorder.this.name
  is_enabled = true

  depends_on = [aws_config_delivery_channel.this]
}
```

Switching the recorder on is its own resource, and it depends on the delivery channel. Terraform enforces the order: recorder, delivery channel, then on.

From `policy/detection.rego`:

```rego
	count(planned("aws_config_configuration_recorder_status")) == 0
	msg := "Security Hub controls need AWS Config recording; enable the recorder"
```

The rule reads: if a Security Hub subscription is planned and no recorder-status resource is, deny. The test `test_security_hub_without_the_config_recorder_is_denied` proves the rule can fire.

## Try it yourself

```bash
python3 -c "
import json
p = json.load(open('build/workload.json'))
print(sorted(x['type'] for x in p['resource_changes'] if x['type'].startswith('aws_config')))"
```

After `make plan`, expect `['aws_config_configuration_recorder', 'aws_config_configuration_recorder_status', 'aws_config_delivery_channel']`.

```bash
opa test policy -v | grep recorder
```

Expect `PASS` for `test_security_hub_without_the_config_recorder_is_denied`.

## Mistakes people make

- Enabling Security Hub controls without the recorder: the controls then show nothing useful.
- Switching the recorder on before the delivery channel exists.
- Leaving Config on after the lesson. It bills per change; `scripts/10-teardown.sh` removes it with the workload account's resources, and the runbook says to check the bill the next day.
- Giving the recorder's role wide S3 rights. This one can write one prefix only.

## Check yourself

1. What does the recorder do? *Records the configuration of resources and their changes over time.*
2. What does the delivery channel do? *Writes the snapshots and history to a bucket.*
3. Why a separate `recorder_status` resource? *Switching on is its own step, and must come after the delivery channel exists.*
4. Why does a policy rule tie Security Hub to the recorder? *Security Hub controls read Config's records; without the recorder they cannot be evaluated.*
5. What does leaving Config on cost? *A charge for each recorded configuration change, every day it stays on.*

## Further reading

- AWS Config developer guide: <https://docs.aws.amazon.com/config/latest/developerguide/>
- Terraform `aws_config_configuration_recorder` (provider 6.x): <https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_configuration_recorder>

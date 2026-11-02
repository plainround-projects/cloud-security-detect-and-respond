# Amazon SNS (Simple Notification Service)

## What it is

SNS delivers messages to subscribers. A **topic** is a named channel. Anything allowed to publish sends a message to the topic, and SNS forwards it to every **subscription**: an email address, a phone number, a queue or a function. An email subscription starts **pending** and only works after the address owner clicks the link in the message AWS sends. A **topic policy** says who may publish.

## Why this repository uses it

A detection that nobody reads is no detection. SNS is the last step of the fast path: an EventBridge rule matches an API call and publishes the alert text to a topic, and the topic emails the responder ([aws-eventbridge.md](aws-eventbridge.md)). Email is the simplest target that needs no extra service.

## Where it appears

| Path | What it does |
| --- | --- |
| `infra/modules/alerting/main.tf` | the topic, its key, its policy and the email subscription; one set per Region |
| `policy/detection.rego` | rules: the topic must be encrypted, and no statement may grant every principal |
| `scripts/02-deploy-workload.sh` | reminds you to confirm the three pending subscriptions |

## How it works underneath

The service that publishes (EventBridge here) is a **principal** and needs permission in the topic policy. If the topic is encrypted with a customer-managed key ([aws-kms.md](aws-kms.md)), the publisher also needs permission on the key. Topics are per Region, so the three Regions have three topics and three subscriptions. SNS sends the message text as it received it; for email, the subject is generic.

## Walkthrough of this repository's use

From `infra/modules/alerting/main.tf`:

```hcl
resource "aws_sns_topic" "alerts" {
  name              = "${var.name}-alerts"
  kms_master_key_id = module.key.key_arn
}
```

`kms_master_key_id` turns on encryption at rest with a key made for this topic. Alerts name callers, addresses and resources, which is information worth protecting. The OPA rule `the alert topic must be encrypted` checks it.

From `infra/modules/alerting/main.tf`:

```hcl
    Sid       = "EventsPublishesEncryptedAlerts"
    Effect    = "Allow"
    Principal = { Service = "events.amazonaws.com" }
    Action    = ["kms:GenerateDataKey*", "kms:Decrypt"]
    Resource  = "*"
    Condition = { StringEquals = { "aws:SourceAccount" = var.account_id } }
```

The key policy statement that lets EventBridge publish to the encrypted topic: it may ask for data keys and decrypt, and only on behalf of this account (`aws:SourceAccount`).

From `infra/modules/alerting/main.tf`:

```hcl
      Sid       = "EventsPublishes"
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.alerts.arn
      Condition = { StringEquals = { "aws:SourceAccount" = var.account_id } }
```

The topic policy: only the EventBridge service, only to publish, only to this topic, only for this account. A policy that granted every principal (`Principal = "*"`) would let anyone send fake alerts, and the OPA rule `grants access to every principal` denies it.

From `infra/modules/alerting/main.tf`:

```hcl
resource "aws_sns_topic_subscription" "responder" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
```

An email subscription. The comment above it says the subscription stays pending until the address confirms it. After `make up` you must open each of the three confirmation emails (one per Region) or **no alert reaches you**, and nothing fails in Terraform.

### Every argument of every AWS resource in this repository

A Terraform `resource` block describes one thing to create. Inside it, each line `name = value` is an **argument** and each `name { ... }` is a **nested block** (a group of arguments for one part of the resource). The column "Kind" says whether the AWS provider requires the argument, whether it is optional, whether it opens a nested block, or whether it is a Terraform **meta-argument** that works on every resource. In "Kind", `required` and `optional` were read from the provider's own schema (version 6.70.0, the one in the lock file), so they are not guesses. A path such as `rule.expiration.days` means the argument `days` inside the nested block `expiration` inside the nested block `rule`. Names that contain `var.` or `local.` or `module.` are values that come from elsewhere in the code ([terraform.md](terraform.md)).

#### `aws_sns_topic`

Declared in `infra/modules/alerting/main.tf` lines 36 to 39 (`alerts`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `kms_master_key_id` | optional | The key that encrypts messages at rest in the topic. | `module.key.key_arn` |
| `name` | optional | The name of the topic. | `"${var.name}-alerts"` |

#### `aws_sns_topic_policy`

Declared in `infra/modules/alerting/main.tf` lines 41 to 55 (`alerts`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `arn` | required | The topic the policy is attached to. | `aws_sns_topic.alerts.arn` |
| `policy` | required | Who may publish to or subscribe to the topic (here: the EventBridge service for one rule). | `jsonencode({ Version = "2012-10-17" Statement = [{ Sid = "EventsPub...` |

#### `aws_sns_topic_subscription`

Declared in `infra/modules/alerting/main.tf` lines 58 to 62 (`responder`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `endpoint` | required | The address that receives them. | `var.alert_email` |
| `protocol` | required | How messages are delivered: `email` sends a mail after the address confirms. | `"email"` |
| `topic_arn` | required | The topic to subscribe to. | `aws_sns_topic.alerts.arn` |

## Try it yourself

```bash
python3 -c "
import json
p = json.load(open('build/workload.json'))
s = [x['change']['after'] for x in p['resource_changes'] if x['type'] == 'aws_sns_topic_subscription']
print(len(s), s[0]['protocol'], s[0]['endpoint'])"
```

After `make plan`, expect `3 email alerts@example.com`: one subscription per Region, to the placeholder address.

```bash
opa test policy -v | grep -E "topic"
```

Expect three `PASS` lines: an unencrypted topic is denied, a topic whose key is only known after apply is allowed, and a public topic policy is denied.

## Mistakes people make

- Not confirming the email subscription. A pending subscription receives nothing.
- Subscribing in one Region only. Each Region's rules publish to that Region's topic.
- A topic policy open to everyone, so anyone can publish a fake alert.
- Encrypting the topic with a key that EventBridge cannot use, so publishing fails silently.
- Putting secrets in the alert text. Anyone with access to the mailbox reads it.

## Check yourself

1. What is a topic? *A named channel that forwards each message to all its subscriptions.*
2. Why is an email subscription "pending"? *The address owner must confirm it from a link in the email AWS sends.*
3. Why does the topic need a key statement for EventBridge? *The topic is encrypted, and the publisher must be able to generate data keys and decrypt.*
4. Why three topics? *A topic and its rules live in one Region, and the repository watches three.*
5. What does `aws:SourceAccount` add to a service statement? *It limits the statement to requests made on behalf of this account.*

## Further reading

- SNS developer guide: <https://docs.aws.amazon.com/sns/latest/dg/>
- Encrypting a topic: <https://docs.aws.amazon.com/sns/latest/dg/sns-server-side-encryption.html>
- Terraform `aws_sns_topic` (provider 6.x): <https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic>

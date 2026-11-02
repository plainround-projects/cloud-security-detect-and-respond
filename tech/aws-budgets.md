# AWS Budgets

## What it is

AWS Budgets lets you set a spending limit for an account and get an email when actual or forecast spending crosses a percentage of it. It does not stop spending; it warns.

## Why this repository uses it

The runbook says to use sandbox accounts with a budget alert and to remove the temporary exception the same day. A forgotten posture service, trail or key keeps billing quietly: AWS Config and Security Hub charge while they exist. A budget with an email makes the surprise visible within hours and not at the end of the month.

## Where it appears

| Path | What it does |
| --- | --- |
| `infra/modules/budget/main.tf` | one monthly cost budget with two notifications |
| `infra/environments/workload/variables.tf` | `monthly_budget_usd` (default 20) and `alert_email` |

## How it works underneath

AWS compares your month-to-date cost (an **actual** figure, which is delayed by hours) and a **forecast** (a projection to the end of the month) with the limit. When a threshold is crossed it emails the subscribers. The first budgets in an account are free.

## Walkthrough of this repository's use

From `infra/modules/budget/main.tf`:

```hcl
resource "aws_budgets_budget" "this" {
  name         = var.name
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
```

- `budget_type = "COST"`: money, not usage.
- `limit_amount`: the API wants text, so `tostring(...)` converts the number (20).
- `time_unit = "MONTHLY"`: the limit resets every month.

From `infra/modules/budget/main.tf`:

```hcl
  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.email]
  }
```

Email when actual spending is above 80 percent of the limit. The second notification uses `notification_type = "FORECASTED"` and `threshold = 100`: email when the forecast says the month will exceed the limit.

### Every argument of every AWS resource in this repository

A Terraform `resource` block describes one thing to create. Inside it, each line `name = value` is an **argument** and each `name { ... }` is a **nested block** (a group of arguments for one part of the resource). The column "Kind" says whether the AWS provider requires the argument, whether it is optional, whether it opens a nested block, or whether it is a Terraform **meta-argument** that works on every resource. In "Kind", `required` and `optional` were read from the provider's own schema (version 6.70.0, the one in the lock file), so they are not guesses. A path such as `rule.expiration.days` means the argument `days` inside the nested block `expiration` inside the nested block `rule`. Names that contain `var.` or `local.` or `module.` are values that come from elsewhere in the code ([terraform.md](terraform.md)).

#### `aws_budgets_budget`

Declared in `infra/modules/budget/main.tf` lines 1 to 23 (`this`).

| Argument | Kind | What it means | Value in this repository |
| --- | --- | --- | --- |
| `budget_type` | required | What the budget measures: `COST` is money spent (other values count usage, reservations or savings plans). | `"COST"` |
| `limit_amount` | optional | The amount of the limit, as text, in the unit below. | `tostring(var.monthly_limit_usd)` |
| `limit_unit` | optional | The unit of the limit: a currency code such as `USD`. | `"USD"` |
| `name` | optional | The name of the budget. | `var.name` |
| `notification.comparison_operator` | required | How the spend is compared with the threshold: `GREATER_THAN` sends the message once the spend is above it. | `"GREATER_THAN"` |
| `notification.notification_type` | required | `ACTUAL` reacts to money already spent; `FORECASTED` reacts to what AWS predicts will be spent. | `"ACTUAL"` / `"FORECASTED"` |
| `notification.subscriber_email_addresses` | optional | The e-mail addresses that receive the message. | `[var.email]` |
| `notification.threshold` | required | The number that triggers the message; meaning depends on `threshold_type`. | `80` / `100` |
| `notification.threshold_type` | required | `PERCENTAGE` means the threshold is a percent of the limit; `ABSOLUTE_VALUE` would mean an amount. | `"PERCENTAGE"` |
| `time_unit` | required | How often the budget starts again: `MONTHLY` here. | `"MONTHLY"` |

## Try it yourself

```bash
python3 -c "
import json
p = json.load(open('build/workload.json'))
b = [x['change']['after'] for x in p['resource_changes'] if x['type'] == 'aws_budgets_budget'][0]
print(b['limit_amount'], b['limit_unit'], b['time_unit'], [n['threshold'] for n in b['notification']])"
```

After `make plan`, expect `20 USD MONTHLY [80, 100]`.

```bash
grep -n "monthly_budget_usd" -A3 infra/environments/workload/variables.tf
```

Expect the variable, its description and the default `20`.

## Mistakes people make

- Believing a budget stops spending. It only notifies.
- Using the budget as the only guard. Delete resources the same day, and check the bill next day.
- Forgetting to confirm the email address, so alerts go nowhere. Check your inbox after the first deploy.

## Check yourself

1. What does a budget do when the limit is crossed? *Sends an email; it does not stop anything.*
2. What is the difference between actual and forecast? *Actual is spending so far; forecast is the projected month-end spending.*
3. Why `tostring`? *The API expects the amount as text.*
4. Which two thresholds are used? *80 percent actual and 100 percent forecast.*
5. What is the runbook's rule about cost? *Use sandbox accounts with a budget alert, and remove the temporary exception the same day.*

## Further reading

- AWS Budgets user guide: <https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html>
- Terraform `aws_budgets_budget` (provider 6.x): <https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/budgets_budget>

# Alerting for one Region: a key, a topic that emails the responder, and one rule per detection deployed here. EventBridge
# only sees events in its own Region, which is why this module is instantiated once per Region that matters.
locals {
  # The text the responder receives. {..} fields are filled here, <..> fields by the rule's input transformer when it fires.
  alert_paths = {
    time     = "$.time"
    who      = "$.detail.userIdentity.arn"
    source   = "$.detail.eventSource"
    name     = "$.detail.eventName"
    params   = "$.detail.requestParameters"
    ip       = "$.detail.sourceIPAddress"
    agent    = "$.detail.userAgent"
    region   = "$.detail.awsRegion"
    event_id = "$.detail.eventID"
  }
}

module "key" {
  source = "../kms-key"

  alias       = "${var.name}-alerts"
  description = "Encrypts the alert topic in ${var.region}."
  account_id  = var.account_id
  region      = var.region

  statements = [{
    Sid       = "EventsPublishesEncryptedAlerts"
    Effect    = "Allow"
    Principal = { Service = "events.amazonaws.com" }
    Action    = ["kms:GenerateDataKey*", "kms:Decrypt"]
    Resource  = "*"
    Condition = { StringEquals = { "aws:SourceAccount" = var.account_id } }
  }]
}

resource "aws_sns_topic" "alerts" {
  name              = "${var.name}-alerts"
  kms_master_key_id = module.key.key_arn
}

resource "aws_sns_topic_policy" "alerts" {
  arn = aws_sns_topic.alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "EventsPublishes"
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.alerts.arn
      Condition = { StringEquals = { "aws:SourceAccount" = var.account_id } }
    }]
  })
}

# The subscription stays pending until the address confirms it from the email AWS sends.
resource "aws_sns_topic_subscription" "responder" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_event_rule" "detection" {
  for_each = var.detections

  name = "${var.name}-${lower(each.key)}"
  # The pattern is the detection file, unchanged, so what the tests replay is what runs.
  event_pattern = each.value.pattern_json
  description   = "${each.key}: ${each.value.title}"
  state         = each.value.state
}

resource "aws_cloudwatch_event_target" "alert" {
  for_each = var.detections

  rule = aws_cloudwatch_event_rule.detection[each.key].name
  arn  = aws_sns_topic.alerts.arn

  input_transformer {
    input_paths = local.alert_paths
    input_template = format("\"%s\"", replace(
      replace(replace(replace(replace(var.template, "{id}", each.key), "{title}", each.value.title), "{severity}", each.value.severity), "{first_step}", each.value.first_step),
      "\n", "\\n"
    ))
  }
}

package detection_test

import data.detection
import rego.v1

change(address, type, after) := {"address": address, "type": type, "change": {"actions": ["create"], "after": after, "after_unknown": {}}}

document(statements) := json.marshal({"Version": "2012-10-17", "Statement": statements})

bucket := "detect-archive-000000000001"

trail_arn := "arn:aws:cloudtrail:eu-west-1:000000000000:trail/central-trail"

archive_policy := document([
	{"Sid": "TrailWrites", "Effect": "Allow", "Principal": {"Service": "cloudtrail.amazonaws.com"}, "Action": "s3:PutObject", "Resource": "*", "Condition": {"StringEquals": {"aws:SourceArn": trail_arn}}},
	{"Sid": "NobodyDeletes", "Effect": "Deny", "Principal": {"AWS": "*"}, "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"], "Resource": "*"},
])

archive := [
	change("module.log_archive.aws_s3_bucket.archive", "aws_s3_bucket", {"bucket": bucket, "object_lock_enabled": true}),
	change("module.log_archive.aws_s3_bucket_object_lock_configuration.archive", "aws_s3_bucket_object_lock_configuration", {"bucket": bucket, "rule": [{"default_retention": [{"mode": "COMPLIANCE", "days": 1}]}]}),
	change("module.log_archive.aws_s3_bucket_versioning.archive", "aws_s3_bucket_versioning", {"bucket": bucket, "versioning_configuration": [{"status": "Enabled"}]}),
	change("module.log_archive.aws_s3_bucket_public_access_block.archive", "aws_s3_bucket_public_access_block", {"bucket": bucket, "block_public_acls": true, "ignore_public_acls": true, "block_public_policy": true, "restrict_public_buckets": true}),
	change("module.log_archive.aws_s3_bucket_server_side_encryption_configuration.archive", "aws_s3_bucket_server_side_encryption_configuration", {"bucket": bucket, "rule": [{"apply_server_side_encryption_by_default": [{"sse_algorithm": "aws:kms"}]}]}),
	change("module.log_archive.aws_s3_bucket_policy.archive", "aws_s3_bucket_policy", {"bucket": bucket, "policy": archive_policy}),
	change("module.archive_key.aws_kms_key.this", "aws_kms_key", {"enable_key_rotation": true}),
]

detection_rule(id, state) := change(sprintf("module.alerting_global.aws_cloudwatch_event_rule.detection[\"%s\"]", [upper(id)]), "aws_cloudwatch_event_rule", {"name": sprintf("detect-global-%s", [id]), "state": state})

detection_target(id) := change(sprintf("module.alerting_global.aws_cloudwatch_event_target.alert[\"%s\"]", [upper(id)]), "aws_cloudwatch_event_target", {"rule": sprintf("detect-global-%s", [id])})

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

without(resources, type) := {"resource_changes": [rc | some rc in resources; rc.type != type]}

replace_type(resources, type, extra) := {"resource_changes": array.concat([rc | some rc in resources; rc.type != type], extra)}

plus(resources, extra) := {"resource_changes": array.concat(resources, extra)}

denied_with(messages, fragment) if {
	some message in messages
	contains(message, fragment)
}

test_the_archive_is_allowed if {
	count(detection.deny) == 0 with input as {"resource_changes": archive}
}

test_the_workload_is_allowed if {
	count(detection.deny) == 0 with input as {"resource_changes": workload}
}

test_an_archive_without_object_lock_in_compliance_mode_is_denied if {
	governance := change("x", "aws_s3_bucket_object_lock_configuration", {"bucket": bucket, "rule": [{"default_retention": [{"mode": "GOVERNANCE", "days": 1}]}]})
	denied_with(detection.deny, "compliance mode") with input as replace_type(archive, "aws_s3_bucket_object_lock_configuration", [governance])
}

test_an_archive_with_no_lock_configuration_is_denied if {
	denied_with(detection.deny, "compliance mode") with input as without(archive, "aws_s3_bucket_object_lock_configuration")
}

test_an_archive_whose_policy_lets_deletes_through_is_denied if {
	soft := document([{"Sid": "TrailWrites", "Effect": "Allow", "Principal": {"Service": "cloudtrail.amazonaws.com"}, "Action": "s3:PutObject", "Resource": "*", "Condition": {"StringEquals": {"aws:SourceArn": trail_arn}}}])
	denied_with(detection.deny, "deny deleting objects") with input as replace_type(archive, "aws_s3_bucket_policy", [change("x", "aws_s3_bucket_policy", {"bucket": bucket, "policy": soft})])
}

test_a_delete_deny_that_names_one_principal_only_is_denied if {
	narrow := document([{"Sid": "NobodyDeletes", "Effect": "Deny", "Principal": {"AWS": "arn:aws:iam::000000000001:root"}, "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"], "Resource": "*"}])
	denied_with(detection.deny, "deny deleting objects") with input as replace_type(archive, "aws_s3_bucket_policy", [change("x", "aws_s3_bucket_policy", {"bucket": bucket, "policy": narrow})])
}

test_an_archive_without_versioning_is_denied if {
	denied_with(detection.deny, "versioning") with input as without(archive, "aws_s3_bucket_versioning")
}

test_an_archive_without_block_public_access_is_denied if {
	denied_with(detection.deny, "Block Public Access") with input as without(archive, "aws_s3_bucket_public_access_block")
}

test_an_archive_with_default_encryption_is_denied if {
	aes := change("x", "aws_s3_bucket_server_side_encryption_configuration", {"bucket": bucket, "rule": [{"apply_server_side_encryption_by_default": [{"sse_algorithm": "AES256"}]}]})
	denied_with(detection.deny, "customer-managed key") with input as replace_type(archive, "aws_s3_bucket_server_side_encryption_configuration", [aes])
}

test_an_archive_policy_that_lets_the_account_root_write_is_denied if {
	loose := document([
		{"Sid": "Anyone", "Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::000000000001:root"}, "Action": "s3:PutObject", "Resource": "*"},
		{"Sid": "NobodyDeletes", "Effect": "Deny", "Principal": {"AWS": "*"}, "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"], "Resource": "*"},
	])
	denied_with(detection.deny, "one trail, pinned") with input as replace_type(archive, "aws_s3_bucket_policy", [change("x", "aws_s3_bucket_policy", {"bucket": bucket, "policy": loose})])
}

test_a_trail_service_grant_without_the_source_arn_pin_is_denied if {
	unpinned := document([
		{"Sid": "TrailWrites", "Effect": "Allow", "Principal": {"Service": "cloudtrail.amazonaws.com"}, "Action": "s3:PutObject", "Resource": "*"},
		{"Sid": "NobodyDeletes", "Effect": "Deny", "Principal": {"AWS": "*"}, "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"], "Resource": "*"},
	])
	denied_with(detection.deny, "one trail, pinned") with input as replace_type(archive, "aws_s3_bucket_policy", [change("x", "aws_s3_bucket_policy", {"bucket": bucket, "policy": unpinned})])
}

test_a_key_without_rotation_is_denied if {
	denied_with(detection.deny, "rotation") with input as replace_type(archive, "aws_kms_key", [change("module.archive_key.aws_kms_key.this", "aws_kms_key", {"enable_key_rotation": false})])
}

test_a_trail_for_one_region_is_denied if {
	one := change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": false, "enable_log_file_validation": true, "s3_bucket_name": bucket, "kms_key_id": "k"})
	denied_with(detection.deny, "every Region") with input as replace_type(workload, "aws_cloudtrail", [one])
}

test_a_trail_without_log_file_validation_is_denied if {
	unvalidated := change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": true, "enable_log_file_validation": false, "s3_bucket_name": bucket, "kms_key_id": "k"})
	denied_with(detection.deny, "log file validation") with input as replace_type(workload, "aws_cloudtrail", [unvalidated])
}

test_a_trail_that_logs_into_a_bucket_of_the_same_account_is_denied if {
	local := change("module.logs.aws_s3_bucket.local", "aws_s3_bucket", {"bucket": "local-logs"})
	trail := change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": true, "enable_log_file_validation": true, "s3_bucket_name": "local-logs", "kms_key_id": "k"})
	denied_with(detection.deny, "outside this account") with input as replace_type(workload, "aws_cloudtrail", [trail]).resource_changes + [local]
}

test_a_trail_with_no_log_bucket_is_denied if {
	none := change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": true, "enable_log_file_validation": true, "kms_key_id": "k"})
	denied_with(detection.deny, "needs a log bucket") with input as replace_type(workload, "aws_cloudtrail", [none])
}

test_a_trail_without_a_key_is_denied if {
	unkeyed := change("module.central_trail.aws_cloudtrail.central", "aws_cloudtrail", {"is_multi_region_trail": true, "enable_log_file_validation": true, "s3_bucket_name": bucket})
	denied_with(detection.deny, "held by the security account") with input as replace_type(workload, "aws_cloudtrail", [unkeyed])
}

test_a_rule_with_no_target_is_denied if {
	denied_with(detection.deny, "alerts nobody") with input as workload + [detection_rule("d5", "ENABLED")]
}

test_an_unencrypted_alert_topic_is_denied if {
	denied_with(detection.deny, "must be encrypted") with input as replace_type(workload, "aws_sns_topic", [change("module.alerting_global.aws_sns_topic.alerts", "aws_sns_topic", {"name": "t"})])
}

test_an_alert_topic_whose_key_is_known_after_apply_is_allowed if {
	unknown := {"address": "module.alerting_global.aws_sns_topic.alerts", "type": "aws_sns_topic", "change": {"actions": ["create"], "after": {"name": "t"}, "after_unknown": {"kms_master_key_id": true}}}
	count(detection.deny) == 0 with input as replace_type(workload, "aws_sns_topic", [unknown])
}

test_a_missing_detection_is_denied if {
	no_d3 := {"resource_changes": [rc | some rc in workload; not endswith(object.get(rc.change.after, "name", ""), "-d3"); not endswith(object.get(rc.change.after, "rule", ""), "-d3")]}
	denied_with(detection.deny, "detection D3 is not deployed") with input as no_d3
}

test_d4_without_the_read_only_rule_state_is_denied if {
	plain := {"resource_changes": [rc | some rc in workload; rc.change.after.name != "detect-global-d4"]}
	denied_with(detection.deny, "read-only") with input as plain.resource_changes + [detection_rule("d4", "ENABLED")]
}

test_an_access_key_in_the_state_is_denied if {
	denied_with(detection.deny, "state") with input as workload + [change("module.drill[0].aws_iam_access_key.k", "aws_iam_access_key", {"user": "drill-user"})]
}

test_administrator_access_attached_by_code_is_denied if {
	admin := change("module.drill[0].aws_iam_role_policy_attachment.admin", "aws_iam_role_policy_attachment", {"policy_arn": "arn:aws:iam::aws:policy/AdministratorAccess"})
	denied_with(detection.deny, "never attached by code") with input as workload + [admin]
}

test_power_user_access_outside_the_drill_is_denied if {
	power := change("module.app.aws_iam_role_policy_attachment.power", "aws_iam_role_policy_attachment", {"policy_arn": "arn:aws:iam::aws:policy/PowerUserAccess"})
	denied_with(detection.deny, "only on the drill role") with input as workload + [power]
}

test_block_public_access_off_outside_the_drill_is_denied if {
	off := change("module.app.aws_s3_bucket_public_access_block.x", "aws_s3_bucket_public_access_block", {"block_public_acls": true, "ignore_public_acls": true, "block_public_policy": false, "restrict_public_buckets": true})
	denied_with(detection.deny, "block_public_policy is off") with input as workload + [off]
}

test_an_iam_user_outside_the_drill_is_denied if {
	user := change("module.app.aws_iam_user.x", "aws_iam_user", {"name": "someone", "tags": {"purpose": "x"}})
	denied_with(detection.deny, "only inside the drill module") with input as workload + [user]
}

test_a_drill_identity_without_the_purpose_tag_is_denied if {
	untagged := change("module.drill[0].aws_iam_user.drill", "aws_iam_user", {"name": "drill-user", "tags": {}})
	denied_with(detection.deny, "purpose") with input as replace_type(workload, "aws_iam_user", [untagged])
}

test_a_public_alert_topic_policy_is_denied if {
	open := document([{"Sid": "Open", "Effect": "Allow", "Principal": "*", "Action": "sns:Publish", "Resource": "*"}])
	denied_with(detection.deny, "every principal") with input as workload + [change("module.alerting_global.aws_sns_topic_policy.alerts", "aws_sns_topic_policy", {"policy": open})]
}

test_security_hub_without_the_config_recorder_is_denied if {
	denied_with(detection.deny, "AWS Config recording") with input as without(workload, "aws_config_configuration_recorder_status")
}

test_resources_the_plan_deletes_are_ignored if {
	deleted := {"address": "aws_iam_access_key.old", "type": "aws_iam_access_key", "change": {"actions": ["delete"], "after": null}}
	count(detection.deny) == 0 with input as workload + [deleted]
}

# Guardrails for the detection and response layer, evaluated on `terraform show -json` output of either environment.
# Every rule has a deny test and an allow test in detection_test.rego.
package detection

import rego.v1

planned(type) := {rc | some rc in input.resource_changes; rc.type == type; rc.change.after != null}

as_list(value) := value if is_array(value)

as_list(value) := [value] if not is_array(value)

statements(document) := as_list(document.Statement)

in_drill(rc) if startswith(rc.address, "module.drill")

known_or_set(rc, attribute) if rc.change.after[attribute] != null

known_or_set(rc, attribute) if rc.change.after_unknown[attribute] == true

public_principal(statement) if statement.Principal == "*"

public_principal(statement) if "*" in as_list(statement.Principal.AWS)

# ---- The archive (security environment) -------------------------------------------------------------------------

archive_buckets := {rc.change.after.bucket | some rc in planned("aws_s3_bucket"); rc.change.after.object_lock_enabled == true}

locked_in_compliance_mode(name) if {
	some rc in planned("aws_s3_bucket_object_lock_configuration")
	rc.change.after.bucket == name
	some rule in rc.change.after.rule
	some retention in rule.default_retention
	retention.mode == "COMPLIANCE"
	retention.days >= 1
}

has_deny_on_delete(name) if {
	some rc in planned("aws_s3_bucket_policy")
	rc.change.after.bucket == name
	some statement in statements(json.unmarshal(rc.change.after.policy))
	statement.Effect == "Deny"
	public_principal(statement)
	"s3:DeleteObject" in as_list(statement.Action)
	"s3:DeleteObjectVersion" in as_list(statement.Action)
}

versioned(name) if {
	some rc in planned("aws_s3_bucket_versioning")
	rc.change.after.bucket == name
	some configuration in rc.change.after.versioning_configuration
	configuration.status == "Enabled"
}

protected(name) if {
	some rc in planned("aws_s3_bucket_public_access_block")
	rc.change.after.bucket == name
	rc.change.after.block_public_acls
	rc.change.after.ignore_public_acls
	rc.change.after.block_public_policy
	rc.change.after.restrict_public_buckets
}

encrypted_with_kms(name) if {
	some rc in planned("aws_s3_bucket_server_side_encryption_configuration")
	rc.change.after.bucket == name
	some rule in rc.change.after.rule
	some encryption in rule.apply_server_side_encryption_by_default
	encryption.sse_algorithm == "aws:kms"
}

deny contains msg if {
	some name in archive_buckets
	not locked_in_compliance_mode(name)
	msg := sprintf("bucket %s: Object Lock must be in compliance mode with a retention of at least one day", [name])
}

deny contains msg if {
	some name in archive_buckets
	not has_deny_on_delete(name)
	msg := sprintf("bucket %s: the policy must deny deleting objects and versions to every principal", [name])
}

deny contains msg if {
	some name in archive_buckets
	not versioned(name)
	msg := sprintf("bucket %s: versioning must be enabled (Object Lock needs it)", [name])
}

deny contains msg if {
	some name in archive_buckets
	not protected(name)
	msg := sprintf("bucket %s: Block Public Access must be fully on", [name])
}

deny contains msg if {
	some name in archive_buckets
	not encrypted_with_kms(name)
	msg := sprintf("bucket %s: the archive must be encrypted with a customer-managed key", [name])
}

# Only the workload account's trail may write: every Allow on the archive names the CloudTrail service and pins the trail.
deny contains msg if {
	some rc in planned("aws_s3_bucket_policy")
	rc.change.after.bucket in archive_buckets
	some statement in statements(json.unmarshal(rc.change.after.policy))
	statement.Effect == "Allow"
	not trail_only(statement)
	msg := sprintf("%s: statement %s allows something other than the one trail, pinned by aws:SourceArn", [rc.address, object.get(statement, "Sid", "(no Sid)")])
}

trail_only(statement) if {
	statement.Principal.Service == "cloudtrail.amazonaws.com"
	statement.Condition.StringEquals["aws:SourceArn"]
}

deny contains msg if {
	some rc in planned("aws_kms_key")
	not rc.change.after.enable_key_rotation
	msg := sprintf("%s: key rotation must be on", [rc.address])
}

# ---- The trail and the detections (workload environment) --------------------------------------------------------

deny contains msg if {
	some rc in planned("aws_cloudtrail")
	not rc.change.after.is_multi_region_trail
	msg := sprintf("%s: the trail must cover every Region", [rc.address])
}

deny contains msg if {
	some rc in planned("aws_cloudtrail")
	not rc.change.after.enable_log_file_validation
	msg := sprintf("%s: log file validation must be on", [rc.address])
}

deny contains msg if {
	some rc in planned("aws_cloudtrail")
	local := {bucket.change.after.bucket | some bucket in planned("aws_s3_bucket")}
	rc.change.after.s3_bucket_name in local
	msg := sprintf("%s: the logs must go to a bucket outside this account, not to %s", [rc.address, rc.change.after.s3_bucket_name])
}

deny contains msg if {
	some rc in planned("aws_cloudtrail")
	not rc.change.after.s3_bucket_name
	msg := sprintf("%s: the trail needs a log bucket", [rc.address])
}

deny contains msg if {
	some rc in planned("aws_cloudtrail")
	not known_or_set(rc, "kms_key_id")
	msg := sprintf("%s: the logs must be encrypted with a key held by the security account", [rc.address])
}

rule_has_target(rc) if {
	some target in planned("aws_cloudwatch_event_target")
	target.change.after.rule == rc.change.after.name
}

deny contains msg if {
	some rc in planned("aws_cloudwatch_event_rule")
	not rule_has_target(rc)
	msg := sprintf("%s: a rule with no target alerts nobody", [rc.address])
}

deny contains msg if {
	some rc in planned("aws_sns_topic")
	not known_or_set(rc, "kms_master_key_id")
	msg := sprintf("%s: the alert topic must be encrypted", [rc.address])
}

required_detections := {"d1", "d2", "d3", "d4"}

deny contains msg if {
	count(planned("aws_cloudwatch_event_rule")) > 0
	some id in required_detections
	not detection_deployed(id)
	msg := sprintf("detection %s is not deployed by any rule", [upper(id)])
}

detection_deployed(id) if {
	some rc in planned("aws_cloudwatch_event_rule")
	endswith(rc.change.after.name, sprintf("-%s", [id]))
}

deny contains msg if {
	some rc in planned("aws_cloudwatch_event_rule")
	endswith(rc.change.after.name, "-d4")
	rc.change.after.state != "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS"
	msg := sprintf("%s: D4 must also see read-only management events", [rc.address])
}

# ---- Credentials and the fenced-in weakness --------------------------------------------------------------------

deny contains msg if {
	some rc in planned("aws_iam_access_key")
	msg := sprintf("%s: an access key would sit in the state; scripts create the drill and honeytoken keys", [rc.address])
}

deny contains msg if {
	some rc in planned("aws_iam_role_policy_attachment")
	rc.change.after.policy_arn == "arn:aws:iam::aws:policy/AdministratorAccess"
	msg := sprintf("%s: AdministratorAccess is never attached by code", [rc.address])
}

deny contains msg if {
	some rc in planned("aws_iam_role_policy_attachment")
	rc.change.after.policy_arn == "arn:aws:iam::aws:policy/PowerUserAccess"
	not in_drill(rc)
	msg := sprintf("%s: PowerUserAccess is allowed only on the drill role", [rc.address])
}

deny contains msg if {
	some rc in planned("aws_s3_bucket_public_access_block")
	not in_drill(rc)
	some flag in ["block_public_acls", "ignore_public_acls", "block_public_policy", "restrict_public_buckets"]
	not rc.change.after[flag]
	msg := sprintf("%s: %s is off outside the drill module", [rc.address, flag])
}

deny contains msg if {
	some rc in planned("aws_iam_user")
	not in_drill(rc)
	msg := sprintf("%s: IAM users exist only inside the drill module", [rc.address])
}

deny contains msg if {
	some type in {"aws_iam_role", "aws_iam_user"}
	some rc in planned(type)
	in_drill(rc)
	not rc.change.after.tags.purpose
	msg := sprintf("%s: drill identities must carry the tag purpose so the teardown can find them", [rc.address])
}

deny contains msg if {
	some type, attribute in {"aws_s3_bucket_policy": "policy", "aws_iam_role": "assume_role_policy", "aws_sns_topic_policy": "policy"}
	some rc in planned(type)
	some statement in statements(json.unmarshal(rc.change.after[attribute]))
	statement.Effect == "Allow"
	public_principal(statement)
	msg := sprintf("%s: statement %s grants access to every principal", [rc.address, object.get(statement, "Sid", "(no Sid)")])
}

# ---- Posture ---------------------------------------------------------------------------------------------------

deny contains msg if {
	count(planned("aws_securityhub_standards_subscription")) > 0
	count(planned("aws_config_configuration_recorder_status")) == 0
	msg := "Security Hub controls need AWS Config recording; enable the recorder"
}

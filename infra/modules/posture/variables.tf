variable "name" {
  description = "Name prefix."
  type        = string
  default     = "detect"
}

variable "account_id" {
  description = "The account being assessed."
  type        = string
}

variable "region" {
  description = "Region of the standards subscription."
  type        = string
}

variable "retention_days" {
  description = "Days configuration snapshots are kept."
  type        = number
  default     = 30
}

variable "force_destroy" {
  description = "Delete the snapshot bucket with its objects on destroy. True only in a throwaway sandbox."
  type        = bool
  default     = false
}

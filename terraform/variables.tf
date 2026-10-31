variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile used for authentication (no credentials are stored in Terraform)."
  type        = string
  default     = "clinical-api-dev"
}

variable "project_name" {
  description = "Project name used in resource names and tags."
  type        = string
  default     = "clinical-document-api"
}

variable "environment" {
  description = "Environment name appended to resource names."
  type        = string
  default     = "dev-tf"
}

variable "log_retention_days" {
  description = "How long CloudWatch keeps log events."
  type        = number
  default     = 14
}

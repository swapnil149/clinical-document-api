locals {
  name = "${var.project_name}-${var.environment}"
}

# Separate development image repository (does not touch the existing ECR repo).
resource "aws_ecr_repository" "dev" {
  name                 = local.name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Separate development log group (does not touch the existing ECS log group).
resource "aws_cloudwatch_log_group" "dev" {
  name              = "/ecs/${local.name}"
  retention_in_days = var.log_retention_days
}

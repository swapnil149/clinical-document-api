output "ecr_repository_url" {
  description = "URL of the development ECR repository."
  value       = aws_ecr_repository.dev.repository_url
}

output "log_group_name" {
  description = "Name of the development CloudWatch log group."
  value       = aws_cloudwatch_log_group.dev.name
}

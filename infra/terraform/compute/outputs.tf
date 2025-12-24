output "ecr_backend_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecs_cluster_arn" {
  value = aws_ecs_cluster.this.arn
}

output "task_execution_role_arn" {
  value = aws_iam_role.task_execution.arn
}

output "task_role_arn" {
  value = aws_iam_role.task.arn
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.api.name
}

output "worker_log_group_name" {
  value = aws_cloudwatch_log_group.worker.name
}

output "worker_service_name" {
  value = aws_ecs_service.worker.name
}

output "worker_service_arn" {
  value = aws_ecs_service.worker.arn
}

output "worker_task_definition_arn" {
  value = aws_ecs_task_definition.worker.arn
}

output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnets" {
  value = module.network.public_subnets
}

output "private_subnets" {
  value = module.network.private_subnets
}

output "sg_alb_id" {
  value = module.network.sg_alb_id
}

output "sg_app_id" {
  value = module.network.sg_app_id
}

output "sg_rds_id" {
  value = module.network.sg_rds_id
}

output "ecr_backend_url" {
  value = module.compute.ecr_backend_url
}

output "ecs_cluster_arn" {
  value = module.compute.ecs_cluster_arn
}

output "task_execution_role_arn" {
  value = module.compute.task_execution_role_arn
}

output "task_role_arn" {
  value = module.compute.task_role_arn
}

output "log_group_name" {
  value = module.compute.log_group_name
}

output "db_endpoint" {
  value = module.db.db_endpoint
}

output "db_identifier" {
  value = module.db.db_identifier
}

output "db_sg_id" {
  value = module.db.db_sg_id
}

output "github_deploy_role_arn" {
  description = "IAM role ARN for GitHub Actions backend deploys"
  value       = aws_iam_role.cricksy_ai_github_deploy.arn
}

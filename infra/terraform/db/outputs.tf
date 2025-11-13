output "db_endpoint" {
  value = aws_db_instance.cricksy.endpoint
}

output "db_identifier" {
  value = aws_db_instance.cricksy.id
}

output "db_sg_id" {
  value = var.rds_sg_id
}

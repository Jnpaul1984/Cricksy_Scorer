terraform {
  required_version = ">= 1.6.0"
}

locals {
  common_tags = {
    project = "cricksy-ai"
    env     = "prod"
    tier    = "db"
  }
}

resource "aws_db_subnet_group" "this" {
  name       = "cricksy-ai-db-subnets"
  subnet_ids = var.private_subnets
  tags       = local.common_tags
}

resource "aws_db_parameter_group" "this" {
  name   = "cricksy-ai-pg14"
  family = "postgres14"
  tags   = local.common_tags
}

resource "aws_db_instance" "cricksy" {
  identifier              = "cricksy-ai-db"
  engine                  = "postgres"
  engine_version          = "14"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  storage_encrypted       = true
  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [var.rds_sg_id]
  username                = var.db_username
  password                = var.db_password
  publicly_accessible     = false
  backup_retention_period = 7
  deletion_protection     = false
  skip_final_snapshot     = true
  parameter_group_name    = aws_db_parameter_group.this.name

  tags = local.common_tags
}

locals {
  # Strip ":5432" from the RDS endpoint we got from the root module
  db_host       = split(":", var.db_endpoint)[0]
  database_name = length(trimspace(var.db_name)) > 0 ? trimspace(var.db_name) : "postgres"
  database_url  = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${local.db_host}:5432/${local.database_name}"
}

resource "aws_secretsmanager_secret" "db_url" {
  name        = "cricksy-ai/db-url"
  description = "Postgres SQLAlchemy URL for backend"
  tags = {
    project = "cricksy-ai"
    env     = "prod"
    tier    = "db"
  }
}

resource "aws_secretsmanager_secret_version" "db_url_v" {
  secret_id     = aws_secretsmanager_secret.db_url.id
  secret_string = local.database_url
}

resource "aws_secretsmanager_secret" "app_secret_key" {
  name        = "cricksy-ai/app-secret-key"
  description = "FastAPI secret key"
  tags = {
    project = "cricksy-ai"
    env     = "prod"
    tier    = "edge"
  }
}

resource "aws_secretsmanager_secret_version" "app_secret_key_v" {
  secret_id     = aws_secretsmanager_secret.app_secret_key.id
  secret_string = var.app_secret_key
}

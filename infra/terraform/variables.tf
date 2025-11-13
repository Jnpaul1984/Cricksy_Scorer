variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "image_tag" {
  type        = string
  description = "ECR image tag to deploy to ECS"
}
variable "db_username" {
  description = "Master username for the Postgres instance"
  type        = string
}

variable "db_password" {
  description = "Master password for the Postgres instance"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Database name used by the application"
  type        = string
  default     = "postgres"
}

variable "app_secret_key" {
  description = "Secret used by the backend for signing and encryption"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "backend_cors_origins" {
  description = "Comma-separated list of allowed origins for the backend API (e.g. \"https://YOUR_FIREBASE_SITE.web.app,https://api.cricksy-ai.com,http://localhost:5173\")"
  type        = string
  default     = "http://localhost:5173,https://app.cricksy-ai.com"
}

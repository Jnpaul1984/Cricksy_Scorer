# Compute module inputs.

variable "vpc_id" {
  type        = string
  description = "VPC ID for ALB and ECS networking"
}

variable "public_subnets" {
  type        = list(string)
  description = "Public subnets for ALB"
}

variable "private_subnets" {
  type        = list(string)
  description = "Private subnets for ECS tasks"
}

variable "sg_alb_id" {
  type        = string
  description = "Security group ID for ALB"
}

variable "sg_app_id" {
  type        = string
  description = "Security group ID for ECS app service"
}

variable "db_endpoint" {
  type        = string
  description = "RDS Postgres endpoint with port"
}

variable "db_username" {
  type        = string
  description = "DB master username"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "DB master password"
}

variable "db_name" {
  type        = string
  description = "Database name for the primary Postgres instance"
}

variable "app_secret_key" {
  type        = string
  sensitive   = true
  description = "Secret key used by the FastAPI backend"
}

variable "image_tag" {
  type        = string
  description = "Container image tag to deploy"
}

variable "backend_cors_origins" {
  type        = string
  description = "Comma-separated origins allowed to call the backend (e.g. \"https://YOUR_FIREBASE_SITE.web.app,https://api.cricksy-ai.com,http://localhost:5173\")"
  default     = "http://localhost:5173,https://app.cricksy-ai.com"
}

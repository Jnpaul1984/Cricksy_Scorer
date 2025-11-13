variable "vpc_id" {
  description = "Target VPC id"
  type        = string
}

variable "private_subnets" {
  description = "Private subnet ids for DB subnet group"
  type        = list(string)
}

variable "rds_sg_id" {
  description = "Security group allowing DB traffic"
  type        = string
}

variable "db_username" {
  description = "Database master username"
  type        = string
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

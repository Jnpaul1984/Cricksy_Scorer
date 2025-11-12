# Network Module

Creates the base networking layer for Cricksy:

- VPC `10.0.0.0/16` using the official `terraform-aws-modules/vpc/aws` module (v5) with two AZs, DNS enabled, and a single shared NAT gateway for cost control.
- Public subnets: `10.0.10.0/24`, `10.0.20.0/24` (tagged for ELB use).
- Private subnets: `10.0.110.0/24`, `10.0.120.0/24` (tagged for internal ELB/ECS use).
- Security groups:
  - `sg_alb` – allows HTTP/HTTPS from the internet for the Application Load Balancer.
  - `sg_app` – allows 80/8080 traffic only from `sg_alb` for ECS tasks or services.
  - `sg_rds` – allows Postgres (5432) only from `sg_app` for database access.

All resources inherit the standard `project=cricksy`, `env=prod`, `tier=network` tags.

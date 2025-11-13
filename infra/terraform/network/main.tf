terraform {
  required_version = ">= 1.6.0"
}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs_public   = slice(data.aws_availability_zones.available.names, 0, 2)
  azs_private  = local.azs_public
  public_cidrs = ["10.0.10.0/24", "10.0.20.0/24"]
  private_cidrs = [
    "10.0.110.0/24",
    "10.0.120.0/24"
  ]
  common_tags = {
    project = "cricksy-ai"
    env     = "prod"
    tier    = "network"
  }
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "cricksy-vpc"
  cidr = "10.0.0.0/16"

  azs             = local.azs_public
  public_subnets  = local.public_cidrs
  private_subnets = local.private_cidrs

  enable_dns_hostnames = true
  enable_dns_support   = true

  enable_nat_gateway     = true
  single_nat_gateway     = true
  one_nat_gateway_per_az = false


  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = local.common_tags
}

resource "aws_security_group" "sg_alb" {
  name        = "cricksy-sg-alb"
  description = "ALB ingress 80/443 from internet"
  vpc_id      = module.vpc.vpc_id
  tags        = local.common_tags
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.sg_alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.sg_alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "alb_all_egress" {
  security_group_id = aws_security_group.sg_alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "sg_app" {
  name        = "cricksy-sg-app"
  description = "App tasks: allow from ALB only"
  vpc_id      = module.vpc.vpc_id
  tags        = local.common_tags
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb_http" {
  security_group_id            = aws_security_group.sg_app.id
  referenced_security_group_id = aws_security_group.sg_alb.id
  from_port                    = 80
  to_port                      = 80
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb_8080" {
  security_group_id            = aws_security_group.sg_app.id
  referenced_security_group_id = aws_security_group.sg_alb.id
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "app_all_egress" {
  security_group_id = aws_security_group.sg_app.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "sg_rds" {
  name        = "cricksy-sg-rds"
  description = "RDS: allow from app only"
  vpc_id      = module.vpc.vpc_id
  tags        = local.common_tags
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_app_pg" {
  security_group_id            = aws_security_group.sg_rds.id
  referenced_security_group_id = aws_security_group.sg_app.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "rds_all_egress" {
  security_group_id = aws_security_group.sg_rds.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

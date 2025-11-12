output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnets" {
  value = module.vpc.public_subnets
}

output "private_subnets" {
  value = module.vpc.private_subnets
}

output "sg_alb_id" {
  value = aws_security_group.sg_alb.id
}

output "sg_app_id" {
  value = aws_security_group.sg_app.id
}

output "sg_rds_id" {
  value = aws_security_group.sg_rds.id
}

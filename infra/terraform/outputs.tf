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

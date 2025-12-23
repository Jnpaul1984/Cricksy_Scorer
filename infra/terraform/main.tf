locals {
  tags = {
    project = "cricksy"
    env     = "prod"
  }
}

module "network" {
  source = "./network"
}

module "compute" {
  source = "./compute"

  vpc_id                         = module.network.vpc_id
  public_subnets                 = module.network.public_subnets
  private_subnets                = module.network.private_subnets
  sg_alb_id                      = module.network.sg_alb_id
  sg_app_id                      = module.network.sg_app_id
  db_endpoint                    = module.db.db_endpoint
  db_username                    = var.db_username
  db_password                    = var.db_password
  db_name                        = var.db_name
  app_secret_key                 = var.app_secret_key
  image_tag                      = var.image_tag
  backend_cors_origins           = var.backend_cors_origins
  aws_region                     = var.aws_region
  s3_coach_videos_bucket         = var.s3_coach_videos_bucket
  s3_upload_url_expires_seconds  = var.s3_upload_url_expires_seconds
  sqs_video_analysis_queue_url   = var.sqs_video_analysis_queue_url
}

module "db" {
  source = "./db"

  vpc_id          = module.network.vpc_id
  private_subnets = module.network.private_subnets
  rds_sg_id       = module.network.sg_rds_id
  db_username     = var.db_username
  db_password     = var.db_password
}

module "sqs" {
  source = "./sqs"
}

# Future AWS resources will live here. Use `locals.tags` to keep tagging consistent.

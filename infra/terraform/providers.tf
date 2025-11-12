provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project = "cricksy-ai"
      env     = "prod"
    }
  }
}

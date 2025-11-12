locals {
  tags = {
    project = "cricksy"
    env     = "prod"
  }
}

module "network" {
  source = "./network"
}

# Future AWS resources will live here. Use `locals.tags` to keep tagging consistent.

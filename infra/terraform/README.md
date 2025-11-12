# Terraform Infrastructure

This directory contains the Terraform configuration scaffolding for Cricksy infrastructure.

## Layout

- `versions.tf` – Terraform & provider requirements plus a commented remote-state backend template.
- `providers.tf` – AWS provider configured for `us-east-1` by default, with project/env tags.
- `variables.tf` – Input definitions (`var.region`).
- `main.tf` – Placeholder for future resources and shared tag locals.
- `outputs.tf` – Reserved for future outputs.

## Usage

```bash
cd infra/terraform
terraform init        # uses local state unless the backend block is uncommented
terraform plan        # add resources first :)
```

To enable remote state, uncomment and populate the `backend "s3"` block in `versions.tf`.

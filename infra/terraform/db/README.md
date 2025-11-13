# Database Module

Provisions the PostgreSQL data layer for Cricksy AI:

- Subnet group across the shared private subnets.
- Parameter group targeting Postgres 14.
- Cost-conscious `db.t3.micro` instance (20 GB storage, encrypted, 7-day backups, no public access).

Credentials are provided via `db_username`/`db_password` module inputs (to be migrated to Secrets Manager later). All resources inherit `project=cricksy-ai`, `env=prod`, `tier=db` tags.

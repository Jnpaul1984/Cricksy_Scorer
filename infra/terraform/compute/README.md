# Compute Module

Provisioning pieces for the Cricksy AI compute layer:

- ECR repository `cricksy-backend` with image scanning enabled.
- CloudWatch log group `/cricksy-ai/api` retained for 30 days.
- ECS cluster `cricksy-ai-cluster` with Container Insights enabled.
- IAM task execution role (AWS managed execution policy + extra inline ECR/Logs perms) and task role placeholder.

All resources inherit the `project=cricksy-ai`, `env=prod`, `tier=compute` tags.

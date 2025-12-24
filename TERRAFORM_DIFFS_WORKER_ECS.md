# Terraform Code Diffs - Worker ECS Implementation

## Summary of Changes

**Files Modified:** 2
**Total Lines Added:** ~145
**New Resources:** 6 (IAM, CloudWatch, Task Definition, Service, Outputs)

---

## File 1: `infra/terraform/compute/main.tf`

### Diff Location 1: Task Role IAM Permissions (after line ~130)

```diff
  resource "aws_iam_role_policy" "exec_extra" {
    name   = "cricksy-ai-ecs-exec-extras"
    role   = aws_iam_role.task_execution.id
    policy = data.aws_iam_policy_document.exec_inline.json
  }

+ data "aws_caller_identity" "current" {}
+
+ data "aws_iam_policy_document" "task_s3_sqs" {
+   statement {
+     actions = [
+       "s3:GetObject",
+       "s3:PutObject",
+       "s3:DeleteObject"
+     ]
+     resources = [
+       "arn:aws:s3:::${var.s3_coach_videos_bucket}/*"
+     ]
+   }
+
+   statement {
+     actions = [
+       "s3:ListBucket"
+     ]
+     resources = [
+       "arn:aws:s3:::${var.s3_coach_videos_bucket}"
+     ]
+   }
+
+   statement {
+     actions = [
+       "sqs:ReceiveMessage",
+       "sqs:DeleteMessage",
+       "sqs:GetQueueAttributes"
+     ]
+     resources = [
+       "arn:aws:sqs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cricksy-video-analysis-prod"
+     ]
+   }
+ }
+
+ resource "aws_iam_role_policy" "task_s3_sqs" {
+   name   = "cricksy-ai-task-s3-sqs"
+   role   = aws_iam_role.task.id
+   policy = data.aws_iam_policy_document.task_s3_sqs.json
+ }
```

**Summary:**
- Added `data.aws_caller_identity` to get AWS account ID
- Added IAM policy document `task_s3_sqs` with S3 and SQS permissions
- Attached policy to task role `cricksy-ai-ecs-task`

---

### Diff Location 2: Worker CloudWatch Log Group (after line ~35)

```diff
  resource "aws_cloudwatch_log_group" "api" {
    name              = "/cricksy-ai/api"
    retention_in_days = 30
    tags              = local.common_tags
  }

+ resource "aws_cloudwatch_log_group" "worker" {
+   name              = "/cricksy-ai/worker"
+   retention_in_days = 30
+   tags              = local.common_tags
+ }
```

**Summary:**
- Created new CloudWatch log group for worker service
- Same retention as backend (30 days)

---

### Diff Location 3: Worker Task Definition & Service (at end of file, after `aws_ecs_service.backend`)

```diff
  resource "aws_ecs_service" "backend" {
    name            = "cricksy-ai-backend-service"
    cluster         = aws_ecs_cluster.this.id
    task_definition = aws_ecs_task_definition.backend.arn
    launch_type     = "FARGATE"
    desired_count   = 1
    propagate_tags  = "TASK_DEFINITION"

    network_configuration {
      subnets         = var.private_subnets
      security_groups = [var.sg_app_id]
      assign_public_ip = false
    }

    load_balancer {
      target_group_arn = aws_lb_target_group.api.arn
      container_name   = "backend"
      container_port   = 8000
    }

    deployment_circuit_breaker {
      enable   = true
      rollback = true
    }

    enable_execute_command = true
    platform_version       = "1.4.0"

    tags = local.common_tags

    depends_on = [
      aws_lb_listener.http
    ]
  }

+ # ========================================
+ # Worker ECS Task Definition & Service
+ # ========================================
+
+ resource "aws_ecs_task_definition" "worker" {
+   family                   = "cricksy-ai-worker"
+   cpu                      = "512"
+   memory                   = "1024"
+   network_mode             = "awsvpc"
+   requires_compatibilities = ["FARGATE"]
+   execution_role_arn       = aws_iam_role.task_execution.arn
+   task_role_arn            = aws_iam_role.task.arn
+
+   container_definitions = jsonencode([
+     {
+       name      = "worker"
+       image     = local.backend_image
+       essential = true
+       command   = ["python", "backend/scripts/run_video_analysis_worker.py"]
+       logConfiguration = {
+         logDriver = "awslogs"
+         options = {
+           awslogs-group         = aws_cloudwatch_log_group.worker.name
+           awslogs-region        = data.aws_region.current.id
+           awslogs-stream-prefix = "worker"
+         }
+       }
+       secrets = [
+         {
+           name      = "DATABASE_URL"
+           valueFrom = aws_secretsmanager_secret.db_url.arn
+         },
+         {
+           name      = "APP_SECRET_KEY"
+           valueFrom = aws_secretsmanager_secret.app_secret_key.arn
+         }
+       ]
+       environment = [
+         {
+           name  = "AWS_REGION"
+           value = var.aws_region
+         },
+         {
+           name  = "S3_COACH_VIDEOS_BUCKET"
+           value = var.s3_coach_videos_bucket
+         },
+         {
+           name  = "S3_UPLOAD_URL_EXPIRES_SECONDS"
+           value = tostring(var.s3_upload_url_expires_seconds)
+         },
+         {
+           name  = "SQS_VIDEO_ANALYSIS_QUEUE_URL"
+           value = var.sqs_video_analysis_queue_url
+         }
+       ]
+     }
+   ])
+
+   tags = local.common_tags
+ }
+
+ resource "aws_ecs_service" "worker" {
+   name            = "cricksy-ai-worker-service"
+   cluster         = aws_ecs_cluster.this.id
+   task_definition = aws_ecs_task_definition.worker.arn
+   launch_type     = "FARGATE"
+   desired_count   = 1
+   propagate_tags  = "TASK_DEFINITION"
+
+   network_configuration {
+     subnets         = var.private_subnets
+     security_groups = [var.sg_app_id]
+     assign_public_ip = false
+   }
+
+   deployment_circuit_breaker {
+     enable   = true
+     rollback = true
+   }
+
+   enable_execute_command = true
+   platform_version       = "1.4.0"
+
+   tags = local.common_tags
+ }
```

**Key Differences from Backend:**
| Feature | Backend | Worker |
|---------|---------|--------|
| Family | `cricksy-ai-backend` | `cricksy-ai-worker` |
| Command | (default entrypoint) | `python backend/scripts/run_video_analysis_worker.py` |
| Port Mappings | `8000:8000` | ❌ None |
| Load Balancer | ✅ ALB attached | ❌ None |
| Task Role | `cricksy-ai-ecs-task` (no S3/SQS) | `cricksy-ai-ecs-task` (+ S3/SQS perms) |

---

## File 2: `infra/terraform/compute/outputs.tf`

### Diff Location: Add Worker Outputs (at end of file)

```diff
  output "log_group_name" {
    value = aws_cloudwatch_log_group.api.name
  }

+ output "worker_log_group_name" {
+   value = aws_cloudwatch_log_group.worker.name
+ }
+
+ output "worker_service_name" {
+   value = aws_ecs_service.worker.name
+ }
+
+ output "worker_service_arn" {
+   value = aws_ecs_service.worker.arn
+ }
+
+ output "worker_task_definition_arn" {
+   value = aws_ecs_task_definition.worker.arn
+ }
```

**Outputs Exported:**
- `worker_log_group_name` → `/cricksy-ai/worker`
- `worker_service_name` → `cricksy-ai-worker-service`
- `worker_service_arn` → `arn:aws:ecs:us-east-2:ACCOUNT:service/cricksy-ai-cluster/cricksy-ai-worker-service`
- `worker_task_definition_arn` → `arn:aws:ecs:us-east-2:ACCOUNT:task-definition/cricksy-ai-worker:1`

---

## No Changes to Other Files

✅ `infra/terraform/compute/alb.tf` — **UNCHANGED**
✅ `infra/terraform/compute/secrets.tf` — **UNCHANGED**
✅ `infra/terraform/compute/variables.tf` — **UNCHANGED** (all variables already exist)
✅ `backend/routes/coach_pro_plus.py` — **UNCHANGED**
✅ `backend/scripts/run_video_analysis_worker.py` — **UNCHANGED**

---

## Pre-Apply Checklist

Before running `terraform apply`, verify:

- [ ] All Terraform variables in `tfvars` are set (especially `sqs_video_analysis_queue_url`)
- [ ] Backend ECS service is running and healthy
- [ ] Worker script exists at `backend/scripts/run_video_analysis_worker.py`
- [ ] Docker image is built and pushed to ECR with updated code
- [ ] SQS queue is created and accessible from your AWS account
- [ ] S3 bucket `cricksy-coach-videos` exists and is accessible
- [ ] PostgreSQL database is running and `DATABASE_URL` secret is set

---

## Apply & Verify

### Step 1: Plan
```bash
cd infra/terraform
terraform plan -out=worker.tfplan
```

Expected output:
```
Terraform will perform the following actions:

  # aws_cloudwatch_log_group.worker will be created
  + resource "aws_cloudwatch_log_group" "worker" {
      + arn               = (known after apply)
      + id                = "/cricksy-ai/worker"
      + name              = "/cricksy-ai/worker"
      + retention_in_days = 30
      + tags              = {
          + "env"    = "prod"
          + "project" = "cricksy-ai"
          + "tier"   = "compute"
        }
    }

  # aws_ecs_service.worker will be created
  + resource "aws_ecs_service" "worker" {
      + arn                    = (known after apply)
      + cluster                = "arn:aws:ecs:us-east-2:ACCOUNT:cluster/cricksy-ai-cluster"
      + deployment_circuit_breaker = {
          + enable   = true
          + rollback = true
        }
      + desired_count          = 1
      + enable_execute_command = true
      + id                     = (known after apply)
      + launch_type            = "FARGATE"
      + name                   = "cricksy-ai-worker-service"
      + platform_version       = "1.4.0"
      ...
    }

  # aws_ecs_task_definition.worker will be created
  + resource "aws_ecs_task_definition" "worker" {
      + arn                   = (known after apply)
      + family                = "cricksy-ai-worker"
      + cpu                   = "512"
      + memory                = "1024"
      + network_mode          = "awsvpc"
      + execution_role_arn    = "arn:aws:iam::ACCOUNT:role/cricksy-ai-ecs-task-exec"
      + task_role_arn         = "arn:aws:iam::ACCOUNT:role/cricksy-ai-ecs-task"
      + requires_compatibilities = [
          + "FARGATE",
        ]
      ...
    }

  # aws_iam_role_policy.task_s3_sqs will be created
  + resource "aws_iam_role_policy" "task_s3_sqs" {
      + id     = (known after apply)
      + name   = "cricksy-ai-task-s3-sqs"
      + policy = jsonencode(
          {
            + Statement = [
                + {
                    + Action   = [
                        + "s3:DeleteObject",
                        + "s3:GetObject",
                        + "s3:PutObject",
                      ]
                    + Effect   = "Allow"
                    + Resource = [
                        + "arn:aws:s3:::cricksy-coach-videos/*",
                      ]
                  },
                + {
                    + Action   = [
                        + "s3:ListBucket",
                      ]
                    + Effect   = "Allow"
                    + Resource = [
                        + "arn:aws:s3:::cricksy-coach-videos",
                      ]
                  },
                + {
                    + Action   = [
                        + "sqs:DeleteMessage",
                        + "sqs:GetQueueAttributes",
                        + "sqs:ReceiveMessage",
                      ]
                    + Effect   = "Allow"
                    + Resource = [
                        + "arn:aws:sqs:us-east-2:ACCOUNT:cricksy-video-analysis-prod",
                      ]
                  },
              ]
            + Version  = "2012-10-17"
          }
        )
      + role   = "cricksy-ai-ecs-task"
    }

Plan: 6 to add, 0 to change, 0 to destroy.
```

### Step 2: Apply
```bash
terraform apply worker.tfplan
```

Expected output:
```
Apply complete! Resources: 6 added, 0 changed, 0 destroyed.

Outputs:

ecs_cluster_arn = "arn:aws:ecs:us-east-2:ACCOUNT:cluster/cricksy-ai-cluster"
ecr_backend_url = "ACCOUNT.dkr.ecr.us-east-2.amazonaws.com/cricksy-backend"
log_group_name = "/cricksy-ai/api"
task_execution_role_arn = "arn:aws:iam::ACCOUNT:role/cricksy-ai-ecs-task-exec"
task_role_arn = "arn:aws:iam::ACCOUNT:role/cricksy-ai-ecs-task"
worker_log_group_name = "/cricksy-ai/worker"
worker_service_arn = "arn:aws:ecs:us-east-2:ACCOUNT:service/cricksy-ai-cluster/cricksy-ai-worker-service"
worker_service_name = "cricksy-ai-worker-service"
worker_task_definition_arn = "arn:aws:ecs:us-east-2:ACCOUNT:task-definition/cricksy-ai-worker:1"
```

### Step 3: Monitor
```bash
# Watch ECS service
aws ecs describe-services \
  --cluster cricksy-ai-cluster \
  --services cricksy-ai-worker-service \
  --region us-east-2 | jq '.services[0] | {name, status, runningCount, desiredCount}'

# Watch logs
aws logs tail /cricksy-ai/worker --follow --region us-east-2
```

---

## Rollback (if needed)

If issues arise:
```bash
terraform destroy -target aws_ecs_service.worker -target aws_ecs_task_definition.worker
```

This deletes worker service/task without touching backend.

---

## Notes

- **Backend unaffected:** No changes to backend task or service
- **Reuses image:** Same Docker image as backend (just different command)
- **Reuses role:** Same task role, but now with S3/SQS permissions
- **No code changes:** Only Terraform infrastructure code
- **Database migration:** Not needed (using existing schemas)

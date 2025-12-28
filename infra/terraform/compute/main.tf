terraform {
  required_version = ">= 1.6.0"
}

locals {
  common_tags = {
    project = "cricksy-ai"
    env     = "prod"
    tier    = "compute"
  }

  backend_image = "${aws_ecr_repository.backend.repository_url}:${var.image_tag}"
}

data "aws_region" "current" {}

resource "aws_ecr_repository" "backend" {
  name                 = "cricksy-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/cricksy-ai/api"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/cricksy-ai/worker"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_ecs_cluster" "this" {
  name = "cricksy-ai-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.common_tags
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = "cricksy-ai-ecs-task-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
  tags               = local.common_tags
}

resource "aws_iam_policy" "task_execution_secrets" {
  name        = "cricksy-ai-task-execution-secrets"
  description = "Allow ECS task execution role to read Secrets Manager values for backend"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.db_url.arn,
          aws_secretsmanager_secret.app_secret_key.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role" "task" {
  name               = "cricksy-ai-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "exec_managed" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy_attachment" "task_execution_secrets" {
  role       = aws_iam_role.task_execution.name
  policy_arn = aws_iam_policy.task_execution_secrets.arn
}

data "aws_iam_policy_document" "exec_inline" {
  statement {
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }

  statement {
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      aws_secretsmanager_secret.db_url.arn,
      aws_secretsmanager_secret.app_secret_key.arn
    ]
  }
}

resource "aws_iam_role_policy" "exec_extra" {
  name   = "cricksy-ai-ecs-exec-extras"
  role   = aws_iam_role.task_execution.id
  policy = data.aws_iam_policy_document.exec_inline.json
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "task_s3_sqs" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = [
      "arn:aws:s3:::${var.s3_coach_videos_bucket}/*"
    ]
  }

  statement {
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.s3_coach_videos_bucket}"
    ]
  }

  statement {
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes"
    ]
    resources = [
      "arn:aws:sqs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cricksy-video-analysis-prod"
    ]
  }
}

resource "aws_iam_role_policy" "task_s3_sqs" {
  name   = "cricksy-ai-task-s3-sqs"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.task_s3_sqs.json
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "cricksy-ai-backend"
  cpu                      = "512"
  memory                   = "1024"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = local.backend_image
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api.name
          awslogs-region        = data.aws_region.current.id
          awslogs-stream-prefix = "backend"
        }
      }
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = aws_secretsmanager_secret.db_url.arn
        },
        {
          name      = "APP_SECRET_KEY"
          valueFrom = aws_secretsmanager_secret.app_secret_key.arn
        }
      ]
      environment = [
        {
          name  = "RUN_MIGRATIONS"
          value = "true"
        },
        {
          name  = "BACKEND_CORS_ORIGINS"
          value = var.backend_cors_origins
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "S3_COACH_VIDEOS_BUCKET"
          value = var.s3_coach_videos_bucket
        },
        {
          name  = "S3_UPLOAD_URL_EXPIRES_SECONDS"
          value = tostring(var.s3_upload_url_expires_seconds)
        },
        {
          name  = "SQS_VIDEO_ANALYSIS_QUEUE_URL"
          value = var.sqs_video_analysis_queue_url
        }
      ]
    }
  ])

  tags = local.common_tags
}

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

# ========================================
# Worker ECS Task Definition & Service
# ========================================

resource "aws_ecs_task_definition" "worker" {
  family                   = "cricksy-ai-worker"
  cpu                      = "512"
  memory                   = "1024"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = local.backend_image
      essential = true
      command   = ["python", "-m", "backend.workers.analysis_worker"]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.worker.name
          awslogs-region        = data.aws_region.current.id
          awslogs-stream-prefix = "worker"
        }
      }
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = aws_secretsmanager_secret.db_url.arn
        },
        {
          name      = "APP_SECRET_KEY"
          valueFrom = aws_secretsmanager_secret.app_secret_key.arn
        }
      ]
      environment = [
        {
          name  = "RUN_MIGRATIONS"
          value = "false"
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "S3_COACH_VIDEOS_BUCKET"
          value = var.s3_coach_videos_bucket
        },
        {
          name  = "S3_UPLOAD_URL_EXPIRES_SECONDS"
          value = tostring(var.s3_upload_url_expires_seconds)
        },
        {
          name  = "SQS_VIDEO_ANALYSIS_QUEUE_URL"
          value = var.sqs_video_analysis_queue_url
        }
      ]
    }
  ])

  tags = local.common_tags
}

resource "aws_ecs_service" "worker" {
  name            = "cricksy-ai-worker-service"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.worker.arn
  launch_type     = "FARGATE"
  desired_count   = 1
  propagate_tags  = "TASK_DEFINITION"

  network_configuration {
    subnets         = var.private_subnets
    security_groups = [var.sg_app_id]
    assign_public_ip = false
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  enable_execute_command = true
  platform_version       = "1.4.0"

  tags = local.common_tags
}

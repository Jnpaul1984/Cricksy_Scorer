data "aws_partition" "current" {}

data "aws_caller_identity" "current" {}

locals {
  github_oidc_url     = "https://token.actions.githubusercontent.com"
  github_client_id    = "sts.amazonaws.com"
  github_repo_subject = "repo:YOUR_GITHUB_ORG/YOUR_REPO:ref:refs/heads/main" # TODO: replace with your org/repo
  task_definition_arn_pattern = format(
    "arn:%s:ecs:%s:%s:task-definition/cricksy-ai-backend*",
    data.aws_partition.current.partition,
    var.region,
    data.aws_caller_identity.current.account_id,
  )
}

data "aws_iam_openid_connect_provider" "github" {
  # ARN for the existing GitHub Actions OIDC provider in this account.
  # Pattern: arn:aws:iam::<account_id>:oidc-provider/token.actions.githubusercontent.com
  arn = "arn:aws:iam::365183982031:oidc-provider/token.actions.githubusercontent.com"
}


data "aws_iam_policy_document" "github_oidc_trust" {
  statement {
    effect = "Allow"

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    actions = ["sts:AssumeRoleWithWebIdentity"]

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = [local.github_client_id]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [local.github_repo_subject]
    }
  }
}

resource "aws_iam_role" "cricksy_ai_github_deploy" {
  name               = "cricksy-ai-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_oidc_trust.json

  tags = {
    project = "cricksy-ai"
    env     = "prod"
    tier    = "ci"
  }
}

data "aws_ecr_repository" "backend" {
  name = "cricksy-backend"
}

data "aws_ecs_cluster" "backend" {
  cluster_name = "cricksy-ai-cluster"
}

data "aws_ecs_service" "backend" {
  cluster_arn  = data.aws_ecs_cluster.backend.arn
  service_name = "cricksy-ai-backend-service"
}

data "aws_ecs_task_definition" "backend" {
  task_definition = "cricksy-ai-backend"
}

data "aws_cloudwatch_log_group" "api" {
  name = "/cricksy-ai/api"
}

data "aws_iam_policy_document" "github_deploy" {
  statement {
    sid    = "ECRRepositoryAccess"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:DescribeRepositories",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:ListImages",
      "ecr:PutImage",
      "ecr:UploadLayerPart"
    ]
    resources = [data.aws_ecr_repository.backend.arn]
  }

  statement {
    sid    = "ECRAuthToken"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ECSServiceControl"
    effect = "Allow"
    actions = [
      "ecs:DescribeServices",
      "ecs:DescribeTasks",
      "ecs:DescribeTaskDefinition",
      "ecs:UpdateService",
      "ecs:RegisterTaskDefinition"
    ]
    resources = [
      data.aws_ecs_cluster.backend.arn,
      data.aws_ecs_service.backend.arn,
      data.aws_ecs_task_definition.backend.arn,
      local.task_definition_arn_pattern
    ]
  }

  statement {
    sid    = "CloudWatchLogsRead"
    effect = "Allow"
    actions = [
      "logs:DescribeLogStreams",
      "logs:FilterLogEvents"
    ]
    resources = [data.aws_cloudwatch_log_group.api.arn]
  }
}

resource "aws_iam_role_policy" "cricksy_ai_github_deploy" {
  name   = "cricksy-ai-github-deploy-policy"
  role   = aws_iam_role.cricksy_ai_github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy.json
}

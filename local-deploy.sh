#!/usr/bin/env bash
set -euo pipefail
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REGISTRY="${ECR_REGISTRY:-365183982031.dkr.ecr.${AWS_REGION}.amazonaws.com}"
ECR_REPOSITORY="${ECR_REPOSITORY:-cricksy-backend}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
TASK_FAMILY="${TASK_FAMILY:-cricksy-ai-backend}"
CONTAINER_NAME="${CONTAINER_NAME:-backend}"
ECS_CLUSTER="${ECS_CLUSTER:-cricksy-ai-cluster}"
ECS_SERVICE="${ECS_SERVICE:-cricksy-ai-backend-service}"
CREATE_WORKFLOW="${CREATE_WORKFLOW:-no}"

command -v aws >/dev/null || { echo "aws CLI not found"; exit 1; }
command -v docker >/dev/null || { echo "docker not found"; exit 1; }
command -v jq >/dev/null || { echo "jq not found"; exit 1; }

echo "AWS region: $AWS_REGION"
echo "ECR registry: $ECR_REGISTRY"
echo "ECR repository: $ECR_REPOSITORY"
echo "Image tag: $IMAGE_TAG"
echo "Task family: $TASK_FAMILY"
echo "Container name: $CONTAINER_NAME"
echo "ECS cluster: $ECS_CLUSTER"
echo "ECS service: $ECS_SERVICE"

echo "Validating AWS credentials..."
aws sts get-caller-identity --region "$AWS_REGION" >/dev/null

echo "Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

if ! aws ecr describe-repositories --repository-names "$ECR_REPOSITORY" --region "$AWS_REGION" >/dev/null 2>&1; then
  echo "Creating ECR repository $ECR_REPOSITORY..."
  aws ecr create-repository --repository-name "$ECR_REPOSITORY" --region "$AWS_REGION"
fi

FULL_IMAGE="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
echo "Building ${FULL_IMAGE}..."
docker build -t "${ECR_REPOSITORY}:${IMAGE_TAG}" .
docker tag "${ECR_REPOSITORY}:${IMAGE_TAG}" "${FULL_IMAGE}"
docker push "${FULL_IMAGE}"

echo "Fetching current task definition..."
aws ecs describe-task-definition --task-definition "${TASK_FAMILY}" --region "$AWS_REGION" > taskdef.json

echo "Updating container image..."
jq --arg image "$FULL_IMAGE" --arg container "$CONTAINER_NAME" --arg py "/app" '
  .taskDefinition
  | {
      family: .family,
      networkMode: .networkMode,
      containerDefinitions:
        (.containerDefinitions
         | map(
             if .name == $container then .image = $image else . end
           )
         | map(
             .environment =
               ( ( .environment // [] )
                 | map(select(.name != "PYTHONPATH"))
                 + [{ name: "PYTHONPATH", value: $py }]
               )
           )
        ),
      volumes: .volumes,
      taskRoleArn: .taskRoleArn,
      executionRoleArn: .executionRoleArn,
      requiresCompatibilities: .requiresCompatibilities,
      cpu: .cpu,
      memory: .memory
    }' taskdef.json > new-taskdef.json


echo "Registering new task definition..."
aws ecs register-task-definition --cli-input-json file://new-taskdef.json --region "$AWS_REGION" > registered-taskdef.json
NEW_TASK_DEF_ARN=$(jq -r '.taskDefinition.taskDefinitionArn' registered-taskdef.json)
echo "New task definition ARN: $NEW_TASK_DEF_ARN"

echo "Updating ECS service..."
aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --task-definition "$NEW_TASK_DEF_ARN" \
  --force-new-deployment \
  --region "$AWS_REGION"

echo "Waiting for service to stabilize..."
if aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" --region "$AWS_REGION"; then
  echo "Service stabilized."
else
  echo "Service did not stabilize; showing events:"
  aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" --region "$AWS_REGION" --query "services[0].events" --output text
fi

if [[ "$CREATE_WORKFLOW" == "yes" ]]; then
  echo "Writing workflow file..."
  mkdir -p .github/workflows
  cat > .github/workflows/deploy-backend.yml <<'EOF'
name: Deploy Backend
on:
  push:
    branches: [ main ]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: 365183982031.dkr.ecr.us-east-1.amazonaws.com
  ECR_REPOSITORY: cricksy-backend

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    outputs:
      task_def_arn: ${{ steps.register-task-def.outputs.task_def_arn }}
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      - name: Login to Amazon ECR
        run: aws ecr get-login-password --region ${{ env.AWS_REGION }} | docker login --username AWS --password-stdin ${{ env.ECR_REGISTRY }}
      - name: Build and push image
        run: |
          IMAGE_TAG=${{ github.sha }}
          docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
          docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
          docker push ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}
      - name: Register new task definition
        id: register-task-def
        run: |
          TASK_FAMILY=cricksy-ai-backend
          CONTAINER_NAME=backend
          IMAGE=${ECR_REGISTRY}/${ECR_REPOSITORY}:${{ github.sha }}
          aws ecs describe-task-definition --task-definition "${TASK_FAMILY}" --region "${{ env.AWS_REGION }}" > taskdef.json
          jq --arg image "$IMAGE" --arg container "$CONTAINER_NAME" '.taskDefinition | { family: .family, networkMode: .networkMode, containerDefinitions: (.containerDefinitions | map(if .name == $container then .image = $image else . end)), volumes: .volumes, taskRoleArn: .taskRoleArn, executionRoleArn: .executionRoleArn, requiresCompatibilities: .requiresCompatibilities, cpu: .cpu, memory: .memory }' taskdef.json > new-taskdef.json
          aws ecs register-task-definition --cli-input-json file://new-taskdef.json --region "${{ env.AWS_REGION }}" > registered.json
          echo "task_def_arn=$(jq -r '.taskDefinition.taskDefinitionArn' registered.json)" >> $GITHUB_OUTPUT

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      - name: Update ECS service
        env:
          ECS_CLUSTER: cricksy-ai-backend-cluster
          ECS_SERVICE: cricksy-ai-backend-service
        run: |
          TASK_DEF_ARN="${{ needs.build-and-push.outputs.task_def_arn }}"
          aws ecs update-service --cluster "${ECS_CLUSTER}" --service "${ECS_SERVICE}" --task-definition "${TASK_DEF_ARN}" --force-new-deployment --region "${{ env.AWS_REGION }}"
          aws ecs wait services-stable --cluster "${ECS_CLUSTER}" --services "${ECS_SERVICE}" --region "${{ env.AWS_REGION }}"
EOF
  git checkout -b fix/ecr-build-push || git checkout fix/ecr-build-push
  git add .github/workflows/deploy-backend.yml
  git commit -m "ci: add build/push to ECR and taskdef registration workflow (edit placeholders before use)"
  echo "Workflow committed on branch fix/ecr-build-push. Push it when ready."
fi

echo "Done."

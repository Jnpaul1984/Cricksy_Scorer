#!/bin/bash
# AWS Setup Script for ML Model Retraining Infrastructure
# =========================================================
# This script sets up S3 bucket, IAM permissions, ECS task definition,
# and EventBridge scheduled retraining for Cricksy ML models.

set -e

echo "========================================"
echo "Cricksy ML Retraining Infrastructure Setup"
echo "========================================"
echo ""

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="365183982031"
S3_BUCKET="cricksy-ml-models"
ECS_CLUSTER="cricksy-ai-cluster"
TASK_ROLE="cricksy-ecs-task-role"
EXECUTION_ROLE="cricksy-ecs-execution-role"
LOG_GROUP="/cricksy-ai/ml-training"

echo "Configuration:"
echo "  AWS Region: $AWS_REGION"
echo "  S3 Bucket: $S3_BUCKET"
echo "  ECS Cluster: $ECS_CLUSTER"
echo ""

# Step 1: Create S3 bucket
echo "[1/7] Creating S3 bucket for models..."
if aws s3 mb s3://$S3_BUCKET --region $AWS_REGION 2>/dev/null; then
    echo "  βœ" Bucket created: s3://$S3_BUCKET"
else
    echo "  βœ" Bucket already exists"
fi

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket $S3_BUCKET \
  --versioning-configuration Status=Enabled \
  --region $AWS_REGION
echo "  βœ" Versioning enabled"
echo ""

# Step 2: Add S3 permissions to ECS task role
echo "[2/7] Adding S3 permissions to ECS task role..."
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/CricksyModelS3Access"

# Create IAM policy (if not exists)
if aws iam create-policy \
  --policy-name CricksyModelS3Access \
  --policy-document file://.aws/iam-s3-model-access-policy.json \
  --region $AWS_REGION 2>/dev/null; then
    echo "  βœ" IAM policy created"
else
    echo "  βœ" IAM policy already exists"
fi

# Attach policy to task role
aws iam attach-role-policy \
  --role-name $TASK_ROLE \
  --policy-arn $POLICY_ARN \
  --region $AWS_REGION 2>/dev/null || echo "  βœ" Policy already attached"
echo ""

# Step 3: Create CloudWatch log group
echo "[3/7] Creating CloudWatch log group..."
aws logs create-log-group \
  --log-group-name $LOG_GROUP \
  --region $AWS_REGION 2>/dev/null || echo "  βœ" Log group already exists"

aws logs put-retention-policy \
  --log-group-name $LOG_GROUP \
  --retention-in-days 30 \
  --region $AWS_REGION
echo "  βœ" Log retention set to 30 days"
echo ""

# Step 4: Register ECS task definition
echo "[4/7] Registering ECS task definition..."
TASK_DEF_ARN=$(aws ecs register-task-definition \
  --cli-input-json file://.aws/ecs-ml-training-task-definition.json \
  --region $AWS_REGION \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)
echo "  βœ" Task definition registered: $TASK_DEF_ARN"
echo ""

# Step 5: Get network configuration from existing backend service
echo "[5/7] Fetching network configuration from backend service..."
NETWORK_CONFIG=$(aws ecs describe-services \
  --cluster $ECS_CLUSTER \
  --services cricksy-ai-backend-service \
  --region $AWS_REGION \
  --query 'services[0].networkConfiguration.awsvpcConfiguration' \
  --output json)

SUBNETS=$(echo $NETWORK_CONFIG | jq -r '.subnets | join(",")')
SECURITY_GROUPS=$(echo $NETWORK_CONFIG | jq -r '.securityGroups | join(",")')

echo "  βœ" Subnets: $SUBNETS"
echo "  βœ" Security Groups: $SECURITY_GROUPS"
echo ""

# Step 6: Create EventBridge IAM role (if not exists)
echo "[6/7] Setting up EventBridge IAM role..."
EVENTBRIDGE_ROLE="cricksy-eventbridge-ecs-role"
EVENTBRIDGE_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${EVENTBRIDGE_ROLE}"

# Create trust policy
cat > /tmp/eventbridge-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "events.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create role
aws iam create-role \
  --role-name $EVENTBRIDGE_ROLE \
  --assume-role-policy-document file:///tmp/eventbridge-trust-policy.json \
  --region $AWS_REGION 2>/dev/null || echo "  βœ" Role already exists"

# Attach ECS task execution policy
aws iam attach-role-policy \
  --role-name $EVENTBRIDGE_ROLE \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
  --region $AWS_REGION 2>/dev/null || true

# Create custom policy for ECS task running
cat > /tmp/eventbridge-ecs-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ecs:RunTask",
      "iam:PassRole"
    ],
    "Resource": "*"
  }]
}
EOF

aws iam put-role-policy \
  --role-name $EVENTBRIDGE_ROLE \
  --policy-name EventBridgeECSAccess \
  --policy-document file:///tmp/eventbridge-ecs-policy.json \
  --region $AWS_REGION
echo "  βœ" EventBridge role configured"
echo ""

# Step 7: Create EventBridge schedule
echo "[7/7] Creating EventBridge schedule for weekly retraining..."
RULE_NAME="cricksy-weekly-model-retrain"

# Create rule (every Sunday at 2 AM UTC)
aws events put-rule \
  --name $RULE_NAME \
  --schedule-expression "cron(0 2 ? * SUN *)" \
  --state ENABLED \
  --description "Retrain Cricksy ML models weekly with new match data" \
  --region $AWS_REGION
echo "  βœ" EventBridge rule created (Sundays at 2 AM UTC)"

# Add ECS task as target
aws events put-targets \
  --rule $RULE_NAME \
  --targets "[
    {
      \"Id\": \"1\",
      \"Arn\": \"arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:cluster/${ECS_CLUSTER}\",
      \"RoleArn\": \"${EVENTBRIDGE_ROLE_ARN}\",
      \"EcsParameters\": {
        \"TaskDefinitionArn\": \"${TASK_DEF_ARN}\",
        \"TaskCount\": 1,
        \"LaunchType\": \"FARGATE\",
        \"NetworkConfiguration\": {
          \"awsvpcConfiguration\": {
            \"Subnets\": $(echo $SUBNETS | jq -R 'split(",")'),
            \"SecurityGroups\": $(echo $SECURITY_GROUPS | jq -R 'split(",")'),
            \"AssignPublicIp\": \"ENABLED\"
          }
        },
        \"PlatformVersion\": \"LATEST\"
      }
    }
  ]" \
  --region $AWS_REGION
echo "  βœ" ECS task added as target"
echo ""

echo "========================================"
echo "Setup Complete! βœ…"
echo "========================================"
echo ""
echo "Summary:"
echo "  β€' S3 bucket: s3://$S3_BUCKET (versioning enabled)"
echo "  β€' IAM permissions: Task role has S3 access"
echo "  β€' ECS task: $TASK_DEF_ARN"
echo "  β€' Schedule: Weekly on Sundays at 2 AM UTC"
echo "  β€' Logs: CloudWatch $LOG_GROUP"
echo ""
echo "Next Steps:"
echo "  1. Update DATABASE_URL in task definition with real RDS password"
echo "  2. Test manual run:"
echo "     aws ecs run-task \\"
echo "       --cluster $ECS_CLUSTER \\"
echo "       --task-definition cricksy-ml-training \\"
echo "       --launch-type FARGATE \\"
echo "       --network-configuration \"awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUPS],assignPublicIp=ENABLED}\""
echo "  3. Monitor logs:"
echo "     aws logs tail $LOG_GROUP --follow"
echo "  4. Verify S3 uploads:"
echo "     aws s3 ls s3://$S3_BUCKET/models/ --recursive"
echo ""

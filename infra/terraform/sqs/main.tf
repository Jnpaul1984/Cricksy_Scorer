terraform {
  required_version = ">= 1.6.0"
}

locals {
  common_tags = {
    project = "cricksy-ai"
    env     = "prod"
    tier    = "messaging"
  }
}

# Dead Letter Queue (DLQ) for failed video analysis jobs
resource "aws_sqs_queue" "video_analysis_dlq" {
  name                      = "cricksy-video-analysis-dlq-prod"
  message_retention_seconds = 1209600  # 14 days
  
  tags = merge(
    local.common_tags,
    {
      Name = "cricksy-video-analysis-dlq-prod"
      Type = "DLQ"
    }
  )
}

# Main queue for video analysis jobs
resource "aws_sqs_queue" "video_analysis" {
  name                       = "cricksy-video-analysis-prod"
  message_retention_seconds  = 86400   # 1 day
  visibility_timeout_seconds = 3600    # 1 hour (video analysis timeout)
  
  # Configure redrive policy to send failed messages to DLQ
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.video_analysis_dlq.arn
    maxReceiveCount     = 3  # Retry up to 3 times before sending to DLQ
  })
  
  tags = merge(
    local.common_tags,
    {
      Name = "cricksy-video-analysis-prod"
      Type = "MainQueue"
    }
  )
}

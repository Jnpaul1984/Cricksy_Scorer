# SQS Module - Video Analysis Queue

This module provisions AWS SQS queues for the Cricksy AI video analysis system.

## Resources

### Main Queue: `cricksy-video-analysis-prod`
- **Purpose**: Receives video analysis jobs from the backend API
- **Visibility Timeout**: 1 hour (60 minutes for processing)
- **Message Retention**: 1 day (86,400 seconds)
- **Max Receive Count**: 3 (before sending to DLQ)

### Dead Letter Queue (DLQ): `cricksy-video-analysis-dlq-prod`
- **Purpose**: Captures failed video analysis jobs after 3 failed attempts
- **Message Retention**: 14 days (for debugging failed jobs)
- **Used for**: Monitoring and alerting on failed video processing

## Architecture

```
Producer (Backend API)
    ↓
[cricksy-video-analysis-prod] (Main Queue)
    ↓
Consumer Worker (ECS Task/Lambda)
    ↓
Success: Job Complete
Failure (3x): → [cricksy-video-analysis-dlq-prod] (DLQ)
```

## Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Visibility Timeout** | 3600 sec (1 hr) | Video analysis with 4K frames can take time |
| **Message Retention** | 86400 sec (1 day) | Short-lived jobs, processed immediately |
| **DLQ Retention** | 1209600 sec (14 days) | Longer retention for post-mortem analysis |
| **Max Receive Count** | 3 | Balanced retry strategy |

## Outputs

The module exports:
- `video_analysis_queue_url` - Main queue URL for sending/receiving messages
- `video_analysis_queue_arn` - Main queue ARN for IAM policies
- `video_analysis_dlq_url` - DLQ URL for monitoring
- `video_analysis_dlq_arn` - DLQ ARN for alarms

## Integration

### Backend Application
1. Producer sends video analysis jobs to the main queue
2. Workers consume messages and process video
3. Failed jobs automatically move to DLQ after retries

### IAM Permissions
Add to ECS task role to enable queue access:

```json
{
  "Effect": "Allow",
  "Action": [
    "sqs:SendMessage",
    "sqs:ReceiveMessage",
    "sqs:DeleteMessage",
    "sqs:GetQueueAttributes",
    "sqs:ChangeMessageVisibility"
  ],
  "Resource": [
    "arn:aws:sqs:us-east-1:ACCOUNT_ID:cricksy-video-analysis-prod",
    "arn:aws:sqs:us-east-1:ACCOUNT_ID:cricksy-video-analysis-dlq-prod"
  ]
}
```

### CloudWatch Alarms
Monitor queue health:
```terraform
# Alert on messages in DLQ
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "cricksy-video-analysis-dlq-has-messages"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = 1
  dimensions = {
    QueueName = aws_sqs_queue.video_analysis_dlq.name
  }
}
```

## Testing Locally

```bash
# Using AWS CLI (requires credentials)
aws sqs send-message \
  --queue-url <queue_url> \
  --message-body '{"video_path": "/path/to/video.mp4", "sample_fps": 2}'

# List messages
aws sqs receive-message --queue-url <queue_url> --max-number-of-messages 1
```

## Future Enhancements

- [ ] FIFO queue variant for strict ordering
- [ ] Message deduplication for idempotency
- [ ] Encryption at rest (KMS)
- [ ] Lambda consumer integration
- [ ] SNS notifications on DLQ events

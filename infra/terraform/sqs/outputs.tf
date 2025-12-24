output "video_analysis_queue_url" {
  description = "URL of the main video analysis queue"
  value       = aws_sqs_queue.video_analysis.url
}

output "video_analysis_queue_arn" {
  description = "ARN of the main video analysis queue"
  value       = aws_sqs_queue.video_analysis.arn
}

output "video_analysis_dlq_url" {
  description = "URL of the video analysis Dead Letter Queue"
  value       = aws_sqs_queue.video_analysis_dlq.url
}

output "video_analysis_dlq_arn" {
  description = "ARN of the video analysis Dead Letter Queue"
  value       = aws_sqs_queue.video_analysis_dlq.arn
}

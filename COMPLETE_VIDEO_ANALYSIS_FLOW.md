# Video Upload + Analysis Complete Flow

## End-to-End Sequence

### Phase 1: Video Upload Initiation (Client → API)

```
Client
  │
  └─→ 1. POST /api/coaches/plus/sessions
      Create video session
      ├─ Headers: Authorization: Bearer <token>
      ├─ Body: {title, player_ids, notes}
      └─ Response: {session_id, status: "pending"}
  
  └─→ 2. POST /api/coaches/plus/videos/upload/initiate
      Get presigned S3 URL
      ├─ Headers: Authorization: Bearer <token>
      ├─ Body: {session_id, sample_fps: 15, include_frames: true}
      └─ Response: {job_id, presigned_url, s3_bucket, s3_key, expires_in}
  
  └─→ 3. PUT <presigned_url> + video file
      Upload directly to S3
      ├─ Headers: Content-Type: video/mp4
      ├─ Body: binary video data
      └─ Response: 200 OK (from S3)

Backend (API)
  ├─ creates VideoAnalysisJob (status: queued)
  ├─ generates presigned PUT URL
  └─ returns URL + job details to client
```

### Phase 2: Upload Completion & Queueing (Client → API → SQS)

```
Client
  │
  └─→ POST /api/coaches/plus/videos/upload/complete
      Complete upload and enqueue for processing
      ├─ Headers: Authorization: Bearer <token>
      ├─ Body: {job_id}
      └─ Response: {job_id, status: "processing", sqs_message_id}

Backend (API)
  ├─ validates job exists
  ├─ validates ownership
  ├─ updates job.status → "processing"
  ├─ updates job.started_at → now()
  └─ sends message to SQS
      Message: {job_id, session_id, sample_fps, include_frames}
      └─ Response: SQS MessageId
  └─ stores sqs_message_id in job
  └─ commits to database

SQS Queue
  └─ Message visible (visibility timeout: 1 hour)
```

### Phase 3: Async Processing (Worker ← SQS → DB → S3)

```
Worker Service (2 tasks)
  │
  └─→ Long-poll SQS (20s timeout)
      ├─ Receive 1 message
      ├─ Parse job_id, session_id, sample_fps
      └─ Update job.status → "processing"
  
  └─→ Load from Database
      ├─ SELECT VideoAnalysisJob WHERE id = job_id
      ├─ Get session (for s3_bucket, s3_key)
      └─ Validate session.s3_key exists
  
  └─→ Download from S3
      ├─ S3GetObject(bucket, key)
      ├─ Save to /tmp/video.mp4
      └─ Verify file exists
  
  └─→ Analysis Pipeline
      ├─ Step 1: extract_pose_keypoints_from_video()
      │   └─ Input: /tmp/video.mp4 (sample_fps=15)
      │   └─ Output: {pose_summary, frames[], metrics}
      │
      ├─ Step 2: compute_pose_metrics()
      │   └─ Input: pose output
      │   └─ Output: {head_stability, balance_drift, knee_brace, ...}
      │
      ├─ Step 3: generate_findings()
      │   └─ Input: metrics
      │   └─ Output: {overall_level, findings[], cues, drills}
      │
      └─ Step 4: generate_report_text()
          └─ Input: findings
          └─ Output: {summary, top_issues, drills, one_week_plan}
  
  └─→ Persist Results
      ├─ UPDATE VideoAnalysisJob
      │   ├─ status = "completed"
      │   ├─ results = {pose, metrics, findings, report}
      │   ├─ completed_at = now()
      │   └─ error_message = NULL
      │
      └─ DELETE message from SQS
          ├─ SQS DeleteMessage(ReceiptHandle)
          └─ Message removed from queue

Database
  └─ Job updated with:
     ├─ status: "completed"
     ├─ started_at: <timestamp>
     ├─ completed_at: <timestamp>
     └─ results: <full JSON payload>
```

### Phase 4: Results Retrieval (Client → API → DB)

```
Client
  │
  └─→ GET /api/coaches/plus/analysis-jobs/{job_id}
      Get analysis results
      ├─ Headers: Authorization: Bearer <token>
      └─ Response: {job_id, status, results, timestamps, ...}

Backend (API)
  ├─ validates job exists
  ├─ validates ownership
  ├─ SELECT VideoAnalysisJob WHERE id = job_id
  ├─ returns job with results (if completed)
  └─ Response:
     {
       "job_id": "uuid",
       "session_id": "uuid",
       "status": "completed",
       "started_at": "2025-12-23T10:00:00Z",
       "completed_at": "2025-12-23T10:02:30Z",
       "results": {
         "pose": {
           "pose_summary": {...},
           "frames": [...]
         },
         "metrics": {
           "head_stability_score": {...},
           "balance_drift_score": {...},
           ...
         },
         "findings": {
           "overall_level": "medium",
           "findings": [...]
         },
         "report": {
           "summary": "Good form...",
           "top_issues": [...],
           "drills": [...]
         }
       }
     }

Client
  └─ Displays results in UI
     ├─ Pose visualization (frame by frame)
     ├─ Metrics dashboard
     ├─ Findings cards (with severity)
     └─ Coaching report + drills
```

## Database State Transitions

### VideoAnalysisJob State Machine

```
State: queued
├─ When: Created by POST /videos/upload/initiate
├─ Meaning: Waiting in SQS queue
├─ sqs_message_id: <set>
├─ started_at: NULL
├─ results: NULL
└─ Transitions to: processing (when worker picks up)

State: processing
├─ When: Worker starts processing
├─ Meaning: Video being downloaded and analyzed
├─ started_at: <set to now>
├─ results: NULL
└─ Transitions to: completed or failed (when worker finishes)

State: completed
├─ When: Worker finishes successfully
├─ Meaning: Results available
├─ completed_at: <set to now>
├─ results: {pose, metrics, findings, report}
├─ error_message: NULL
└─ Final state (no transitions)

State: failed
├─ When: Worker encounters error
├─ Meaning: Processing failed, results unavailable
├─ completed_at: <set to now>
├─ error_message: <exception message>
├─ results: NULL or partial
└─ Final state (no transitions)
```

## Error Scenarios

### Scenario 1: Upload Fails (S3)

```
Client
  └─→ PUT <presigned_url> + video
      └─ S3 rejects upload (permission, network, etc)
      └─ 403 or 5xx from S3

Result: Job remains in "queued" state
Action: Client can retry or delete job
```

### Scenario 2: Complete Without Upload (Missing S3 Key)

```
Client
  └─→ POST /videos/upload/complete {job_id}

Backend
  └─→ Load job from DB
      └─ job.session.s3_key = NULL
      └─ Error: "Job missing S3 key"

Result: 500 error returned to client
Action: Database job remains "queued"
```

### Scenario 3: Worker Download Fails (S3)

```
Worker
  └─→ S3GetObject(bucket, key)
      └─ 404 Not Found (file deleted)
      └─ 403 Forbidden (permissions)

Worker
  └─→ Mark job as "failed"
  └─→ Store error_message: "Failed to download video from S3: 404 Not Found"
  └─→ Keep message in SQS queue (don't delete)

Result: Message visible after visibility timeout (1 hour)
Action: Message will be retried (up to 3 times, then DLQ)
```

### Scenario 4: Worker Analysis Fails (MediaPipe)

```
Worker
  └─→ extract_pose_keypoints_from_video()
      └─ MediaPipe model missing
      └─ RuntimeError: "MediaPipe model not initialized"

Worker
  └─→ Mark job as "failed"
  └─→ Store error_message: "Processing failed: MediaPipe model not initialized"
  └─→ Keep message in SQS queue (don't delete)

Result: Message visible after visibility timeout
Action: Message will be retried (may fail again if model still missing)
```

### Scenario 5: Worker Database Commit Fails

```
Worker
  └─→ UPDATE job with results
      └─ Database connection lost
      └─ Commit fails

Worker
  └─→ Mark job as "failed"
  └─→ Store error_message: "Processing failed: Database connection lost"
  └─→ Keep message in SQS queue (don't delete)

Result: Message visible after visibility timeout
Action: Message will be retried
```

### Scenario 6: Message Visibility Timeout Expires

```
Worker (Task 1)
  └─→ Start processing job_id=ABC
  ├─ Visibility timeout starts (3600s = 1 hour)
  ├─ Download video (30s)
  ├─ Analysis pipeline (120s)
  └─ Database update hangs (>3000s)

Result: Visibility timeout expires
├─ Message becomes visible again in queue
├─ Worker (Task 2) receives same message
├─ Both workers now processing same job (race condition)

Prevention: Increase visibility timeout in SQS
Solution: Set VisibilityTimeout ≥ max processing time + buffer
  └─ Recommended: 7200s (2 hours) for large videos
```

## Monitoring & Observability

### CloudWatch Logs

**API Logs** (`/cricksy-ai/api`)
```
INFO: [2025-12-23 10:00:00] POST /api/coaches/plus/videos/upload/initiate - user_id=u123
INFO: [2025-12-23 10:00:01] Created job job_id=j456 with presigned_url
INFO: [2025-12-23 10:00:05] POST /api/coaches/plus/videos/upload/complete - job_id=j456
INFO: [2025-12-23 10:00:06] Sent message to SQS - MessageId=m789
```

**Worker Logs** (`/cricksy-ai/worker`)
```
INFO: [2025-12-23 10:00:10] Received 1 message from SQS - MessageId=m789
INFO: [2025-12-23 10:00:10] Processing message for job j456
INFO: [2025-12-23 10:00:10] Downloaded s3://bucket/coach_plus/coach/u123/s456/v789/original.mp4
INFO: [2025-12-23 10:00:10] Starting analysis pipeline for /tmp/video.mp4
INFO: [2025-12-23 10:00:15] Step 1/4: Extracting pose keypoints... (took 30s)
INFO: [2025-12-23 10:00:15] Step 2/4: Computing pose metrics... (took 1s)
INFO: [2025-12-23 10:00:15] Step 3/4: Generating findings... (took 1s)
INFO: [2025-12-23 10:00:16] Step 4/4: Generating report... (took 1s)
INFO: [2025-12-23 10:00:16] Updated job j456 with status completed
INFO: [2025-12-23 10:00:16] Deleted message m789
```

### CloudWatch Metrics

**SQS Queue**
```
ApproximateNumberOfMessages: 0-5 (healthy)
ApproximateNumberOfMessages: > 10 (backlog)
ApproximateNumberOfMessages: > 50 (critical)

ApproximateAgeOfOldestMessage: 0-60s (processing quickly)
ApproximateAgeOfOldestMessage: > 600s (slow processing)
```

**Worker Tasks**
```
CPUUtilization: 20-40% (normal)
CPUUtilization: > 80% (heavy processing or stuck)

MemoryUtilization: 50-70% (normal)
MemoryUtilization: > 90% (potential memory issue)

TaskCount: 2 (desired)
RunningCount: 2 (healthy)
RunningCount: < 2 (crashing or recovering)
```

### Health Checks

```bash
# Check queue depth
aws sqs get-queue-attributes \
  --queue-url $SQS_QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages \
  --query 'Attributes.ApproximateNumberOfMessages'

# Check worker tasks
aws ecs list-tasks \
  --cluster cricksy-ai-cluster \
  --service-name cricksy-ai-worker-service \
  --query 'taskArns'

# Check DLQ for failed messages
aws sqs get-queue-attributes \
  --queue-url $DLQ_URL \
  --attribute-names ApproximateNumberOfMessages
```

## Troubleshooting Checklist

- [ ] API service is running (1 task)
- [ ] Worker service is running (2 tasks)
- [ ] S3 bucket exists and is accessible
- [ ] SQS queue exists and is not rate-limited
- [ ] Database is accessible from both services
- [ ] IAM roles have correct permissions
- [ ] Environment variables are set in ECS
- [ ] Presigned URLs are being generated correctly
- [ ] Videos are being uploaded to correct S3 keys
- [ ] Messages are appearing in SQS queue
- [ ] Worker is polling SQS (check logs)
- [ ] Messages are being deleted from queue (not stuck)
- [ ] Jobs are being marked as "completed" (not stuck in "processing")
- [ ] CloudWatch logs are being written to
- [ ] No errors in API logs about SQS send failures
- [ ] No errors in Worker logs about database updates

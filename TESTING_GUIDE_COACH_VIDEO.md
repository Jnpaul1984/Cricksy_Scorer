# 🧪 TESTING GUIDE - Coach Pro Plus Video Upload

**Status**: Ready to Test
**Commit**: 895001e
**Date**: December 26, 2025

---

## 🎯 TEST CHECKLIST

### SETUP
- [ ] Ensure Coach Pro Plus user is logged in
- [ ] Open browser DevTools (F12)
- [ ] Go to **Network** tab
- [ ] Go to **Console** tab (check for errors)

---

## ✅ HAPPY PATH TESTS

### Test 1: Create Video Session
```
STEPS:
1. Navigate to /coach-pro-plus/video-sessions
2. See "Unlock Video Sessions" card (if not Coach Pro Plus) OR session list (if Coach Pro Plus)
3. Click "+ New Video Session"
4. Fill form:
   - Title: "Batting Technique Test"
   - Players: (optional)
   - Notes: (optional)
5. Click "Create Session"

EXPECTED RESULTS:
✅ Network tab shows:
   POST /api/coaches/plus/sessions → 201 or 200
✅ Session appears in list
✅ No errors in console

FAILURE RECOVERY:
❌ 403 response?
   → Check error message in UI
   → Should say: "Video sessions feature is not enabled on your plan"
```

### Test 2: Upload Video File
```
STEPS:
1. In session card, click "Upload & Analyze"
2. Select a video file (MP4, MOV, or AVI)
3. Set sample_fps if needed (default 10)
4. Click "Upload"

EXPECTED RESULTS:
✅ Network tab sequence:
   a) POST /api/coaches/plus/videos/upload/initiate → 200
      Payload: {session_id, sample_fps, include_frames}
      Response: {job_id, presigned_url, s3_bucket, s3_key}

   b) PUT https://bucket.s3.amazonaws.com/...?signature
      Headers: Content-Type: video/mp4
      Status: 200 (from S3, not your API)
      Body: File binary data

   c) POST /api/coaches/plus/videos/upload/complete → 200
      Payload: {job_id}
      Response: {status: "processing", sqs_message_id}

✅ Progress bar shows 0-100%
✅ After upload completes:
   - Status shows "Waiting for analysis..."
   - Polling starts automatically (every 5s)

FAILURE RECOVERY:
❌ PUT to S3 gets 403?
   → S3 signature/Content-Type mismatch
   → Check browser CORS error in Network tab

❌ PUT to S3 gets CORS error?
   → S3 CORS not configured
   → Check S3 bucket CORS rules

❌ Upload fails with "feature not enabled"?
   → Should show: "Video upload feature is not enabled on your plan"
   → Check ApiError.isFeatureDisabled() logic
```

### Test 3: Poll for Results (5 second intervals)
```
STEPS:
1. After upload completes (Test 2)
2. Observe Network tab every 5 seconds

EXPECTED RESULTS:
✅ Every 5 seconds:
   GET /api/coaches/plus/analysis-jobs/{job_id} → 200

✅ Response body:
   {
     "id": "...",
     "status": "processing",  (changes to "completed" when done)
     "results": null          (filled in when completed)
   }

✅ Once status = "completed":
   - Network stops polling
   - Modal appears showing results
   - Coaching report displays
   - Biomechanical metrics shown

FAILURE RECOVERY:
❌ Polling never stops?
   → Memory leak! Check onBeforeUnmount in view
   → Manually navigate away and check if polling stops

❌ 401 response?
   → Auth expired
   → Should show: "Your session expired. Please log in again."
```

### Test 4: View Results Modal
```
STEPS:
1. Wait for job to complete (status="completed")
2. Modal should automatically appear

EXPECTED RESULTS:
✅ Modal shows:
   - Pose summary (detection rate, frames)
   - Coaching report (summary, key issues, drills)
   - Biomechanical metrics (shoulder rotation, hip alignment, etc.)
   - One-week training plan
   - Close button

✅ Numbers formatted correctly (2 decimal places)
✅ Drills show name, description, duration, focus areas
```

---

## ❌ ERROR PATH TESTS

### Test 5: Feature-Disabled Error (403)
```
SETUP:
- Use a user WITHOUT Coach Pro Plus access
- Ensure backend returns 403 with feature-disabled message

STEPS:
1. Navigate to /coach-pro-plus/video-sessions
2. Should see upgrade card (if clientStore.isCoachProPlus = false)

EXPECTED RESULTS:
✅ Card shows:
   "Unlock Video Sessions"
   "Available with Coach Pro Plus ($24.99/month)"
   "Upgrade to Coach Pro Plus" button

✅ If trying API directly without UI gate:
   Network tab shows: POST /api/coaches/plus/sessions → 403
   Error message: "Video sessions feature is not enabled on your plan. Please upgrade your subscription."

VERIFICATION:
Check store error handling catches ApiError.isFeatureDisabled()
```

### Test 6: Unauthorized Error (401)
```
SETUP:
- User is logged in
- Clear auth token or use invalid token

STEPS:
1. Attempt to upload a video
2. Backend returns 401

EXPECTED RESULTS:
✅ Error message shows:
   "Your session expired. Please log in again."
   (Not generic "Failed to upload")

✅ Console shows:
   ApiError {
     status: 401,
     detail: "Unauthorized",
     isUnauthorized(): true
   }
```

### Test 7: Memory Leak Prevention
```
SETUP:
- Have polling active (job in progress)

STEPS:
1. Start video upload and wait for polling to begin
2. Watch Network tab (should see GET requests every 5s)
3. Navigate to different page (e.g., /home)
4. Wait 10 seconds
5. Check Network tab

EXPECTED RESULTS:
✅ After leaving page:
   - No more GET /api/coaches/plus/analysis-jobs/{job_id} requests
   - onBeforeUnmount hook fired
   - videoStore.cleanup() cleared intervals

❌ FAILURE:
   - Requests continue every 5s
   → Memory leak! Check view doesn't have onBeforeUnmount hook
```

---

## 📋 DEBUGGING TIPS

### Check Error in Console
```javascript
// In browser console
// Look for messages like:
[coachPlusVideo] fetchSessions error: ApiError...
[coachPlusVideo] startUpload error: ApiError...

// Check if ApiError is proper type
err instanceof ApiError  // Should be true
err.isFeatureDisabled()  // true if 403 feature error
err.isUnauthorized()     // true if 401 auth error
err.detail              // Contains backend error message
```

### Check Network Response
```javascript
// For any 4xx/5xx response, click on response tab:
{
  "detail": "Video upload feature is not enabled on your plan",
  "code": "feature_disabled",  // ← Check for "feature" in code/detail
  "status": 403
}
```

### Check Polling Cleanup
```javascript
// Open DevTools, set breakpoint in view onBeforeUnmount
// Or add console log:
onBeforeUnmount(() => {
  console.log('Cleanup called, stopping', pollingJobs.value.size, 'intervals')
  videoStore.cleanup()
})

// Then navigate away and check console
```

---

## 🎬 FULL USER FLOW (One Test Run)

```
TIME: 0s
  - User navigates to /coach-pro-plus/video-sessions
  - fetchSessions() called
  - Network: GET /api/coaches/plus/sessions → 200
  - Session list loads

TIME: 5s
  - User clicks "+ New Video Session"
  - Fills form
  - Clicks "Create"
  - Network: POST /api/coaches/plus/sessions → 201
  - Session appears in list

TIME: 15s
  - User clicks "Upload & Analyze" on session
  - Selects video.mp4 (50MB)
  - Clicks "Upload"

TIME: 16s
  - Network: POST /api/coaches/plus/videos/upload/initiate → 200
  - Returns presigned_url + job_id
  - Progress bar appears

TIME: 17s
  - Network: PUT https://s3.amazonaws.com/...presigned → 200
  - File uploads to S3 (50MB takes ~30s at typical speed)
  - Progress bar updates to 50%

TIME: 47s
  - Network: POST /api/coaches/plus/videos/upload/complete → 200
  - Status shows "Waiting for analysis..."
  - Polling starts

TIME: 52s, 57s, 62s, 67s, 72s, 77s...
  - Network: GET /api/coaches/plus/analysis-jobs/{job_id} → 200
  - status: "processing" (repeats every 5s)

TIME: 127s
  - Network: GET /api/coaches/plus/analysis-jobs/{job_id} → 200
  - status: "completed"
  - results: {...coaching report, metrics, drills...}
  - Polling STOPS
  - Modal appears with results

TIME: 135s
  - User reads coaching report
  - Clicks close button
  - User navigates away

TIME: 140s
  - onBeforeUnmount hook fires
  - videoStore.cleanup() called
  - All intervals cleared
  - No more network requests
```

---

## ✅ SIGN-OFF CHECKLIST

Run through all tests in order. Check off as you go:

- [ ] Test 1: Create session works, API called correctly
- [ ] Test 2: Upload file, presigned URL works, S3 PUT succeeds
- [ ] Test 3: Polling starts and stops correctly when completed
- [ ] Test 4: Results modal displays all content correctly
- [ ] Test 5: 403 error shows feature-disabled message (not generic)
- [ ] Test 6: 401 error shows session-expired message
- [ ] Test 7: Memory leak test - no polling after navigation
- [ ] Network tab: All endpoints match specification
- [ ] Console: No errors or warnings (only info logs)
- [ ] UI: Responsive and user-friendly error messages

**If all ✅**: Ready to deploy

**If any ❌**: Debug and fix before merging

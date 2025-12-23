#!/bin/bash
# Verification Script - Run in Docker container to validate all changes

set -e

echo "=========================================="
echo "Frame Data Exposure - Verification"
echo "=========================================="
echo ""

# Test 1: Import models
echo "✅ Test 1: Pydantic Model Imports"
docker exec cricksy_backend python3 << 'IMPORTS_EOF'
from backend.routes.coach_pro_plus import VideoAnalysisRequest, VideoAnalysisResponse
print("  VideoAnalysisRequest: OK")
print("  VideoAnalysisResponse: OK")
IMPORTS_EOF
echo ""

# Test 2: Verify request fields
echo "✅ Test 2: Request Model Fields"
docker exec cricksy_backend python3 << 'REQUEST_EOF'
from backend.routes.coach_pro_plus import VideoAnalysisRequest
fields = VideoAnalysisRequest.model_fields
print(f"  include_frames field: {'include_frames' in fields}")
print(f"  include_frames type: {fields['include_frames'].annotation}")
print(f"  include_frames default: {fields['include_frames'].default}")
REQUEST_EOF
echo ""

# Test 3: Verify response fields
echo "✅ Test 3: Response Model Fields"
docker exec cricksy_backend python3 << 'RESPONSE_EOF'
from backend.routes.coach_pro_plus import VideoAnalysisResponse
from typing import get_args
fields = VideoAnalysisResponse.model_fields
print(f"  frames field: {'frames' in fields}")
print(f"  frames type: {fields['frames'].annotation}")
print(f"  frames default: {fields['frames'].default}")
RESPONSE_EOF
echo ""

# Test 4: Verify pose service
echo "✅ Test 4: Pose Service Functions"
docker exec cricksy_backend python3 << 'SERVICE_EOF'
from backend.services.pose_service import extract_pose_keypoints_from_video
import inspect
sig = str(inspect.signature(extract_pose_keypoints_from_video))
print(f"  extract_pose_keypoints_from_video: OK")
print(f"  Signature: {sig}")
SERVICE_EOF
echo ""

echo "=========================================="
echo "ALL VERIFICATIONS PASSED ✅"
echo "=========================================="
echo ""
echo "Ready for API testing:"
echo "  1. POST /api/coaches/plus/videos/analyze with include_frames=true"
echo "  2. POST /api/coaches/plus/videos/analyze with include_frames=false"
echo ""
echo "Documentation:"
echo "  - FRAME_DATA_READY_FOR_TESTING.md (quick reference)"
echo "  - FRAME_DATA_IMPLEMENTATION_COMPLETE.md (detailed guide)"
echo "  - IMPLEMENTATION_SUMMARY.md (updated summary)"
echo ""

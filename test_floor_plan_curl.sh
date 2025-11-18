#!/bin/bash

# Floor Plan Analysis API Test Script (cURL)
# Usage: ./test_floor_plan_curl.sh [image_path]

API_BASE_URL="http://127.0.0.1:8000/api/inventory"
ANALYZE_ENDPOINT="${API_BASE_URL}/analyze-floor-plan/"
SERVICE_INFO_ENDPOINT="${API_BASE_URL}/service-info/"

echo "============================================================"
echo " Floor Plan Analysis API Test (cURL)"
echo "============================================================"

# Test 1: Get Service Information
echo ""
echo "📋 Testing Service Info Endpoint..."
echo "GET ${SERVICE_INFO_ENDPOINT}"
echo ""

curl -X GET \
  "${SERVICE_INFO_ENDPOINT}" \
  -H "Accept: application/json" \
  -w "\n\nStatus Code: %{http_code}\nTotal Time: %{time_total}s\n" \
  -s

echo ""
echo "============================================================"

# Test 2: Floor Plan Analysis
echo ""
echo "🏠 Testing Floor Plan Analysis Endpoint..."
echo "POST ${ANALYZE_ENDPOINT}"

# Check if image path is provided
if [ -z "$1" ]; then
    echo ""
    echo "❌ No image path provided!"
    echo "Usage: $0 [image_path]"
    echo ""
    echo "Example:"
    echo "  $0 media/property_floor_maps/sample_floor_plan.jpg"
    echo "  $0 /path/to/your/floor_plan.png"
    echo ""
    echo "Supported formats: .jpg, .jpeg, .png, .gif, .bmp"
    exit 1
fi

IMAGE_PATH="$1"

# Check if file exists
if [ ! -f "$IMAGE_PATH" ]; then
    echo ""
    echo "❌ Image file not found: $IMAGE_PATH"
    exit 1
fi

# Get file info
FILE_SIZE=$(stat -c%s "$IMAGE_PATH" 2>/dev/null || stat -f%z "$IMAGE_PATH" 2>/dev/null)
FILE_SIZE_MB=$(echo "scale=2; $FILE_SIZE / 1024 / 1024" | bc)

echo "Image: $IMAGE_PATH"
echo "Size: ${FILE_SIZE_MB} MB"
echo ""

# Check file size (10MB limit)
if (( $(echo "$FILE_SIZE > 10485760" | bc -l) )); then
    echo "⚠️  Warning: File size exceeds 10MB limit"
fi

echo "Uploading and analyzing..."
echo ""

# Perform the API call
curl -X POST \
  "${ANALYZE_ENDPOINT}" \
  -H "Accept: application/json" \
  -F "floor_plan=@${IMAGE_PATH}" \
  -w "\n\nStatus Code: %{http_code}\nTotal Time: %{time_total}s\nUpload Speed: %{speed_upload} bytes/sec\n" \
  -s

echo ""
echo "============================================================"
echo "✅ Test completed!"
echo ""
echo "Tips:"
echo "  • Make sure Django server is running: python manage.py runserver"
echo "  • Check server logs for detailed analysis information"
echo "  • Use jq for better JSON formatting: curl ... | jq ."
echo ""

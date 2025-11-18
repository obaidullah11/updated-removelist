@echo off
REM Floor Plan Analysis API Test Script (cURL for Windows)
REM Usage: test_floor_plan_curl.bat [image_path]

set API_BASE_URL=http://127.0.0.1:8000/api/inventory
set ANALYZE_ENDPOINT=%API_BASE_URL%/analyze-floor-plan/
set SERVICE_INFO_ENDPOINT=%API_BASE_URL%/service-info/

echo ============================================================
echo  Floor Plan Analysis API Test (cURL - Windows)
echo ============================================================

REM Test 1: Get Service Information
echo.
echo 📋 Testing Service Info Endpoint...
echo GET %SERVICE_INFO_ENDPOINT%
echo.

curl -X GET "%SERVICE_INFO_ENDPOINT%" -H "Accept: application/json" -w "%%{http_code}" -s
echo.
echo.

echo ============================================================

REM Test 2: Floor Plan Analysis
echo.
echo 🏠 Testing Floor Plan Analysis Endpoint...
echo POST %ANALYZE_ENDPOINT%

REM Check if image path is provided
if "%~1"=="" (
    echo.
    echo ❌ No image path provided!
    echo Usage: %0 [image_path]
    echo.
    echo Example:
    echo   %0 media\property_floor_maps\sample_floor_plan.jpg
    echo   %0 C:\path\to\your\floor_plan.png
    echo.
    echo Supported formats: .jpg, .jpeg, .png, .gif, .bmp
    pause
    exit /b 1
)

set IMAGE_PATH=%~1

REM Check if file exists
if not exist "%IMAGE_PATH%" (
    echo.
    echo ❌ Image file not found: %IMAGE_PATH%
    pause
    exit /b 1
)

echo Image: %IMAGE_PATH%
echo.
echo Uploading and analyzing...
echo.

REM Perform the API call
curl -X POST "%ANALYZE_ENDPOINT%" -H "Accept: application/json" -F "floor_plan=@%IMAGE_PATH%" -w "%%{http_code}" -s
echo.
echo.

echo ============================================================
echo ✅ Test completed!
echo.
echo Tips:
echo   • Make sure Django server is running: python manage.py runserver
echo   • Check server logs for detailed analysis information
echo   • Install jq for better JSON formatting: curl ... ^| jq .
echo.
pause

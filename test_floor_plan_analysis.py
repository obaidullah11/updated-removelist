"""
Test script for the Floor Plan Analysis API endpoint.

This script tests the floor plan analysis service endpoint:
- POST /api/inventory/analyze-floor-plan/
- GET /api/inventory/service-info/

Usage:
    python test_floor_plan_analysis.py [image_path]

If no image path is provided, it will look for test images in the media directory.
"""
import os
import sys
import requests
import json
from pathlib import Path
import mimetypes

# Configuration
API_BASE_URL = "http://127.0.0.1:8000/api/inventory"
ANALYZE_ENDPOINT = f"{API_BASE_URL}/analyze-floor-plan/"
SERVICE_INFO_ENDPOINT = f"{API_BASE_URL}/service-info/"

# Test image paths to try (relative to backend directory)
TEST_IMAGE_PATHS = [
    "media/property_floor_maps",  # Check existing floor maps
    "test_images",  # Custom test images directory
]

# Supported image extensions
SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']


def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def print_success(message):
    """Print a success message."""
    print(f"✅ {message}")


def print_error(message):
    """Print an error message."""
    print(f"❌ {message}")


def print_info(message):
    """Print an info message."""
    print(f"ℹ️  {message}")


def find_test_images():
    """Find available test images in the project."""
    test_images = []
    base_dir = Path(__file__).parent
    
    for test_path in TEST_IMAGE_PATHS:
        full_path = base_dir / test_path
        if full_path.exists() and full_path.is_dir():
            for ext in SUPPORTED_EXTENSIONS:
                images = list(full_path.glob(f"*{ext}"))
                test_images.extend(images)
    
    return test_images


def test_service_info():
    """Test the service info endpoint."""
    print_header("Testing Service Info Endpoint")
    print_info(f"GET {SERVICE_INFO_ENDPOINT}")
    
    try:
        response = requests.get(SERVICE_INFO_ENDPOINT, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Service info retrieved successfully!")
            
            # Pretty print the service info
            print("\n📋 Service Information:")
            print(json.dumps(data, indent=2))
            
            return True
        else:
            print_error(f"Failed to get service info: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Raw response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Connection failed. Make sure Django server is running on http://127.0.0.1:8000")
        return False
    except requests.exceptions.Timeout:
        print_error("Request timed out")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        return False


def test_floor_plan_analysis(image_path):
    """Test the floor plan analysis endpoint with an image."""
    print_header(f"Testing Floor Plan Analysis")
    print_info(f"POST {ANALYZE_ENDPOINT}")
    print_info(f"Image: {image_path}")
    
    # Check if file exists
    if not os.path.exists(image_path):
        print_error(f"Image file not found: {image_path}")
        return False
    
    # Get file info
    file_size = os.path.getsize(image_path)
    file_size_mb = file_size / (1024 * 1024)
    mime_type, _ = mimetypes.guess_type(image_path)
    
    print_info(f"File size: {file_size_mb:.2f} MB")
    print_info(f"MIME type: {mime_type}")
    
    # Check file size limit
    if file_size > 10 * 1024 * 1024:  # 10MB
        print_error("File size exceeds 10MB limit")
        return False
    
    try:
        # Prepare the file for upload
        with open(image_path, 'rb') as image_file:
            files = {
                'floor_plan': (
                    os.path.basename(image_path),
                    image_file,
                    mime_type or 'application/octet-stream'
                )
            }
            
            print_info("Uploading and analyzing image...")
            response = requests.post(
                ANALYZE_ENDPOINT,
                files=files,
                timeout=120  # 2 minutes timeout for analysis
            )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Floor plan analysis completed successfully!")
            
            # Extract key information
            analysis_data = data.get('data', {})
            
            print(f"\n📊 Analysis Results:")
            print(f"   • Rooms detected: {analysis_data.get('rooms_detected', 'N/A')}")
            print(f"   • Analysis successful: {analysis_data.get('analysis_successful', 'N/A')}")
            
            # File info
            file_info = analysis_data.get('file_info', {})
            if file_info:
                print(f"\n📁 File Information:")
                print(f"   • Filename: {file_info.get('filename', 'N/A')}")
                print(f"   • Size: {file_info.get('size_bytes', 'N/A')} bytes")
                print(f"   • Type: {file_info.get('file_type', 'N/A')}")
            
            # Inventory summary
            inventory_summary = analysis_data.get('inventory_summary', {})
            if inventory_summary:
                print(f"\n📦 Inventory Summary:")
                for key, value in inventory_summary.items():
                    if isinstance(value, dict):
                        print(f"   • {key.replace('_', ' ').title()}:")
                        for sub_key, sub_value in value.items():
                            print(f"     - {sub_key.replace('_', ' ').title()}: {sub_value}")
                    else:
                        print(f"   • {key.replace('_', ' ').title()}: {value}")
            
            # Detailed rooms
            detailed_rooms = analysis_data.get('detailed_rooms', [])
            if detailed_rooms:
                print(f"\n🏠 Detailed Rooms ({len(detailed_rooms)} rooms):")
                for i, room in enumerate(detailed_rooms, 1):
                    print(f"   Room {i}: {room.get('room_name', 'Unknown')} ({room.get('room_type', 'Unknown type')})")
                    items_summary = room.get('items_summary', {})
                    if items_summary:
                        print(f"     Items: {items_summary}")
            
            # Full response (for debugging)
            print(f"\n📋 Full Response:")
            print(json.dumps(data, indent=2))
            
            return True
            
        else:
            print_error(f"Analysis failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Raw response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Connection failed. Make sure Django server is running on http://127.0.0.1:8000")
        return False
    except requests.exceptions.Timeout:
        print_error("Request timed out (analysis may take a while for large images)")
        return False
    except FileNotFoundError:
        print_error(f"Image file not found: {image_path}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        return False


def main():
    """Main test function."""
    print_header("Floor Plan Analysis API Test")
    print_info("Testing the floor plan analysis service endpoints")
    
    # Test 1: Service Info
    service_info_success = test_service_info()
    
    # Test 2: Floor Plan Analysis
    image_path = None
    
    # Check command line argument
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        if not os.path.exists(image_path):
            print_error(f"Provided image path does not exist: {image_path}")
            image_path = None
    
    # If no image provided or invalid, try to find test images
    if not image_path:
        print_info("No image path provided, searching for test images...")
        test_images = find_test_images()
        
        if test_images:
            image_path = str(test_images[0])  # Use the first found image
            print_info(f"Found {len(test_images)} test images, using: {image_path}")
        else:
            print_error("No test images found!")
            print_info("Available test image directories:")
            for test_path in TEST_IMAGE_PATHS:
                print(f"  - {test_path}")
            print_info(f"Supported extensions: {', '.join(SUPPORTED_EXTENSIONS)}")
            print_info("Usage: python test_floor_plan_analysis.py [image_path]")
            return False
    
    # Run the analysis test
    analysis_success = test_floor_plan_analysis(image_path)
    
    # Summary
    print_header("Test Summary")
    print(f"Service Info Test: {'✅ PASSED' if service_info_success else '❌ FAILED'}")
    print(f"Floor Plan Analysis Test: {'✅ PASSED' if analysis_success else '❌ FAILED'}")
    
    if service_info_success and analysis_success:
        print_success("All tests passed! 🎉")
        return True
    else:
        print_error("Some tests failed. Check the Django server and try again.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

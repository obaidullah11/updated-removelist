# Floor Plan Analysis API Testing Templates

This directory contains comprehensive testing templates for the Floor Plan Analysis API endpoint.

## API Endpoint Information

- **Endpoint**: `POST http://127.0.0.1:8000/api/inventory/analyze-floor-plan/`
- **Service Info**: `GET http://127.0.0.1:8000/api/inventory/service-info/`
- **Authentication**: None required
- **Content-Type**: `multipart/form-data`
- **Field Name**: `floor_plan`
- **Supported Formats**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`
- **Max File Size**: 10MB

## Available Testing Templates

### 1. HTML Web Interface (`test_floor_plan_api.html`)

**Best for**: Interactive testing with a user-friendly interface

**Features**:
- ✅ File upload with drag-and-drop support
- ✅ Real-time file validation (size, format)
- ✅ Service information retrieval
- ✅ Formatted JSON response display
- ✅ Error handling and loading states
- ✅ Responsive design

**Usage**:
```bash
# Open in any web browser
open test_floor_plan_api.html
# or
start test_floor_plan_api.html  # Windows
```

### 2. Python Test Script (`test_floor_plan_analysis.py`)

**Best for**: Automated testing and integration into CI/CD pipelines

**Features**:
- ✅ Automatic test image discovery
- ✅ Comprehensive error handling
- ✅ Detailed response analysis
- ✅ Service info validation
- ✅ File size and format validation
- ✅ Pretty-printed JSON output

**Usage**:
```bash
# Test with automatic image discovery
python test_floor_plan_analysis.py

# Test with specific image
python test_floor_plan_analysis.py path/to/your/floor_plan.jpg

# Test with image from media directory
python test_floor_plan_analysis.py media/property_floor_maps/sample_floor_plan.jpg
```

**Requirements**:
```bash
pip install requests
```

### 3. cURL Scripts

#### Linux/macOS (`test_floor_plan_curl.sh`)

**Best for**: Command-line testing on Unix systems

**Usage**:
```bash
# Make executable
chmod +x test_floor_plan_curl.sh

# Run test
./test_floor_plan_curl.sh path/to/your/floor_plan.jpg
```

#### Windows (`test_floor_plan_curl.bat`)

**Best for**: Command-line testing on Windows

**Usage**:
```cmd
test_floor_plan_curl.bat path\to\your\floor_plan.jpg
```

**Requirements**: cURL must be installed and available in PATH

## Test Image Preparation

### Finding Test Images

The Python script automatically searches for test images in:
- `media/property_floor_maps/` (existing floor plan images)
- `test_images/` (custom test directory)

### Creating Test Images

1. **Create a test images directory**:
```bash
mkdir test_images
```

2. **Add sample floor plan images**:
   - Download architectural floor plans from free resources
   - Use simple hand-drawn floor plans
   - Convert existing images to supported formats

3. **Recommended test cases**:
   - Small image (< 1MB): Quick processing test
   - Large image (5-10MB): Performance test
   - Different formats: `.jpg`, `.png`, `.gif`
   - Complex floor plans: Multiple rooms
   - Simple floor plans: Single room

## Expected API Response

### Successful Analysis Response
```json
{
  "success": true,
  "message": "Floor plan analyzed successfully",
  "data": {
    "analysis_successful": true,
    "file_info": {
      "filename": "floor_plan.jpg",
      "size_bytes": 1234567,
      "file_type": ".jpg"
    },
    "rooms_detected": 5,
    "inventory_summary": {
      "total_rooms": 5,
      "total_regular_items": 25,
      "total_boxes": 12,
      "total_heavy_items": 8,
      "rooms_by_type": {
        "living_room": 1,
        "bedroom": 3,
        "bathroom": 1
      }
    },
    "detailed_rooms": [
      {
        "room_name": "Living Room",
        "room_type": "living_room",
        "area": 200,
        "items_summary": {
          "regular_items": 8,
          "boxes": 4,
          "heavy_items": 2
        }
      }
    ]
  }
}
```

### Service Info Response
```json
{
  "success": true,
  "message": "Floor plan analysis service information",
  "data": {
    "service_name": "Floor Plan Analysis Service",
    "version": "2.0",
    "description": "Analyzes architectural floor plan images...",
    "capabilities": [
      "Room detection and classification",
      "Inventory item generation by room type",
      "Packing box estimation"
    ],
    "supported_formats": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
    "max_file_size": "10MB"
  }
}
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - ✅ Ensure Django server is running: `python manage.py runserver`
   - ✅ Check the correct port (default: 8000)

2. **File Too Large**
   - ✅ Compress images to under 10MB
   - ✅ Use image optimization tools

3. **Unsupported Format**
   - ✅ Convert to supported formats: `.jpg`, `.png`, `.gif`, `.bmp`

4. **Analysis Timeout**
   - ✅ Use smaller images for testing
   - ✅ Check server logs for processing details

### Server Logs

Monitor Django logs for detailed analysis information:
```bash
tail -f logs/django.log
```

### Debug Mode

For detailed error information, ensure Django is running in debug mode:
```python
# settings.py
DEBUG = True
```

## Integration Examples

### JavaScript/Fetch API
```javascript
const formData = new FormData();
formData.append('floor_plan', fileInput.files[0]);

fetch('http://127.0.0.1:8000/api/inventory/analyze-floor-plan/', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

### Python Requests
```python
import requests

with open('floor_plan.jpg', 'rb') as f:
    files = {'floor_plan': f}
    response = requests.post(
        'http://127.0.0.1:8000/api/inventory/analyze-floor-plan/',
        files=files
    )
    data = response.json()
```

### cURL Command
```bash
curl -X POST \
  http://127.0.0.1:8000/api/inventory/analyze-floor-plan/ \
  -F "floor_plan=@floor_plan.jpg" \
  -H "Accept: application/json"
```

## Performance Testing

### Load Testing with Python
```python
import concurrent.futures
import requests

def test_analysis(image_path):
    with open(image_path, 'rb') as f:
        files = {'floor_plan': f}
        response = requests.post(ANALYZE_ENDPOINT, files=files)
        return response.status_code

# Run multiple concurrent requests
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(test_analysis, 'test_image.jpg') for _ in range(10)]
    results = [future.result() for future in futures]
```

## Contributing

When adding new test templates:

1. Follow the existing naming convention: `test_floor_plan_*`
2. Include comprehensive error handling
3. Add usage documentation
4. Test with various image formats and sizes
5. Update this README with new template information

## Support

For issues with the API or testing templates:

1. Check Django server logs
2. Verify image format and size requirements
3. Test with the HTML interface first for debugging
4. Review the API documentation in `FLOOR_PLAN_SERVICE_API.md`

# Floor Plan Analysis Service API

## Overview

A standalone REST API service that analyzes architectural floor plan images and extracts room information to generate comprehensive inventory checklists. **No authentication required** - perfect for testing and demonstrations.

## Endpoints

### 1. Service Information
```
GET /api/inventory/service-info/
```

**Response:**
```json
{
  "success": true,
  "message": "Floor plan analysis service information",
  "data": {
    "service_name": "Floor Plan Analysis Service",
    "version": "2.0",
    "description": "Analyzes architectural floor plan images to extract room information and generate inventory checklists",
    "capabilities": [
      "Room detection and classification",
      "Inventory item generation by room type",
      "Packing box estimation",
      "Heavy item identification",
      "OCR text recognition (when available)",
      "Architectural pattern recognition"
    ],
    "supported_formats": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
    "max_file_size": "10MB",
    "usage": {
      "endpoint": "/api/inventory/analyze-floor-plan/",
      "method": "POST",
      "content_type": "multipart/form-data",
      "required_field": "floor_plan",
      "authentication": "None required"
    }
  }
}
```

### 2. Analyze Floor Plan
```
POST /api/inventory/analyze-floor-plan/
Content-Type: multipart/form-data
```

**Request:**
- Field: `floor_plan` (image file)
- Supported formats: JPG, JPEG, PNG, GIF, BMP
- Max file size: 10MB

**Response:**
```json
{
  "success": true,
  "message": "Floor plan analyzed successfully",
  "data": {
    "analysis_successful": true,
    "file_info": {
      "filename": "floor_plan.jpg",
      "size_bytes": 245760,
      "file_type": ".jpg"
    },
    "rooms_detected": 7,
    "inventory_summary": {
      "total_rooms": 7,
      "total_regular_items": 31,
      "total_boxes": 15,
      "total_heavy_items": 10,
      "rooms_by_type": {
        "living_room": 2,
        "bedroom": 4,
        "bathroom": 1
      }
    },
    "detailed_rooms": [
      {
        "room_name": "Living Room 1",
        "room_type": "living_room",
        "area_pixels": 15502,
        "regular_items": [
          "Sofa", "Coffee table", "TV", "Bookshelf", "Lamps", "Decorations"
        ],
        "boxes": [
          "Living Room 1 - Books box",
          "Living Room 1 - Electronics box",
          "Living Room 1 - Decorations box"
        ],
        "heavy_items": [
          "Piano", "Large TV", "Heavy bookshelf"
        ],
        "item_counts": {
          "regular_items": 6,
          "boxes": 3,
          "heavy_items": 3
        }
      }
      // ... more rooms
    ]
  }
}
```

## Usage Examples

### cURL Commands

**Get service information:**
```bash
curl -X GET http://localhost:8000/api/inventory/service-info/
```

**Analyze a floor plan:**
```bash
curl -X POST http://localhost:8000/api/inventory/analyze-floor-plan/ \
     -F 'floor_plan=@/path/to/your/floor_plan.jpg' \
     -H 'Accept: application/json'
```

### JavaScript/Fetch API

```javascript
// Analyze floor plan
const formData = new FormData();
formData.append('floor_plan', fileInput.files[0]);

fetch('/api/inventory/analyze-floor-plan/', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  console.log('Analysis result:', data);
  // Process the room and inventory data
});
```

### Python Requests

```python
import requests

# Analyze floor plan
with open('floor_plan.jpg', 'rb') as f:
    files = {'floor_plan': f}
    response = requests.post(
        'http://localhost:8000/api/inventory/analyze-floor-plan/',
        files=files
    )
    
result = response.json()
print(f"Detected {result['data']['rooms_detected']} rooms")
```

## Features

### 🏠 **Room Detection**
- Automatically detects room boundaries using computer vision
- Classifies rooms by type (bedroom, kitchen, bathroom, etc.)
- Handles complex architectural floor plans

### 📦 **Inventory Generation**
- Generates appropriate items for each room type
- Creates packing box estimates
- Identifies heavy items requiring special handling

### 🔍 **Advanced Analysis**
- OCR text recognition for room labels
- Architectural pattern recognition
- Intelligent room classification based on size and position

### ⚡ **Performance**
- Fast analysis (typically 2-5 seconds)
- No database dependencies for the service
- Handles images up to 10MB

## Error Responses

### Invalid File Type
```json
{
  "success": false,
  "message": "Invalid file type",
  "errors": {
    "floor_plan": ["Please upload an image file. Allowed types: .jpg, .jpeg, .png, .gif, .bmp"]
  }
}
```

### File Too Large
```json
{
  "success": false,
  "message": "File too large",
  "errors": {
    "floor_plan": ["File size must be less than 10MB"]
  }
}
```

### Analysis Failed
```json
{
  "success": false,
  "message": "Floor plan analysis failed",
  "errors": {
    "analysis": ["Could not process the floor plan image"]
  }
}
```

## Technical Details

### Room Types Supported
- `living_room` - Living rooms, family rooms, dining rooms
- `bedroom` - All bedroom types
- `kitchen` - Kitchen and pantry areas
- `bathroom` - Bathrooms and powder rooms
- `office` - Home offices, studies, media rooms
- `garage` - Garages and utility areas
- `other` - Hallways, entries, etc.

### Generated Items by Room Type

**Living Room:**
- Regular items: Sofa, Coffee table, TV, Bookshelf, Lamps, Decorations
- Boxes: Books box, Electronics box, Decorations box
- Heavy items: Piano, Large TV, Heavy bookshelf

**Kitchen:**
- Regular items: Dining table, Chairs, Microwave, Toaster, Kitchen utensils, Dishes, Cookware
- Boxes: Kitchen appliances box, Dishes box, Pantry items box
- Heavy items: Refrigerator, Dishwasher, Oven

**Bedroom:**
- Regular items: Bed, Dresser, Nightstand, Lamp, Clothes, Bedding
- Boxes: Clothes box, Bedding box, Personal items box
- Heavy items: Mattress, Heavy dresser

**Bathroom:**
- Regular items: Towels, Toiletries, Bathroom accessories, Medicine cabinet items
- Boxes: Toiletries box, Bathroom supplies box
- Heavy items: None typically

## Integration

This service can be easily integrated into:
- Moving company websites
- Real estate applications
- Property management systems
- Inventory management tools

No authentication required makes it perfect for public-facing tools and demonstrations.

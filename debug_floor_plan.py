"""
Debug script to test floor plan analysis with detailed logging.
"""
import os
import sys
import django
from pathlib import Path
import logging

# Set up Django environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'removealist_backend.settings')
django.setup()

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_floor_plan.log')
    ]
)

# Import after Django setup
from apps.inventory.services.floor_plan_analyzer import FloorPlanAnalyzer
import cv2

def debug_floor_plan_analysis(image_path):
    """Debug the floor plan analysis process."""
    print(f"🔍 Debugging floor plan analysis for: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return
    
    try:
        # Load the image
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ Could not load image: {image_path}")
            return
        
        print(f"✅ Image loaded successfully: {image.shape}")
        
        # Initialize the analyzer
        analyzer = FloorPlanAnalyzer()
        print(f"✅ Analyzer initialized")
        print(f"📋 OCR Available: {analyzer.ocr_reader is not None}")
        
        # Test OCR detection
        print("\n" + "="*60)
        print("🔍 TESTING OCR DETECTION")
        print("="*60)
        
        rooms_ocr = analyzer.detect_rooms_with_ocr(image)
        print(f"📊 OCR detected {len(rooms_ocr)} rooms:")
        for i, room in enumerate(rooms_ocr, 1):
            print(f"  {i}. {room['name']} ({room['type']}) - Area: {room.get('area', 'N/A')}")
            if 'original_text' in room:
                print(f"     Original OCR text: '{room['original_text']}' (confidence: {room.get('text_confidence', 'N/A'):.2f})")
        
        # Test contour detection
        print("\n" + "="*60)
        print("🔍 TESTING CONTOUR DETECTION")
        print("="*60)
        
        rooms_contour = analyzer.detect_rooms_with_contours(image)
        print(f"📊 Contour detected {len(rooms_contour)} rooms:")
        for i, room in enumerate(rooms_contour, 1):
            print(f"  {i}. {room['name']} ({room['type']}) - Area: {room.get('area', 'N/A')}")
        
        # Test intelligent default rooms
        print("\n" + "="*60)
        print("🔍 TESTING INTELLIGENT DEFAULT ROOMS")
        print("="*60)
        
        rooms_default = analyzer.create_intelligent_default_rooms(image)
        print(f"📊 Default method created {len(rooms_default)} rooms:")
        for i, room in enumerate(rooms_default, 1):
            print(f"  {i}. {room['name']} ({room['type']}) - Area: {room.get('area', 'N/A')}")
        
        # Test the full analysis
        print("\n" + "="*60)
        print("🔍 TESTING FULL ANALYSIS")
        print("="*60)
        
        result = analyzer.analyze_floor_plan_service(image_path)
        print(f"📊 Full analysis result:")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Rooms created: {result.get('rooms_created', 0)}")
        
        if 'inventory_data' in result:
            print(f"  Inventory data ({len(result['inventory_data'])} rooms):")
            for i, room in enumerate(result['inventory_data'], 1):
                room_name = room.get('room_name', 'Unknown')
                room_type = room.get('room_type', 'unknown')
                floor_level = room.get('floor_level', 'Unknown Floor')
                dimensions = room.get('dimensions_m', 'No dimensions')
                features = room.get('features', [])
                
                print(f"    {i}. {room_name} ({room_type}) - {floor_level}")
                if dimensions != 'No dimensions':
                    print(f"       Dimensions: {dimensions}")
                if features:
                    print(f"       Features: {', '.join(features)}")
        
        # Show structured data (new format)
        if 'structured_data' in result:
            print(f"\n🏠 STRUCTURED FLOOR PLAN DATA:")
            structured = result['structured_data']
            print(f"  Property: {structured.get('property_address', 'N/A')}")
            
            for floor in structured.get('floors', []):
                print(f"\n  📍 {floor['name']} ({len(floor['rooms'])} rooms):")
                for room in floor['rooms']:
                    room_line = f"    • {room['name']} ({room.get('type', 'unknown')})"
                    if 'dimensions_m' in room:
                        room_line += f" - {room['dimensions_m']}"
                    print(room_line)
                    
                    if 'features' in room and room['features']:
                        print(f"      Features: {', '.join(room['features'])}")
                    if 'label' in room:
                        print(f"      OCR Label: '{room['label']}'")
            
            # Export structured data as JSON
            import json
            with open('structured_floor_plan.json', 'w') as f:
                json.dump(structured, f, indent=2)
            print(f"\n💾 Structured data saved to: structured_floor_plan.json")
        
        # Test individual OCR on different image preprocessing
        print("\n" + "="*60)
        print("🔍 TESTING RAW OCR OUTPUT")
        print("="*60)
        
        if analyzer.ocr_reader:
            # Original image
            print("📋 OCR on original image:")
            results1 = analyzer.ocr_reader.readtext(image)
            for bbox, text, confidence in results1:
                print(f"  Text: '{text}' (confidence: {confidence:.2f})")
            
            # Enhanced contrast
            print("\n📋 OCR on enhanced contrast image:")
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.equalizeHist(gray)
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            results2 = analyzer.ocr_reader.readtext(enhanced_bgr)
            for bbox, text, confidence in results2:
                print(f"  Text: '{text}' (confidence: {confidence:.2f})")
            
            # Thresholded image
            print("\n📋 OCR on thresholded image:")
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            thresh_bgr = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
            results3 = analyzer.ocr_reader.readtext(thresh_bgr)
            for bbox, text, confidence in results3:
                print(f"  Text: '{text}' (confidence: {confidence:.2f})")
        
        print("\n" + "="*60)
        print("✅ DEBUG ANALYSIS COMPLETE")
        print("="*60)
        print("Check debug_floor_plan.log for detailed logs")
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main debug function."""
    print("🏠 Floor Plan Analysis Debug Tool")
    print("="*60)
    
    # Check for command line argument
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Look for test images
        test_paths = [
            "media/property_floor_maps",
            "test_images"
        ]
        
        image_path = None
        for test_path in test_paths:
            if os.path.exists(test_path):
                for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    images = list(Path(test_path).glob(f"*{ext}"))
                    if images:
                        image_path = str(images[0])
                        break
                if image_path:
                    break
        
        if not image_path:
            print("❌ No image provided and no test images found!")
            print("Usage: python debug_floor_plan.py [image_path]")
            print("Or place test images in media/property_floor_maps/ or test_images/")
            return
    
    debug_floor_plan_analysis(image_path)

if __name__ == "__main__":
    main()

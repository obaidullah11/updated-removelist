#!/usr/bin/env python3
"""
OCR Debug Test Script
Run this script to test if EasyOCR is working properly with your floor plan images.
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'removealist_backend.settings')
django.setup()

from apps.inventory.services.floor_plan_analyzer import EnhancedFloorPlanAnalyzer

def test_ocr_installation():
    """Test if OCR is properly installed and working."""
    print("=== OCR Installation Test ===")
    
    try:
        import easyocr
        print("✅ EasyOCR imported successfully")
        
        # Try to initialize reader
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print("✅ EasyOCR reader initialized successfully")
        
        # Test with a simple image
        import numpy as np
        import cv2
        test_image = np.ones((100, 300, 3), dtype=np.uint8) * 255
        cv2.putText(test_image, 'TEST TEXT', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        results = reader.readtext(test_image)
        print(f"✅ OCR test completed - found {len(results)} text elements")
        
        if results:
            for bbox, text, conf in results:
                print(f"   Detected: '{text}' (confidence: {conf:.2f})")
        
        return True
        
    except ImportError as e:
        print(f"❌ EasyOCR import failed: {e}")
        print("   Solution: pip install easyocr")
        return False
    except Exception as e:
        print(f"❌ OCR initialization failed: {e}")
        return False

def test_floor_plan_analysis(image_path):
    """Test floor plan analysis with a specific image."""
    print(f"\n=== Testing Floor Plan Analysis ===")
    print(f"Image: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return
    
    analyzer = EnhancedFloorPlanAnalyzer()
    
    # Test OCR functionality
    ocr_test = analyzer.test_ocr_functionality(image_path)
    
    if ocr_test.get('success'):
        print("✅ OCR test successful!")
        print(f"   Total text found: {ocr_test['total_text_found']}")
        print(f"   High confidence text: {len(ocr_test['high_confidence_text'])}")
        
        if ocr_test['high_confidence_text']:
            print("   High confidence detections:")
            for item in ocr_test['high_confidence_text']:
                print(f"     '{item['text']}' (confidence: {item['confidence']:.2f})")
        
        if 'debug_image_saved' in ocr_test:
            print(f"   Debug image saved: {ocr_test['debug_image_saved']}")
    else:
        print(f"❌ OCR test failed: {ocr_test.get('error', 'Unknown error')}")
        if 'recommendation' in ocr_test:
            print(f"   Recommendation: {ocr_test['recommendation']}")
    
    # Test full analysis
    print("\n--- Full Analysis Test ---")
    try:
        result = analyzer.analyze_floor_plan_enhanced(image_path)
        
        if result.get('success'):
            print("✅ Floor plan analysis successful!")
            floors = result.get('floors', [])
            print(f"   Floors detected: {len(floors)}")
            
            total_rooms = 0
            for floor in floors:
                rooms = floor.get('rooms', [])
                total_rooms += len(rooms)
                print(f"   {floor['name']}: {len(rooms)} rooms")
                
                for room in rooms[:5]:  # Show first 5 rooms
                    print(f"     - {room['name']} ({room['type']})")
                
                if len(rooms) > 5:
                    print(f"     ... and {len(rooms) - 5} more rooms")
            
            print(f"   Total rooms: {total_rooms}")
            
        else:
            print(f"❌ Floor plan analysis failed: {result.get('error', 'Unknown error')}")
            if 'debug_info' in result:
                debug = result['debug_info']
                print(f"   OCR Available: {debug.get('ocr_available', 'Unknown')}")
                print(f"   OCR Reader Initialized: {debug.get('ocr_reader_initialized', 'Unknown')}")
                print(f"   Text Elements Found: {debug.get('text_elements_found', 'Unknown')}")
                print(f"   Message: {debug.get('message', 'No additional info')}")
    
    except Exception as e:
        print(f"❌ Analysis failed with exception: {e}")

def main():
    """Main test function."""
    print("Floor Plan OCR Debug Tool")
    print("=" * 50)
    
    # Test OCR installation
    if not test_ocr_installation():
        print("\n❌ OCR installation test failed. Please install EasyOCR first:")
        print("   pip install easyocr")
        return
    
    # Test with sample images if they exist
    test_images = [
        'media/property_floor_maps/sample_floor_plan.jpg',
        'test_images/floor_plan.jpg',
        'floor_plan.jpg'
    ]
    
    # Also check for any uploaded images
    media_dir = 'media/property_floor_maps'
    if os.path.exists(media_dir):
        for file in os.listdir(media_dir):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                test_images.append(os.path.join(media_dir, file))
    
    # Test with available images
    tested_any = False
    for image_path in test_images:
        if os.path.exists(image_path):
            test_floor_plan_analysis(image_path)
            tested_any = True
            break
    
    if not tested_any:
        print(f"\n⚠️  No test images found. Please provide a floor plan image path:")
        print("   Available locations to place test images:")
        for path in test_images[:3]:
            print(f"     - {path}")
        print("\n   Or run: python test_ocr_debug.py <path_to_your_image>")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test with provided image path
        image_path = sys.argv[1]
        test_ocr_installation()
        test_floor_plan_analysis(image_path)
    else:
        main()

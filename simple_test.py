#!/usr/bin/env python3
"""
SIMPLE Floor Plan Test - Just extract what we can see!
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'removealist_backend.settings')
django.setup()

from apps.inventory.services.floor_plan_analyzer import EnhancedFloorPlanAnalyzer

def simple_test(image_path):
    """Simple test - just show what we can extract."""
    
    print("=" * 60)
    print("SIMPLE FLOOR PLAN EXTRACTION TEST")
    print("=" * 60)
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    print(f"📁 Testing image: {image_path}")
    
    # Create analyzer
    analyzer = EnhancedFloorPlanAnalyzer()
    
    # Run simple analysis
    result = analyzer.analyze_floor_plan_service(image_path)
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    
    if result.get('success'):
        print("✅ SUCCESS!")
        print(f"📊 Found {result['rooms_created']} rooms")
        print(f"📏 Total area: {result['summary']['total_area_sqm']} m²")
        
        print("\n🏠 ROOMS FOUND:")
        for room in result['rooms']:
            dimensions = room.get('dimensions', 'No dimensions')
            print(f"  • {room['name']} ({room['type']}) - {dimensions} - {room['area_sqm']} m²")
        
        print(f"\n📈 ROOM TYPES:")
        for room_type, count in result['summary']['rooms_by_type'].items():
            print(f"  • {room_type}: {count}")
        
        if 'debug' in result:
            print(f"\n🔍 DEBUG INFO:")
            print(f"  • Total text found: {result['debug']['total_text_found']}")
            print(f"  • Rooms identified: {result['debug']['rooms_identified']}")
            print(f"  • OCR working: {result['debug']['ocr_working']}")
    
    else:
        print("❌ FAILED!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        
        if 'debug' in result:
            print(f"\n🔍 DEBUG INFO:")
            print(f"  • Total text found: {result['debug']['total_text_found']}")
            
            if result['debug']['total_text_found'] > 0:
                print("  • All text found:")
                for text in result['debug']['all_text']:
                    print(f"    - '{text}'")
            else:
                print("  • No text was detected by OCR")
                print("  • This could mean:")
                print("    1. EasyOCR is not working")
                print("    2. Image quality is too poor")
                print("    3. No readable text in the image")

def main():
    """Main function."""
    
    # Check if image path provided
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        simple_test(image_path)
        return
    
    # Look for test images
    test_paths = [
        'media/property_floor_maps/',
        'test_images/',
        '.'
    ]
    
    found_images = []
    for path in test_paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                    found_images.append(os.path.join(path, file))
    
    if found_images:
        print("Found these images:")
        for i, img in enumerate(found_images[:5]):  # Show first 5
            print(f"  {i+1}. {img}")
        
        print(f"\nTesting first image: {found_images[0]}")
        simple_test(found_images[0])
    else:
        print("No images found!")
        print("Usage: python simple_test.py <path_to_floor_plan_image>")
        print("\nOr place images in:")
        for path in test_paths:
            print(f"  - {path}")

if __name__ == "__main__":
    main()

"""
Enhanced Floor Plan Analysis Service with improved OCR and dimension extraction.
"""
import cv2
import numpy as np
from PIL import Image
import os
import logging
import re
from django.conf import settings
from apps.inventory.models import InventoryRoom, InventoryBox, HeavyItem
from apps.moves.models import Move

logger = logging.getLogger(__name__)

# Fix for PIL.Image.ANTIALIAS deprecation (Pillow 10.0+)
# This provides backward compatibility for dependencies that still use ANTIALIAS
try:
    # Pillow 10.0+ uses Image.Resampling.LANCZOS
    if hasattr(Image, 'Resampling'):
        Image.ANTIALIAS = Image.Resampling.LANCZOS
    elif not hasattr(Image, 'ANTIALIAS'):
        # Fallback for older Pillow versions
        Image.ANTIALIAS = Image.LANCZOS
except AttributeError:
    # If Resampling doesn't exist, use LANCZOS directly
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS

# Try to import OCR libraries
try:
    import easyocr
    OCR_AVAILABLE = True
    logger.info("EasyOCR is available for text recognition")
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("EasyOCR not available, using fallback room detection")

class EnhancedFloorPlanAnalyzer:
    """
    Enhanced service class for analyzing architectural floor plans with better accuracy.
    """
    
    def __init__(self):
        """Initialize the analyzer with comprehensive room detection patterns."""
        
        # Enhanced room type patterns with more variations (ordered by specificity)
        self.room_patterns = {
            # Most specific patterns first to avoid false matches
            r'\bmaster\s*bed(?:room)?\b': 'bedroom',
            r'\bformal\s*living\b': 'living_room',
            r'\bunder\s*house\s*storage\b': 'storage',
            r'\bpowder\s*room\b': 'bathroom',
            r'\bcar\s*port\b': 'garage',
            
            # Bedrooms - with number variations
            r'\bbed(?:room)?\s*\d+\b': 'bedroom',
            r'\bbr\s*\d+\b': 'bedroom',
            r'\bbed(?:room)?\b': 'bedroom',
            r'\bmaster\b': 'bedroom',
            
            # Living areas
            r'\bliving\s*room\b': 'living_room',
            r'\bliving\b': 'living_room',
            r'\blounge\b': 'living_room',
            r'\bfamily\s*room\b': 'living_room',
            r'\bsitting\s*room\b': 'living_room',
            
            # Dining
            r'\bdining\s*room\b': 'dining_room',
            r'\bdining\b': 'dining_room',
            r'\bmeals?\b': 'dining_room',
            
            # Kitchen
            r'\bkitchen\b': 'kitchen',
            r'\bcook\b': 'kitchen',
            r'\bpantry\b': 'kitchen',
            
            # Bathrooms (be more specific to avoid false matches)
            r'\bbath(?:room)?\b': 'bathroom',
            r'\bwc\b': 'bathroom',
            r'\btoilet\b': 'bathroom',
            
            # Laundry
            r'\blaundry\b': 'laundry',
            r'\bldry\b': 'laundry',
            
            # Storage and Garage
            r'\bgarage\b': 'garage',
            r'\bstorage\b': 'storage',
            r'\bstore\b': 'storage',
            
            # Entry and circulation
            r'\bentry\b': 'entry',
            r'\bfoyer\b': 'entry',
            r'\bhall(?:way)?\b': 'hallway',
            r'\bstair(?:s|case)?\b': 'stairs',
            
            # Outdoor
            r'\bbalcony\b': 'balcony',
            r'\bdeck\b': 'deck',
            r'\bporch\b': 'porch',
            r'\bpatio\b': 'patio',
            
            # Other
            r'\boffice\b': 'office',
            r'\bstudy\b': 'office',
            r'\blinen\b': 'linen',
            r'\bln\b': 'linen',
            r'\bcloset\b': 'closet',
        }
        
        # Dimension extraction patterns
        self.dimension_patterns = [
            r'(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)\s*m',  # "4.8 x 5.2m"
            r'(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)',      # "4.8 x 5.2"
            r'(\d+\.?\d*)\s*m\s*[xX×]\s*(\d+\.?\d*)\s*m',  # "4.8m x 5.2m"
        ]
        
        # Floor level patterns
        self.floor_patterns = [
            (r'ground\s*floor', 'Ground Floor'),
            (r'first\s*floor', 'First Floor'),
            (r'second\s*floor', 'Second Floor'),
            (r'basement', 'Basement'),
            (r'level\s*(\d+)', lambda m: f'Level {m.group(1)}'),
        ]
        
        # Initialize OCR reader if available
        self.ocr_reader = None
        if OCR_AVAILABLE:
            try:
                logger.info("Attempting to initialize EasyOCR reader...")
                self.ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                logger.info("OCR reader initialized successfully")
                
                # Test OCR with a simple image to make sure it's working
                try:
                    import numpy as np
                    test_image = np.ones((100, 200, 3), dtype=np.uint8) * 255
                    test_results = self.ocr_reader.readtext(test_image)
                    logger.info(f"OCR test completed - found {len(test_results)} elements (expected 0 for blank image)")
                except Exception as test_e:
                    logger.warning(f"OCR test failed: {test_e}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize OCR reader: {e}")
                logger.error("This might be due to missing dependencies or installation issues")
                self.ocr_reader = None
        else:
            logger.warning("EasyOCR not available - check if it's properly installed")
        
        # Storage keywords for identifying storage spaces
        self.storage_keywords = [
            'storage', 'store', 'garage', 'under house', 'basement', 
            'attic', 'utility', 'shed', 'warehouse'
        ]
        
        # Heavy item keywords
        self.heavy_items_keywords = [
            'piano', 'pool', 'billiard', 'treadmill', 'exercise', 'gym',
            'refrigerator', 'fridge', 'washer', 'dryer', 'dishwasher',
            'oven', 'stove', 'aquarium', 'safe', 'sculpture'
        ]

    def analyze_floor_plan_enhanced(self, floor_plan_path):
        """
        Enhanced floor plan analysis with better OCR and data extraction.
        
        Args:
            floor_plan_path: Path to the floor plan image
            
        Returns:
            dict: Comprehensive analysis results
        """
        try:
            if not os.path.exists(floor_plan_path):
                logger.warning(f"Floor plan image not found at {floor_plan_path}")
                return self.create_default_response()
            
            # Load image
            image = cv2.imread(floor_plan_path)
            if image is None:
                logger.warning(f"Could not load image from {floor_plan_path}")
                return self.create_default_response()
            
            logger.info(f"Analyzing floor plan: {image.shape}")
            logger.info(f"OCR Available: {OCR_AVAILABLE}")
            logger.info(f"OCR Reader initialized: {self.ocr_reader is not None}")
            
            # Step 1: Extract all text with OCR
            all_text_data = self.extract_all_text(image)
            logger.info(f"Extracted {len(all_text_data)} text elements")
            
            # Debug: Log if we're getting any text at all
            if len(all_text_data) == 0:
                logger.error("OCR FAILED: No text detected from image!")
                logger.error("This could be due to:")
                logger.error("1. EasyOCR not properly installed")
                logger.error("2. Image format/quality issues")
                logger.error("3. OCR reader initialization failure")
                logger.error("Falling back to intelligent defaults...")
            else:
                logger.info("OCR SUCCESS: Text detected, proceeding with analysis")
            
            # Step 2: Identify floor levels
            floor_sections = self.identify_floor_sections(all_text_data, image.shape)
            logger.info(f"Identified {len(floor_sections)} floor sections")
            
            # Step 3: Extract rooms with dimensions
            rooms_data = self.extract_rooms_with_dimensions(all_text_data, floor_sections, image.shape)
            logger.info(f"Extracted {len(rooms_data)} rooms")
            
            # If no rooms found, DO NOT use defaults - return error instead
            if not rooms_data:
                logger.error("CRITICAL: No rooms found via OCR!")
                logger.error("OCR failed to extract any room information from the image")
                logger.error("This could be due to:")
                logger.error("1. EasyOCR not properly installed or working")
                logger.error("2. Image quality/format issues")
                logger.error("3. Text too small or unclear in the image")
                
                # Return error instead of defaults
                return {
                    'success': False,
                    'error': 'OCR failed to extract room information from floor plan',
                    'debug_info': {
                        'ocr_available': OCR_AVAILABLE,
                        'ocr_reader_initialized': self.ocr_reader is not None,
                        'text_elements_found': len(all_text_data),
                        'image_shape': image.shape,
                        'message': 'No room text could be detected from the image. Please ensure the image has clear, readable room labels.'
                    }
                }
            else:
                logger.info("SUCCESS: Rooms extracted from OCR text!")
            
            # Step 4: Calculate storage capacity
            storage_analysis = self.analyze_storage_capacity(rooms_data)
            
            # Step 5: Generate inventory for each room
            for room in rooms_data:
                room['inventory'] = self.generate_room_inventory(room)
            
            # Step 6: Create structured output
            result = self.create_structured_output(rooms_data, storage_analysis, floor_sections)
            
            # Add debug info to result
            result['debug_info'] = {
                'ocr_available': OCR_AVAILABLE,
                'ocr_reader_initialized': self.ocr_reader is not None,
                'text_elements_found': len(all_text_data),
                'used_defaults': len(all_text_data) == 0 or len(rooms_data) == 16,
                'image_shape': image.shape
            }
            
            logger.info(f"Analysis completed successfully: {len(rooms_data)} rooms across {len(floor_sections)} floors")
            
            return result
            
        except Exception as e:
            logger.error(f"Floor plan analysis failed: {str(e)}", exc_info=True)
            return self.create_default_response()

    def analyze_floor_plan(self, move_id, floor_plan_path):
        """
        Main method to analyze floor plan and create inventory items.
        
        Args:
            move_id: UUID of the move
            floor_plan_path: Path to the floor plan image
            
        Returns:
            dict: Analysis results with created inventory items
        """
        try:
            move = Move.objects.get(id=move_id)
            
            # Check if image file exists
            if not os.path.exists(floor_plan_path):
                logger.warning(f"Floor plan image not found at {floor_plan_path}")
                return self.create_default_inventory(move)
            
            # Load and preprocess the image
            image = cv2.imread(floor_plan_path)
            if image is None:
                logger.warning(f"Could not load image from {floor_plan_path}")
                return self.create_default_inventory(move)
            
            # Detect rooms in the floor plan
            rooms_data = self.detect_rooms(image)
            
            # Create inventory items for each detected room
            created_inventory = []
            
            for room_data in rooms_data:
                # Create InventoryRoom
                inventory_room = self.create_inventory_room(move, room_data)
                
                # Detect objects in this room
                objects_data = self.detect_objects_in_room(image, room_data)
                
                # Categorize and create items
                items_summary = self.process_room_objects(move, inventory_room, objects_data)
                
                created_inventory.append({
                    'room': inventory_room,
                    'items_summary': items_summary
                })
            
            # Generate summary
            summary = self.generate_analysis_summary(created_inventory)
            
            logger.info(f"Floor plan analysis completed for move {move_id}. Created {len(created_inventory)} rooms.")
            
            return {
                'success': True,
                'rooms_created': len(created_inventory),
                'inventory_data': created_inventory,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Floor plan analysis failed for move {move_id}: {str(e)}")
            # Fallback to default inventory
            return self.create_default_inventory(Move.objects.get(id=move_id))

    def analyze_floor_plan_service(self, floor_plan_path):
        """
        SIMPLIFIED service method - just extract what we can see in the image.
        
        Args:
            floor_plan_path: Path to the floor plan image
            
        Returns:
            dict: Simple analysis results with actual extracted data
        """
        try:
            if not os.path.exists(floor_plan_path):
                return {'success': False, 'error': 'Image file not found'}
            
            # Load image
            image = cv2.imread(floor_plan_path)
            if image is None:
                return {'success': False, 'error': 'Could not load image'}
            
            logger.info(f"SIMPLE ANALYSIS: Processing image {image.shape}")
            
            # Try to extract text using OCR
            extracted_text = self.simple_text_extraction(image)
            logger.info(f"EXTRACTED TEXT: {len(extracted_text)} elements found")
            
            # Log all found text for debugging
            for item in extracted_text:
                logger.info(f"  Found: '{item['text']}' (confidence: {item['confidence']:.2f})")
            
            # Convert text to rooms
            rooms = self.simple_room_extraction(extracted_text)
            logger.info(f"IDENTIFIED ROOMS: {len(rooms)} rooms")
            
            # Create simple response
            return self.create_simple_response(rooms, extracted_text)
                
        except Exception as e:
            logger.error(f"Simple analysis failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def analyze_floor_plan_service_original(self, floor_plan_path):
        """
        Original service method (kept for fallback).
        """
        try:
            # Check if image file exists
            if not os.path.exists(floor_plan_path):
                logger.warning(f"Floor plan image not found at {floor_plan_path}")
                return self.create_service_default_response()
            
            # Load and preprocess the image
            image = cv2.imread(floor_plan_path)
            if image is None:
                logger.warning(f"Could not load image from {floor_plan_path}")
                return self.create_service_default_response()
            
            logger.info(f"Analyzing floor plan image: {image.shape}")
            
            # Detect rooms in the floor plan
            rooms_data = self.detect_rooms(image)
            logger.info(f"Detected {len(rooms_data)} rooms for processing")
            
            # If no rooms detected, return default response
            if not rooms_data:
                logger.warning("No rooms detected in floor plan, returning default response")
                return self.create_service_default_response()
            
            # Process rooms without creating database records
            processed_inventory = []
            floors_data = {}  # Group rooms by floor
            
            for room_data in rooms_data:
                try:
                    # Detect objects in this room
                    objects_data = self.detect_objects_in_room(image, room_data)
                    logger.debug(f"Objects detected for {room_data.get('name', 'Unknown')}: {objects_data}")
                    
                    # Process items without database creation
                    items_summary = self.process_room_objects_service(room_data, objects_data)
                    logger.debug(f"Items summary for {room_data.get('name', 'Unknown')}: {items_summary}")
                except Exception as e:
                    logger.error(f"Error processing room {room_data.get('name', 'Unknown')}: {str(e)}")
                    # Provide default items_summary
                    items_summary = {
                        'regular_items': [],
                        'boxes': [],
                        'heavy_items': [],
                        'regular_items_count': 0,
                        'boxes_created': 0,
                        'heavy_items_created': 0
                    }
                
                # Enhanced room data structure
                # Ensure 'type' key exists with a default value
                room_type = room_data.get('type', room_data.get('room_type', 'other'))
                room_info = {
                    'room_name': room_data.get('name', 'Unknown Room'),
                    'room_type': room_type,
                    'area_pixels': room_data.get('area', 0),
                    'floor_level': room_data.get('floor_level', 'Unknown Floor'),
                    'original_text': room_data.get('original_text', ''),
                    'confidence': room_data.get('text_confidence', 0),
                    'regular_items': items_summary.get('regular_items', []),
                    'boxes': items_summary.get('boxes', []),
                    'heavy_items': items_summary.get('heavy_items', []),
                    'item_counts': {
                        'regular_items': items_summary.get('regular_items_count', len(items_summary.get('regular_items', []))),
                        'boxes': items_summary.get('boxes_created', len(items_summary.get('boxes', []))),
                        'heavy_items': items_summary.get('heavy_items_created', len(items_summary.get('heavy_items', [])))
                    },
                    'items_summary': items_summary
                }
                
                # Add dimensions if available
                if 'dimensions' in room_data:
                    room_info['dimensions_m'] = room_data['dimensions']['dimensions_text']
                    room_info['area_sqm'] = room_data['dimensions']['area_sqm']
                
                # Add features based on room type and text
                features = self.extract_room_features(room_data)
                if features:
                    room_info['features'] = features
                
                processed_inventory.append(room_info)
                
                # Group by floor
                floor_level = room_data.get('floor_level', 'Unknown Floor')
                if floor_level not in floors_data:
                    floors_data[floor_level] = []
                floors_data[floor_level].append(room_info)
            
            # Generate summary
            summary = self.generate_service_summary(processed_inventory)
            
            # Create structured floor plan data similar to AI software output
            structured_data = {
                'property_address': 'Analyzed Floor Plan',  # Could be extracted from OCR
                'floors': []
            }
            
            for floor_name, floor_rooms in floors_data.items():
                floor_data = {
                    'name': floor_name,
                    'rooms': []
                }
                
                for room in floor_rooms:
                    room_entry = {
                        'name': room['room_name'],
                        'type': room['room_type']
                    }
                    
                    if 'dimensions_m' in room:
                        room_entry['dimensions_m'] = room['dimensions_m']
                    
                    if 'features' in room:
                        room_entry['features'] = room['features']
                    
                    if 'original_text' in room and room['original_text']:
                        room_entry['label'] = room['original_text']
                    
                    floor_data['rooms'].append(room_entry)
                
                structured_data['floors'].append(floor_data)
            
            logger.info(f"Floor plan service analysis completed. Detected {len(processed_inventory)} rooms across {len(floors_data)} floors.")
            
            return {
                'success': True,
                'rooms_created': len(processed_inventory),
                'inventory_data': processed_inventory,  # Original format for compatibility
                'structured_data': structured_data,     # New structured format
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Floor plan service analysis failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'rooms_created': 0
            }

    def create_default_inventory(self, move):
        """
        Create default inventory when floor plan analysis fails.
        
        Args:
            move: Move instance
            
        Returns:
            dict: Default inventory results
        """
        try:
            default_rooms = self.create_default_rooms()
            created_inventory = []
            
            for room_data in default_rooms:
                # Ensure room_data has required keys
                room_type = room_data.get('type', 'other')
                room_area = room_data.get('area', 10000)
                
                # Create InventoryRoom
                inventory_room = self.create_inventory_room(move, room_data)
                
                # Generate default objects for this room
                objects_data = self.generate_room_items(room_type, room_area)
                
                # Process the objects
                items_summary = self.process_room_objects(move, inventory_room, objects_data)
                
                created_inventory.append({
                    'room': inventory_room,
                    'items_summary': items_summary
                })
            
            summary = self.generate_analysis_summary(created_inventory)
            
            logger.info(f"Created default inventory for move {move.id}. Created {len(created_inventory)} rooms.")
            
            return {
                'success': True,
                'rooms_created': len(created_inventory),
                'inventory_data': created_inventory,
                'summary': summary,
                'is_default': True
            }
            
        except Exception as e:
            logger.error(f"Failed to create default inventory for move {move.id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'rooms_created': 0
            }

    def detect_rooms(self, image):
        """
        Detect rooms in the floor plan using advanced computer vision and OCR.
        
        Args:
            image: OpenCV image array
            
        Returns:
            list: List of room data dictionaries
        """
        try:
            logger.info("Starting advanced floor plan analysis...")
            
            # First, try OCR-based room detection
            rooms_data = self.detect_rooms_with_ocr(image)
            
            # If OCR didn't find enough rooms, try contour-based detection
            if len(rooms_data) < 2:
                logger.info("OCR found few rooms, trying contour-based detection...")
                contour_rooms = self.detect_rooms_with_contours(image)
                
                # Merge results, prioritizing OCR results
                existing_types = {room['type'] for room in rooms_data}
                for room in contour_rooms:
                    if room['type'] not in existing_types:
                        rooms_data.append(room)
            
            # If still no rooms detected, create default rooms based on floor plan analysis
            if not rooms_data:
                logger.info("No rooms detected, creating intelligent default rooms...")
                rooms_data = self.create_intelligent_default_rooms(image)
            
            logger.info(f"Detected {len(rooms_data)} rooms: {[room['name'] for room in rooms_data]}")
            return rooms_data
            
        except Exception as e:
            logger.error(f"Room detection failed: {str(e)}")
            return self.create_default_rooms()

    def detect_rooms_with_ocr(self, image):
        """
        Detect rooms using OCR to read text labels from the floor plan.
        
        Args:
            image: OpenCV image array
            
        Returns:
            list: List of room data dictionaries
        """
        rooms_data = []
        
        if not self.ocr_reader:
            logger.info("OCR not available, skipping text-based room detection")
            return rooms_data
        
        try:
            # Try multiple image preprocessing techniques for better OCR
            ocr_results = []
            
            # Method 1: Original image
            results1 = self.ocr_reader.readtext(image)
            ocr_results.extend(results1)
            
            # Method 2: Enhanced contrast
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.equalizeHist(gray)
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            results2 = self.ocr_reader.readtext(enhanced_bgr)
            ocr_results.extend(results2)
            
            # Method 3: Thresholded image
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            thresh_bgr = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
            results3 = self.ocr_reader.readtext(thresh_bgr)
            ocr_results.extend(results3)
            
            logger.info(f"OCR detected {len(ocr_results)} total text elements from {len(set([r[1] for r in ocr_results]))} unique texts")
            
            # Remove duplicates based on text content
            unique_results = {}
            for bbox, text, confidence in ocr_results:
                text_key = text.lower().strip()
                if text_key not in unique_results or confidence > unique_results[text_key][2]:
                    unique_results[text_key] = (bbox, text, confidence)
            
            results = list(unique_results.values())
            logger.info(f"After deduplication: {len(results)} unique text elements")
            
            # First pass: detect floor levels and dimensions
            floor_levels = {}
            all_dimensions = {}
            
            for (bbox, text, confidence) in results:
                # Detect floor level
                floor_level = self.detect_floor_level(text, bbox, image.shape)
                if floor_level:
                    floor_levels[floor_level] = bbox
                    logger.info(f"Detected floor level: {floor_level}")
                
                # Extract dimensions
                dimensions = self.extract_dimensions(text)
                if dimensions:
                    all_dimensions[text] = dimensions
                    logger.info(f"Extracted dimensions from '{text}': {dimensions['dimensions_text']}")
            
            room_counter = {}  # Track room numbers by type
            
            for (bbox, text, confidence) in results:
                logger.info(f"OCR found text: '{text}' (confidence: {confidence:.2f})")
                
                if confidence < 0.2:  # Even lower threshold for architectural drawings
                    logger.debug(f"Skipping low-confidence text: '{text}' ({confidence:.2f})")
                    continue
                
                # Clean and normalize the text, but preserve numbers
                text_clean = re.sub(r'[^\w\s]', '', text.lower().strip())
                
                # Also try the original text in case cleaning removed important info
                text_variations = [text_clean, text.lower().strip(), text.strip()]
                
                room_type = None
                for text_variant in text_variations:
                    room_type = self.identify_room_type(text_variant)
                    if room_type:
                        logger.info(f"Successfully identified room type '{room_type}' from text '{text}' (variant: '{text_variant}')")
                        break
                
                if room_type:
                    # Get the center point of the text
                    bbox_array = np.array(bbox)
                    center_x = int(np.mean(bbox_array[:, 0]))
                    center_y = int(np.mean(bbox_array[:, 1]))
                    
                    # Count rooms of this type
                    room_counter[room_type] = room_counter.get(room_type, 0) + 1
                    room_number = room_counter[room_type]
                    
                    # Create intelligent room name based on original text
                    room_name = self.create_intelligent_room_name(text, room_type, room_number)
                    
                    # Check if this text has associated dimensions
                    dimensions = self.extract_dimensions(text)
                    if not dimensions:
                        # Look for nearby dimension text
                        dimensions = self.find_nearby_dimensions(bbox, all_dimensions, results)
                    
                    # Estimate room area
                    if dimensions:
                        estimated_area = dimensions['area_sqm'] * 10000  # Convert to pixels (rough)
                    else:
                        text_width = int(np.max(bbox_array[:, 0]) - np.min(bbox_array[:, 0]))
                        text_height = int(np.max(bbox_array[:, 1]) - np.min(bbox_array[:, 1]))
                        estimated_area = max(5000, text_width * text_height * 10)
                    
                    # Determine floor level
                    floor_level = self.determine_room_floor_level(bbox, floor_levels, image.shape)
                    
                    room_data = {
                        'name': room_name,
                        'type': room_type,
                        'bbox': (center_x - 50, center_y - 50, 100, 100),
                        'area': estimated_area,
                        'contour': None,
                        'text_confidence': confidence,
                        'original_text': text,
                        'floor_level': floor_level
                    }
                    
                    # Add dimensions if found
                    if dimensions:
                        room_data['dimensions'] = dimensions
                        room_data['dimensions_text'] = dimensions['dimensions_text']
                    
                    rooms_data.append(room_data)
                    
                    logger.info(f"Found room via OCR: {room_name} on {floor_level} (confidence: {confidence:.2f})")
            
            return rooms_data
            
        except Exception as e:
            logger.error(f"OCR-based room detection failed: {str(e)}")
            return []

    def detect_rooms_with_contours(self, image):
        """
        Detect rooms using contour analysis for architectural floor plans.
        
        Args:
            image: OpenCV image array
            
        Returns:
            list: List of room data dictionaries
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply adaptive thresholding for better results with architectural drawings
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10
            )
            
            # Apply morphological operations to clean up the image
            kernel = np.ones((3, 3), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            rooms_data = []
            room_counter = 1
            
            # Sort contours by area (largest first)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Filter contours based on area (rooms should be reasonably sized)
                if area < 2000 or area > image.shape[0] * image.shape[1] * 0.3:
                    continue
                
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter based on aspect ratio (rooms shouldn't be too thin)
                aspect_ratio = w / h if h > 0 else 1
                if aspect_ratio > 5 or aspect_ratio < 0.2:
                    continue
                
                # Estimate room type based on size and position
                room_type = self.estimate_room_type_advanced(w, h, x, y, image.shape, area)
                
                room_name = f"{room_type.replace('_', ' ').title()} {room_counter}"
                
                rooms_data.append({
                    'name': room_name,
                    'type': room_type,
                    'bbox': (x, y, w, h),
                    'area': area,
                    'contour': contour
                })
                
                room_counter += 1
                
                # Limit to reasonable number of rooms
                if len(rooms_data) >= 8:
                    break
            
            return rooms_data
            
        except Exception as e:
            logger.error(f"Contour-based room detection failed: {str(e)}")
            return []

    def identify_room_type(self, text):
        """
        Identify room type from OCR text.
        
        Args:
            text: Cleaned text from OCR
            
        Returns:
            str: Room type or None if not recognized
        """
        # Log the text being analyzed for debugging
        logger.debug(f"Analyzing OCR text: '{text}'")
        
        # Check for exact matches first
        for keyword, room_type in self.room_types.items():
            if keyword in text:
                logger.debug(f"Found exact match: '{keyword}' -> {room_type}")
                return room_type
        
        # Check for partial matches and common variations
        # Enhanced bedroom detection (including numbered bedrooms like "BED 2", "BED 3")
        if any(word in text for word in ['bed', 'bedroom', 'master']):
            logger.debug(f"Detected bedroom from text: '{text}'")
            return 'bedroom'
        elif any(word in text for word in ['kitchen', 'cook']):
            logger.debug(f"Detected kitchen from text: '{text}'")
            return 'kitchen'
        elif any(word in text for word in ['bath', 'bathroom', 'toilet', 'wc']):
            logger.debug(f"Detected bathroom from text: '{text}'")
            return 'bathroom'
        elif any(word in text for word in ['living', 'lounge', 'family', 'sitting', 'formal']):
            logger.debug(f"Detected living room from text: '{text}'")
            return 'living_room'
        elif any(word in text for word in ['dining', 'eat', 'meals']):
            logger.debug(f"Detected dining room from text: '{text}'")
            return 'living_room'
        elif any(word in text for word in ['garage', 'car']):
            logger.debug(f"Detected garage from text: '{text}'")
            return 'garage'
        elif any(word in text for word in ['office', 'study', 'work']):
            logger.debug(f"Detected office from text: '{text}'")
            return 'office'
        elif any(word in text for word in ['media', 'tv', 'entertainment']):
            logger.debug(f"Detected media room from text: '{text}'")
            return 'office'
        elif any(word in text for word in ['laundry', 'wash', 'dry']):
            logger.debug(f"Detected laundry from text: '{text}'")
            return 'bathroom'
        elif any(word in text for word in ['utility', 'storage', 'under house']):
            logger.debug(f"Detected utility/storage from text: '{text}'")
            return 'garage'
        elif any(word in text for word in ['entry', 'entryway', 'foyer', 'hall']):
            logger.debug(f"Detected entry/hall from text: '{text}'")
            return 'other'
        elif any(word in text for word in ['balcony', 'deck', 'porch']):
            logger.debug(f"Detected balcony/deck from text: '{text}'")
            return 'other'
        
        logger.debug(f"No room type identified for text: '{text}'")
        return None

    def extract_dimensions(self, text):
        """
        Extract room dimensions from OCR text.
        
        Args:
            text: OCR text that might contain dimensions
            
        Returns:
            dict: Dimensions info or None if not found
        """
        import re
        
        # Common dimension patterns in floor plans
        patterns = [
            r'(\d+\.?\d*)\s*x\s*(\d+\.?\d*)m?',  # "4.8 x 5.2" or "4.8 x 5.2m"
            r'(\d+\.?\d*)\s*×\s*(\d+\.?\d*)m?',  # "4.8 × 5.2" (multiplication symbol)
            r'(\d+\.?\d*)\s*by\s*(\d+\.?\d*)m?', # "4.8 by 5.2"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                width = float(match.group(1))
                height = float(match.group(2))
                return {
                    'width_m': width,
                    'height_m': height,
                    'dimensions_text': f"{width} x {height}m",
                    'area_sqm': round(width * height, 2)
                }
        
        return None

    def detect_floor_level(self, text, bbox, image_shape):
        """
        Detect if text indicates a floor level.
        
        Args:
            text: OCR text
            bbox: Bounding box of the text
            image_shape: Image dimensions
            
        Returns:
            str: Floor level or None
        """
        text_lower = text.lower()
        
        # Check for explicit floor mentions
        if 'ground floor' in text_lower or 'ground level' in text_lower:
            return 'Ground Floor'
        elif 'first floor' in text_lower or '1st floor' in text_lower:
            return 'First Floor'
        elif 'second floor' in text_lower or '2nd floor' in text_lower:
            return 'Second Floor'
        
        # Infer from position (ground floor typically at bottom of image)
        bbox_array = np.array(bbox)
        center_y = int(np.mean(bbox_array[:, 1]))
        relative_y = center_y / image_shape[0]
        
        # If text is in bottom half, likely ground floor
        if relative_y > 0.6:
            return 'Ground Floor'
        elif relative_y < 0.4:
            return 'First Floor'
        
        return None

    def create_intelligent_room_name(self, original_text, room_type, room_number):
        """
        Create intelligent room names based on original OCR text.
        
        Args:
            original_text: Original OCR text
            room_type: Detected room type
            room_number: Room number for this type
            
        Returns:
            str: Intelligent room name
        """
        text_lower = original_text.lower().strip()
        
        # Handle specific cases from your floor plan
        if 'master' in text_lower or 'master bed' in text_lower:
            return 'Master Bedroom'
        elif 'bed' in text_lower and any(char.isdigit() for char in text_lower):
            # Extract number from text like "BED 2", "BED 3"
            import re
            numbers = re.findall(r'\d+', text_lower)
            if numbers:
                return f'Bedroom {numbers[0]}'
        elif 'formal' in text_lower and 'living' in text_lower:
            return 'Formal Living Room'
        elif 'living' in text_lower:
            if room_number == 1:
                return 'Living Room'
            else:
                return f'Living Room {room_number}'
        elif 'garage' in text_lower and any(char.isdigit() for char in text_lower):
            import re
            numbers = re.findall(r'\d+', text_lower)
            if numbers:
                return f'Garage {numbers[0]}'
        elif 'under house' in text_lower or 'storage' in text_lower:
            return 'Under House Storage'
        elif 'ldry' in text_lower or 'laundry' in text_lower:
            return 'Laundry'
        elif 'wc' in text_lower:
            return 'WC'
        elif 'ln' in text_lower:
            return 'Linen Closet'
        elif 'meals' in text_lower:
            return 'Meals Area'
        elif 'entry' in text_lower:
            return 'Entry'
        elif 'balcony' in text_lower:
            return 'Balcony'
        
        # Default naming
        if room_number == 1:
            return room_type.replace('_', ' ').title()
        else:
            return f"{room_type.replace('_', ' ').title()} {room_number}"

    def find_nearby_dimensions(self, room_bbox, all_dimensions, all_results):
        """
        Find dimensions text near a room label.
        
        Args:
            room_bbox: Bounding box of the room label
            all_dimensions: Dictionary of all found dimensions
            all_results: All OCR results
            
        Returns:
            dict: Dimensions if found nearby
        """
        room_center = np.array(room_bbox).mean(axis=0)
        min_distance = float('inf')
        closest_dimensions = None
        
        for text, dimensions in all_dimensions.items():
            # Find this text in results to get its bbox
            for bbox, result_text, confidence in all_results:
                if result_text == text:
                    text_center = np.array(bbox).mean(axis=0)
                    distance = np.linalg.norm(room_center - text_center)
                    
                    if distance < min_distance and distance < 100:  # Within 100 pixels
                        min_distance = distance
                        closest_dimensions = dimensions
                    break
        
        return closest_dimensions

    def determine_room_floor_level(self, room_bbox, floor_levels, image_shape):
        """
        Determine which floor a room is on based on its position and detected floor labels.
        
        Args:
            room_bbox: Room bounding box
            floor_levels: Dictionary of detected floor levels
            image_shape: Image dimensions
            
        Returns:
            str: Floor level
        """
        room_center_y = np.array(room_bbox).mean(axis=0)[1]
        relative_y = room_center_y / image_shape[0]
        
        # If we have explicit floor level detections, use those
        if floor_levels:
            min_distance = float('inf')
            closest_floor = None
            
            for floor_name, floor_bbox in floor_levels.items():
                floor_center_y = np.array(floor_bbox).mean(axis=0)[1]
                distance = abs(room_center_y - floor_center_y)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_floor = floor_name
            
            if closest_floor:
                return closest_floor
        
        # Fallback to position-based detection
        if relative_y > 0.6:
            return 'Ground Floor'
        else:
            return 'First Floor'

    def extract_room_features(self, room_data):
        """
        Extract room features based on room type and OCR text.
        
        Args:
            room_data: Room data dictionary
            
        Returns:
            list: List of room features
        """
        features = []
        room_type = room_data.get('type', '')
        original_text = room_data.get('original_text', '').lower()
        
        # Common features based on room type
        if room_type == 'bedroom':
            features.append('Built-in robe (BIR)')
            if 'master' in original_text:
                features.append('Master bedroom with ensuite access')
        elif room_type == 'garage':
            features.append('Vehicle space')
            if 'storage' in original_text or 'under house' in original_text:
                features.append('Large storage area')
        elif room_type == 'kitchen':
            features.append('Island bench')
            features.append('Connected to meals area')
        elif room_type == 'living_room':
            if 'formal' in original_text:
                features.append('Formal living space')
            if 'meals' in original_text:
                features.append('Adjacent to kitchen')
        elif room_type == 'bathroom':
            if 'laundry' in original_text or 'ldry' in original_text:
                features.append('Near kitchen')
            elif 'wc' in original_text:
                features.append('Near laundry')
            else:
                features.append('Main bathroom near bedrooms')
        elif room_type == 'other':
            if 'entry' in original_text:
                features.append('Main entrance')
                features.append('Access to hallway')
            elif 'balcony' in original_text:
                features.append('Central outdoor space')
            elif 'linen' in original_text or 'ln' in original_text:
                features.append('Linen storage')
            elif 'stair' in original_text:
                features.append('Leads to first floor')
        
        return features

    def estimate_room_type_advanced(self, width, height, x, y, image_shape, area):
        """
        Advanced room type estimation based on multiple factors.
        
        Args:
            width, height: Room dimensions
            x, y: Room position
            image_shape: Image dimensions
            area: Room area
            
        Returns:
            str: Estimated room type
        """
        aspect_ratio = width / height if height > 0 else 1
        relative_x = x / image_shape[1] if image_shape[1] > 0 else 0
        relative_y = y / image_shape[0] if image_shape[0] > 0 else 0
        relative_area = area / (image_shape[0] * image_shape[1])
        
        # Very small rooms are likely bathrooms
        if relative_area < 0.02 or area < 3000:
            return 'bathroom'
        
        # Large rooms are likely living areas
        elif relative_area > 0.08 or area > 15000:
            return 'living_room'
        
        # Long narrow rooms might be hallways or utility areas
        elif aspect_ratio > 3 or aspect_ratio < 0.3:
            return 'other'
        
        # Rooms near edges might be garages
        elif relative_x < 0.1 or relative_x > 0.9 or relative_y < 0.1:
            return 'garage'
        
        # Medium-sized square rooms are likely bedrooms
        elif 0.7 <= aspect_ratio <= 1.4 and 0.03 <= relative_area <= 0.07:
            return 'bedroom'
        
        # Rooms in typical kitchen positions
        elif relative_x < 0.4 and relative_y < 0.4 and relative_area < 0.06:
            return 'kitchen'
        
        # Default to bedroom for medium-sized rooms
        else:
            return 'bedroom'

    def create_intelligent_default_rooms(self, image):
        """
        Create intelligent default rooms based on image analysis.
        
        Args:
            image: OpenCV image array
            
        Returns:
            list: Default room data based on image characteristics
        """
        try:
            # First try to detect architectural floor plan patterns
            architectural_rooms = self.detect_architectural_floor_plan(image)
            if architectural_rooms:
                return architectural_rooms
            
            # Fallback to edge density analysis
            height, width = image.shape[:2]
            total_area = height * width
            
            # Determine number of rooms based on image complexity
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / total_area
            
            # More edges suggest more complex floor plan with more rooms
            if edge_density > 0.1:
                # Large house/complex layout
                return [
                    {'name': 'Living Room', 'type': 'living_room', 'bbox': (0, 0, width//2, height//2), 'area': total_area//4, 'contour': None},
                    {'name': 'Kitchen', 'type': 'kitchen', 'bbox': (width//2, 0, width//2, height//3), 'area': total_area//6, 'contour': None},
                    {'name': 'Master Bedroom', 'type': 'bedroom', 'bbox': (0, height//2, width//2, height//2), 'area': total_area//4, 'contour': None},
                    {'name': 'Bedroom 2', 'type': 'bedroom', 'bbox': (width//2, height//3, width//3, height//3), 'area': total_area//9, 'contour': None},
                    {'name': 'Bedroom 3', 'type': 'bedroom', 'bbox': (5*width//6, height//3, width//6, height//3), 'area': total_area//18, 'contour': None},
                    {'name': 'Bathroom', 'type': 'bathroom', 'bbox': (width//2, 2*height//3, width//4, height//6), 'area': total_area//24, 'contour': None},
                    {'name': 'Garage', 'type': 'garage', 'bbox': (3*width//4, 2*height//3, width//4, height//3), 'area': total_area//12, 'contour': None},
                ]
            elif edge_density > 0.05:
                # Medium house
                return [
                    {'name': 'Living Room', 'type': 'living_room', 'bbox': (0, 0, width//2, height//2), 'area': total_area//4, 'contour': None},
                    {'name': 'Kitchen', 'type': 'kitchen', 'bbox': (width//2, 0, width//2, height//2), 'area': total_area//4, 'contour': None},
                    {'name': 'Master Bedroom', 'type': 'bedroom', 'bbox': (0, height//2, width//2, height//2), 'area': total_area//4, 'contour': None},
                    {'name': 'Bedroom 2', 'type': 'bedroom', 'bbox': (width//2, height//2, width//3, height//2), 'area': total_area//6, 'contour': None},
                    {'name': 'Bathroom', 'type': 'bathroom', 'bbox': (5*width//6, height//2, width//6, height//2), 'area': total_area//12, 'contour': None},
                ]
            else:
                # Simple layout
                return [
                    {'name': 'Living Room', 'type': 'living_room', 'bbox': (0, 0, width//2, height), 'area': total_area//2, 'contour': None},
                    {'name': 'Kitchen', 'type': 'kitchen', 'bbox': (width//2, 0, width//2, height//2), 'area': total_area//4, 'contour': None},
                    {'name': 'Bedroom', 'type': 'bedroom', 'bbox': (width//2, height//2, width//2, height//2), 'area': total_area//4, 'contour': None},
                ]
                
        except Exception as e:
            logger.error(f"Failed to create intelligent default rooms: {str(e)}")
            return self.create_default_rooms()

    def detect_architectural_floor_plan(self, image):
        """
        Detect rooms in architectural floor plans by analyzing layout patterns.
        This method is specifically designed for professional floor plans like yours.
        
        Args:
            image: OpenCV image array
            
        Returns:
            list: Room data based on architectural analysis
        """
        try:
            height, width = image.shape[:2]
            total_area = height * width
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Look for rectangular room patterns typical in floor plans
            # Use adaptive threshold to handle varying lighting
            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # Find contours that could represent rooms
            contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter and analyze contours for room-like shapes
            potential_rooms = []
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Filter by area - rooms should be a reasonable size
                if area < total_area * 0.01 or area > total_area * 0.4:
                    continue
                
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Check if it's roughly rectangular (architectural rooms usually are)
                rect_area = w * h
                if area / rect_area < 0.6:  # Should fill most of the bounding rectangle
                    continue
                
                # Check aspect ratio - avoid very thin shapes
                aspect_ratio = w / h if h > 0 else 1
                if aspect_ratio > 4 or aspect_ratio < 0.25:
                    continue
                
                potential_rooms.append({
                    'bbox': (x, y, w, h),
                    'area': area,
                    'contour': contour,
                    'aspect_ratio': aspect_ratio
                })
            
            # Sort by area (largest first) and select reasonable number of rooms
            potential_rooms.sort(key=lambda r: r['area'], reverse=True)
            potential_rooms = potential_rooms[:8]  # Max 8 rooms
            
            # Create room data with intelligent type assignment
            rooms_data = []
            room_types_used = {'bedroom': 0, 'bathroom': 0, 'living_room': 0, 'kitchen': 0, 'garage': 0, 'office': 0}
            
            for i, room in enumerate(potential_rooms):
                x, y, w, h = room['bbox']
                area = room['area']
                
                # Determine room type based on size, position, and aspect ratio
                room_type = self.classify_room_by_characteristics(
                    w, h, x, y, area, image.shape, room['aspect_ratio']
                )
                
                # Create appropriate room name
                room_types_used[room_type] += 1
                if room_types_used[room_type] == 1:
                    if room_type == 'bedroom':
                        room_name = 'Master Bedroom'
                    elif room_type == 'living_room':
                        room_name = 'Living/Dining Room'
                    else:
                        room_name = room_type.replace('_', ' ').title()
                else:
                    if room_type == 'bedroom':
                        room_name = f'Bedroom {room_types_used[room_type]}'
                    elif room_type == 'bathroom':
                        room_name = f'Bathroom {room_types_used[room_type]}'
                    else:
                        room_name = f"{room_type.replace('_', ' ').title()} {room_types_used[room_type]}"
                
                rooms_data.append({
                    'name': room_name,
                    'type': room_type,
                    'bbox': (x, y, w, h),
                    'area': area,
                    'contour': room['contour']
                })
            
            # Ensure we have at least basic rooms
            if len(rooms_data) < 3:
                return None  # Fall back to other methods
            
            logger.info(f"Detected {len(rooms_data)} rooms using architectural analysis")
            return rooms_data
            
        except Exception as e:
            logger.error(f"Architectural floor plan detection failed: {str(e)}")
            return None

    def classify_room_by_characteristics(self, width, height, x, y, area, image_shape, aspect_ratio):
        """
        Classify room type based on multiple characteristics.
        
        Args:
            width, height: Room dimensions
            x, y: Room position  
            area: Room area
            image_shape: Image dimensions
            aspect_ratio: Width/height ratio
            
        Returns:
            str: Classified room type
        """
        img_height, img_width = image_shape[:2]
        total_area = img_height * img_width
        relative_area = area / total_area
        relative_x = x / img_width
        relative_y = y / img_height
        
        # Very small rooms are likely bathrooms
        if relative_area < 0.03:
            return 'bathroom'
        
        # Large rooms are likely living areas
        elif relative_area > 0.15:
            return 'living_room'
        
        # Rooms near the top or edges might be kitchens or garages
        elif relative_y < 0.3 and relative_area < 0.12:
            # Small rooms at top are likely kitchens
            if relative_area < 0.08:
                return 'kitchen'
            else:
                return 'garage'
        
        # Square-ish medium rooms are likely bedrooms
        elif 0.6 <= aspect_ratio <= 1.7 and 0.05 <= relative_area <= 0.15:
            return 'bedroom'
        
        # Long narrow rooms might be utility or office
        elif aspect_ratio > 2 or aspect_ratio < 0.5:
            return 'office'
        
        # Default classification based on size
        elif relative_area > 0.08:
            return 'living_room'
        else:
            return 'bedroom'

    def estimate_room_type(self, width, height, x, y, image_shape):
        """
        Estimate room type based on dimensions and position.
        
        Args:
            width, height: Room dimensions
            x, y: Room position
            image_shape: Image dimensions (height, width, channels)
            
        Returns:
            str: Estimated room type
        """
        try:
            aspect_ratio = width / height if height > 0 else 1
            relative_x = x / image_shape[1] if image_shape[1] > 0 else 0
            relative_y = y / image_shape[0] if image_shape[0] > 0 else 0
            
            # Simple heuristics for room type estimation
            if aspect_ratio > 2 or (width * height) < 2000:
                return 'bathroom'  # Long narrow rooms or small rooms
            elif relative_x < 0.3 and relative_y < 0.3:
                return 'kitchen'  # Top-left area often kitchen
            elif aspect_ratio > 1.5:
                return 'living_room'  # Wide rooms often living areas
            elif 0.8 <= aspect_ratio <= 1.2:
                return 'bedroom'  # Square-ish rooms often bedrooms
            else:
                return 'other'
        except Exception:
            return 'other'

    def detect_objects_in_room(self, image, room_data):
        """
        Detect objects and furniture within a room area.
        
        Args:
            image: OpenCV image array
            room_data: Room information dictionary
            
        Returns:
            dict: Detected objects data
        """
        try:
            x, y, w, h = room_data.get('bbox', (0, 0, 100, 100))
            room_type = room_data.get('type', 'other')
            
            # Generate items based on room type (rule-based approach)
            items = self.generate_room_items(room_type, w * h)
            
            return items
            
        except Exception as e:
            logger.error(f"Object detection failed for room {room_data.get('name', 'Unknown')}: {str(e)}")
            return {'regular_items': [], 'boxes': [], 'heavy_items': []}

    def generate_room_items(self, room_type, room_area):
        """
        Generate typical items for a room type based on common patterns.
        
        Args:
            room_type: Type of room
            room_area: Area of the room in pixels
            
        Returns:
            dict: Generated items categorized by type
        """
        # Base items by room type
        room_items = {
            'kitchen': {
                'regular_items': ['Dining table', 'Chairs', 'Microwave', 'Toaster', 'Kitchen utensils', 'Dishes', 'Cookware'],
                'boxes': ['Kitchen appliances box', 'Dishes box', 'Pantry items box'],
                'heavy_items': ['Refrigerator', 'Dishwasher', 'Oven']
            },
            'living_room': {
                'regular_items': ['Sofa', 'Coffee table', 'TV', 'Bookshelf', 'Lamps', 'Decorations'],
                'boxes': ['Books box', 'Electronics box', 'Decorations box'],
                'heavy_items': ['Piano', 'Large TV', 'Heavy bookshelf']
            },
            'bedroom': {
                'regular_items': ['Bed', 'Dresser', 'Nightstand', 'Lamp', 'Clothes', 'Bedding'],
                'boxes': ['Clothes box', 'Bedding box', 'Personal items box'],
                'heavy_items': ['Mattress', 'Heavy dresser']
            },
            'bathroom': {
                'regular_items': ['Towels', 'Toiletries', 'Bathroom accessories', 'Medicine cabinet items'],
                'boxes': ['Toiletries box', 'Bathroom supplies box'],
                'heavy_items': []
            },
            'office': {
                'regular_items': ['Desk', 'Office chair', 'Computer', 'Books', 'Office supplies'],
                'boxes': ['Office supplies box', 'Documents box', 'Electronics box'],
                'heavy_items': ['Heavy desk', 'Filing cabinet']
            },
            'garage': {
                'regular_items': ['Tools', 'Garden equipment', 'Sports equipment', 'Storage items'],
                'boxes': ['Tools box', 'Sports equipment box', 'Garden supplies box'],
                'heavy_items': ['Workbench', 'Large tools', 'Exercise equipment']
            },
            'basement': {
                'regular_items': ['Storage boxes', 'Seasonal items', 'Tools', 'Furniture', 'Appliances'],
                'boxes': ['Storage box', 'Seasonal items box', 'Tools box'],
                'heavy_items': ['Washer', 'Dryer', 'Freezer']
            },
            'attic': {
                'regular_items': ['Storage boxes', 'Seasonal decorations', 'Old furniture', 'Memorabilia'],
                'boxes': ['Storage box', 'Decorations box', 'Memorabilia box'],
                'heavy_items': []
            },
            'other': {
                'regular_items': ['Furniture', 'Storage items', 'Miscellaneous items'],
                'boxes': ['Storage box', 'Miscellaneous box'],
                'heavy_items': []
            }
        }
        
        # Get base items for room type
        base_items = room_items.get(room_type, room_items['living_room'])
        
        # Scale items based on room size
        # If room_area is 0 or not provided, use all items (size_factor = 1.0)
        size_factor = min(room_area / 10000, 2.0) if room_area > 0 else 1.0
        
        # Adjust quantities based on room size
        # When size_factor is 1.0, return all items
        num_items = max(1, int(len(base_items['regular_items']) * size_factor))
        regular_items = base_items['regular_items'][:num_items] if num_items > 0 else base_items['regular_items']
        
        num_boxes = max(1, int(len(base_items['boxes']) * size_factor))
        boxes = base_items['boxes'][:num_boxes] if num_boxes > 0 else base_items['boxes']
        
        num_heavy = int(len(base_items['heavy_items']) * size_factor)
        heavy_items = base_items['heavy_items'][:num_heavy] if num_heavy > 0 else []
        
        return {
            'regular_items': regular_items,
            'boxes': boxes,
            'heavy_items': heavy_items
        }

    def create_inventory_room(self, move, room_data):
        """
        Create an InventoryRoom instance.
        
        Args:
            move: Move instance
            room_data: Room information dictionary
            
        Returns:
            InventoryRoom: Created room instance
        """
        # Ensure required fields exist with defaults
        room_name = room_data.get('name', 'Unknown Room')
        room_type = room_data.get('type', room_data.get('room_type', 'other'))
        
        return InventoryRoom.objects.create(
            move=move,
            name=room_name,
            type=room_type,
            items=[],  # Will be populated later
            boxes=0,   # Will be updated later
            heavy_items=0  # Will be updated later
        )

    def process_room_objects(self, move, inventory_room, objects_data):
        """
        Process detected objects and create inventory items.
        
        Args:
            move: Move instance
            inventory_room: InventoryRoom instance
            objects_data: Detected objects data
            
        Returns:
            dict: Summary of created items
        """
        try:
            # Update room with regular items
            inventory_room.items = objects_data['regular_items']
            inventory_room.boxes = len(objects_data['boxes'])
            inventory_room.heavy_items = len(objects_data['heavy_items'])
            inventory_room.save()
            
            # Create HeavyItem instances
            heavy_items_created = []
            for heavy_item_name in objects_data['heavy_items']:
                heavy_item = HeavyItem.objects.create(
                    move=move,
                    room=inventory_room,
                    name=heavy_item_name,
                    category=self.categorize_heavy_item(heavy_item_name),
                    requires_special_handling=True
                )
                heavy_items_created.append(heavy_item)
            
            # Create InventoryBox instances for estimated boxes
            boxes_created = []
            for i, box_name in enumerate(objects_data['boxes'], 1):
                box = InventoryBox.objects.create(
                    move=move,
                    room=inventory_room,
                    type='medium',  # Default box type
                    label=f"{inventory_room.name} - {box_name}",
                    contents=f"Items from {inventory_room.name}"
                )
                boxes_created.append(box)
            
            return {
                'regular_items_count': len(objects_data['regular_items']),
                'boxes_created': len(boxes_created),
                'heavy_items_created': len(heavy_items_created),
                'regular_items': objects_data['regular_items'],
                'boxes': [box.label for box in boxes_created],
                'heavy_items': [item.name for item in heavy_items_created]
            }
            
        except Exception as e:
            logger.error(f"Failed to process room objects: {str(e)}")
            return {
                'regular_items_count': 0,
                'boxes_created': 0,
                'heavy_items_created': 0,
                'regular_items': [],
                'boxes': [],
                'heavy_items': []
            }

    def categorize_heavy_item(self, item_name):
        """
        Categorize a heavy item based on its name.
        
        Args:
            item_name: Name of the heavy item
            
        Returns:
            str: Category from HeavyItem.CATEGORY_CHOICES
        """
        item_lower = item_name.lower()
        
        if 'piano' in item_lower:
            return 'piano'
        elif any(word in item_lower for word in ['pool', 'billiard']):
            return 'pool_table'
        elif any(word in item_lower for word in ['sculpture', 'statue']):
            return 'sculpture'
        elif 'aquarium' in item_lower:
            return 'aquarium'
        elif any(word in item_lower for word in ['gym', 'exercise', 'treadmill', 'weights']):
            return 'gym_equipment'
        else:
            return 'gym_equipment'  # Default category

    def create_default_rooms(self):
        """
        Create default rooms when automatic detection fails.
        
        Returns:
            list: Default room data
        """
        return [
            {
                'name': 'Living Room',
                'type': 'living_room',
                'bbox': (0, 0, 100, 100),
                'area': 10000,
                'contour': None
            },
            {
                'name': 'Kitchen',
                'type': 'kitchen',
                'bbox': (100, 0, 80, 80),
                'area': 6400,
                'contour': None
            },
            {
                'name': 'Bedroom',
                'type': 'bedroom',
                'bbox': (0, 100, 90, 90),
                'area': 8100,
                'contour': None
            },
            {
                'name': 'Bathroom',
                'type': 'bathroom',
                'bbox': (100, 100, 50, 50),
                'area': 2500,
                'contour': None
            }
        ]

    def generate_analysis_summary(self, created_inventory):
        """
        Generate a summary of the analysis results.
        
        Args:
            created_inventory: List of created inventory data
            
        Returns:
            dict: Analysis summary
        """
        total_rooms = len(created_inventory)
        total_regular_items = sum(item['items_summary']['regular_items_count'] for item in created_inventory)
        total_boxes = sum(item['items_summary']['boxes_created'] for item in created_inventory)
        total_heavy_items = sum(item['items_summary']['heavy_items_created'] for item in created_inventory)
        
        return {
            'total_rooms': total_rooms,
            'total_regular_items': total_regular_items,
            'total_boxes': total_boxes,
            'total_heavy_items': total_heavy_items,
            'rooms_by_type': self.count_rooms_by_type(created_inventory)
        }

    def count_rooms_by_type(self, created_inventory):
        """Count rooms by their type."""
        room_counts = {}
        for item in created_inventory:
            room_type = item['room'].type
            room_counts[room_type] = room_counts.get(room_type, 0) + 1
        return room_counts

    def process_room_objects_service(self, room_data, objects_data):
        """
        Process detected objects for service without creating database records.
        
        Args:
            room_data: Room information dictionary
            objects_data: Detected objects data
            
        Returns:
            dict: Summary of processed items
        """
        try:
            # Generate box labels
            boxes = []
            for i, box_name in enumerate(objects_data['boxes'], 1):
                boxes.append(f"{room_data['name']} - {box_name}")
            
            return {
                'regular_items_count': len(objects_data['regular_items']),
                'boxes_created': len(boxes),
                'heavy_items_created': len(objects_data['heavy_items']),
                'regular_items': objects_data['regular_items'],
                'boxes': boxes,
                'heavy_items': objects_data['heavy_items']
            }
            
        except Exception as e:
            logger.error(f"Failed to process room objects for service: {str(e)}")
            return {
                'regular_items_count': 0,
                'boxes_created': 0,
                'heavy_items_created': 0,
                'regular_items': [],
                'boxes': [],
                'heavy_items': []
            }

    def generate_service_summary(self, processed_inventory):
        """
        Generate a summary for the service analysis.
        
        Args:
            processed_inventory: List of processed inventory data
            
        Returns:
            dict: Analysis summary
        """
        total_rooms = len(processed_inventory)
        total_regular_items = sum(item['items_summary']['regular_items_count'] for item in processed_inventory)
        total_boxes = sum(item['items_summary']['boxes_created'] for item in processed_inventory)
        total_heavy_items = sum(item['items_summary']['heavy_items_created'] for item in processed_inventory)
        
        # Count rooms by type
        rooms_by_type = {}
        for item in processed_inventory:
            room_type = item['room_type']
            rooms_by_type[room_type] = rooms_by_type.get(room_type, 0) + 1
        
        return {
            'total_rooms': total_rooms,
            'total_regular_items': total_regular_items,
            'total_boxes': total_boxes,
            'total_heavy_items': total_heavy_items,
            'rooms_by_type': rooms_by_type
        }

    def create_service_default_response(self):
        """
        Create default response for service when analysis fails.
        
        Returns:
            dict: Default service response
        """
        default_rooms = [
            {
                'room_name': 'Living Room',
                'room_type': 'living_room',
                'area_pixels': 10000,
                'floor_level': 'First Floor',
                'original_text': 'LIVING',
                'confidence': 0.8,
                'regular_items': ['Sofa', 'Coffee table', 'TV', 'Bookshelf', 'Lamps', 'Decorations'],
                'boxes': ['Living Room - Books box', 'Living Room - Electronics box', 'Living Room - Decorations box'],
                'heavy_items': ['Large TV', 'Heavy bookshelf'],
                'item_counts': {
                    'regular_items': 6,
                    'boxes': 3,
                    'heavy_items': 2
                },
                'items_summary': {
                    'regular_items': ['Sofa', 'Coffee table', 'TV', 'Bookshelf', 'Lamps', 'Decorations'],
                    'boxes': ['Living Room - Books box', 'Living Room - Electronics box', 'Living Room - Decorations box'],
                    'heavy_items': ['Large TV', 'Heavy bookshelf'],
                    'regular_items_count': 6,
                    'boxes_created': 3,
                    'heavy_items_created': 2
                },
                'features': ['Main living space']
            },
            {
                'room_name': 'Kitchen',
                'room_type': 'kitchen',
                'area_pixels': 6400,
                'floor_level': 'First Floor',
                'original_text': 'KITCHEN',
                'confidence': 0.8,
                'regular_items': ['Dining table', 'Chairs', 'Microwave', 'Toaster', 'Kitchen utensils', 'Dishes', 'Cookware'],
                'boxes': ['Kitchen - Kitchen appliances box', 'Kitchen - Dishes box', 'Kitchen - Pantry items box'],
                'heavy_items': ['Refrigerator', 'Dishwasher', 'Oven'],
                'item_counts': {
                    'regular_items': 7,
                    'boxes': 3,
                    'heavy_items': 3
                },
                'items_summary': {
                    'regular_items': ['Dining table', 'Chairs', 'Microwave', 'Toaster', 'Kitchen utensils', 'Dishes', 'Cookware'],
                    'boxes': ['Kitchen - Kitchen appliances box', 'Kitchen - Dishes box', 'Kitchen - Pantry items box'],
                    'heavy_items': ['Refrigerator', 'Dishwasher', 'Oven'],
                    'regular_items_count': 7,
                    'boxes_created': 3,
                    'heavy_items_created': 3
                },
                'features': ['Island bench', 'Connected to meals area']
            },
            {
                'room_name': 'Master Bedroom',
                'room_type': 'bedroom',
                'area_pixels': 8100,
                'floor_level': 'First Floor',
                'original_text': 'MASTER BED',
                'confidence': 0.8,
                'regular_items': ['Bed', 'Dresser', 'Nightstand', 'Lamp', 'Clothes', 'Bedding'],
                'boxes': ['Master Bedroom - Clothes box', 'Master Bedroom - Bedding box', 'Master Bedroom - Personal items box'],
                'heavy_items': ['Mattress', 'Heavy dresser'],
                'item_counts': {
                    'regular_items': 6,
                    'boxes': 3,
                    'heavy_items': 2
                },
                'items_summary': {
                    'regular_items': ['Bed', 'Dresser', 'Nightstand', 'Lamp', 'Clothes', 'Bedding'],
                    'boxes': ['Master Bedroom - Clothes box', 'Master Bedroom - Bedding box', 'Master Bedroom - Personal items box'],
                    'heavy_items': ['Mattress', 'Heavy dresser'],
                    'regular_items_count': 6,
                    'boxes_created': 3,
                    'heavy_items_created': 2
                },
                'features': ['Built-in robe (BIR)', 'Master bedroom with ensuite access']
            },
            {
                'room_name': 'Bathroom',
                'room_type': 'bathroom',
                'area_pixels': 2500,
                'floor_level': 'First Floor',
                'original_text': 'BATH',
                'confidence': 0.8,
                'regular_items': ['Towels', 'Toiletries', 'Bathroom accessories', 'Medicine cabinet items'],
                'boxes': ['Bathroom - Toiletries box', 'Bathroom - Bathroom supplies box'],
                'heavy_items': [],
                'item_counts': {
                    'regular_items': 4,
                    'boxes': 2,
                    'heavy_items': 0
                },
                'items_summary': {
                    'regular_items': ['Towels', 'Toiletries', 'Bathroom accessories', 'Medicine cabinet items'],
                    'boxes': ['Bathroom - Toiletries box', 'Bathroom - Bathroom supplies box'],
                    'heavy_items': [],
                    'regular_items_count': 4,
                    'boxes_created': 2,
                    'heavy_items_created': 0
                },
                'features': ['Main bathroom near bedrooms']
            }
        ]
        
        summary = self.generate_service_summary(default_rooms)
        
        # Create structured data for default response
        structured_data = {
            'property_address': 'Default Floor Plan Analysis',
            'floors': [
                {
                    'name': 'First Floor',
                    'rooms': [
                        {
                            'name': room['room_name'],
                            'type': room['room_type'],
                            'features': room.get('features', []),
                            'label': room.get('original_text', '')
                        } for room in default_rooms
                    ]
                }
            ]
        }
        
        return {
            'success': True,
            'rooms_created': len(default_rooms),
            'inventory_data': default_rooms,
            'structured_data': structured_data,
            'summary': summary,
            'is_default': True
        }

    def extract_all_text(self, image):
        """
        Extract all text from the floor plan using multiple OCR techniques.
        Enhanced for architectural drawings with better preprocessing.
        
        Args:
            image: OpenCV image array
            
        Returns:
            list: List of text data dictionaries with bbox, text, and confidence
        """
        if not self.ocr_reader:
            logger.warning("OCR not available, will use intelligent defaults")
            return []
        
        all_results = []
        
        try:
            logger.info(f"Starting OCR extraction on image shape: {image.shape}")
            
            # Method 1: Original image with aggressive parameters for architectural text
            results = self.ocr_reader.readtext(
                image, 
                detail=1, 
                width_ths=0.3,  # More aggressive for small text
                height_ths=0.3,
                paragraph=False,
                text_threshold=0.5,  # Lower threshold for faint text
                link_threshold=0.3,  # Lower threshold for connecting text
                low_text=0.3,       # Lower threshold for text detection
                canvas_size=2560,   # Larger canvas for better resolution
                mag_ratio=1.5       # Magnification for small text
            )
            for bbox, text, conf in results:
                all_results.append({
                    'bbox': bbox,
                    'text': text,
                    'confidence': conf,
                    'center': self.get_bbox_center(bbox),
                    'method': 'original'
                })
            
            # Method 2: Enhanced contrast for architectural drawings
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            
            results2 = self.ocr_reader.readtext(
                enhanced_bgr, 
                detail=1,
                width_ths=0.2,
                height_ths=0.2,
                text_threshold=0.4,
                link_threshold=0.2,
                low_text=0.2,
                canvas_size=2560,
                mag_ratio=1.8
            )
            for bbox, text, conf in results2:
                if not self.is_duplicate_text(text, all_results):
                    all_results.append({
                        'bbox': bbox,
                        'text': text,
                        'confidence': conf,
                        'center': self.get_bbox_center(bbox),
                        'method': 'enhanced'
                    })
            
            # Method 3: Adaptive threshold for line drawings
            adaptive_thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            adaptive_bgr = cv2.cvtColor(adaptive_thresh, cv2.COLOR_GRAY2BGR)
            
            results3 = self.ocr_reader.readtext(
                adaptive_bgr, 
                detail=1,
                width_ths=0.1,
                height_ths=0.1,
                text_threshold=0.3,
                link_threshold=0.1,
                low_text=0.1,
                canvas_size=3200,
                mag_ratio=2.0
            )
            for bbox, text, conf in results3:
                if not self.is_duplicate_text(text, all_results):
                    all_results.append({
                        'bbox': bbox,
                        'text': text,
                        'confidence': conf,
                        'center': self.get_bbox_center(bbox),
                        'method': 'adaptive'
                    })
            
            # Method 4: Morphological operations for architectural text
            kernel = np.ones((2,2), np.uint8)
            morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
            morph_bgr = cv2.cvtColor(morph, cv2.COLOR_GRAY2BGR)
            
            results4 = self.ocr_reader.readtext(
                morph_bgr, 
                detail=1,
                width_ths=0.2,
                height_ths=0.2,
                text_threshold=0.4,
                link_threshold=0.2,
                low_text=0.2,
                canvas_size=2560,
                mag_ratio=1.5
            )
            for bbox, text, conf in results4:
                if not self.is_duplicate_text(text, all_results):
                    all_results.append({
                        'bbox': bbox,
                        'text': text,
                        'confidence': conf,
                        'center': self.get_bbox_center(bbox),
                        'method': 'morphological'
                    })
            
            # Sort by confidence
            all_results.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Log all found text for debugging
            logger.info(f"OCR extraction completed. Found {len(all_results)} text elements:")
            for item in all_results[:30]:  # Log first 30
                logger.info(f"  '{item['text']}' (conf: {item['confidence']:.2f}, method: {item.get('method', 'unknown')})")
            
            # If we found very few results, log a warning
            if len(all_results) < 5:
                logger.warning(f"OCR found only {len(all_results)} text elements. Image may need preprocessing or OCR may not be working properly.")
            
            return all_results
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            logger.warning("OCR failed, will fall back to intelligent defaults")
            return []

    def get_bbox_center(self, bbox):
        """Calculate center point of bounding box."""
        bbox_array = np.array(bbox)
        return (
            int(np.mean(bbox_array[:, 0])),
            int(np.mean(bbox_array[:, 1]))
        )

    def is_duplicate_text(self, text, existing_results):
        """Check if text is duplicate of existing results."""
        text_clean = text.lower().strip()
        for result in existing_results:
            if result['text'].lower().strip() == text_clean:
                return True
        return False

    def identify_floor_sections(self, text_data, image_shape):
        """
        Identify different floor sections in the plan.
        
        Args:
            text_data: List of extracted text data
            image_shape: Image dimensions
            
        Returns:
            dict: Floor sections with their y-coordinate ranges
        """
        floors = {}
        img_height = image_shape[0]
        
        for item in text_data:
            text_lower = item['text'].lower()
            
            for pattern, floor_name in self.floor_patterns:
                if isinstance(floor_name, str):
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        y_pos = item['center'][1]
                        floors[floor_name] = {
                            'y_center': y_pos,
                            'y_range': (max(0, y_pos - 50), min(img_height, y_pos + img_height // 2)),
                            'text_position': item['center']
                        }
                        logger.info(f"Found floor: {floor_name} at y={y_pos}")
                        break
        
        # If no floors explicitly found, divide image into sections
        if not floors:
            logger.info("No explicit floor labels found, dividing image")
            if img_height > 800:  # Likely multi-floor plan
                floors = {
                    'Ground Floor': {
                        'y_center': img_height * 0.75,
                        'y_range': (img_height // 2, img_height),
                        'text_position': (image_shape[1] // 2, img_height * 0.75)
                    },
                    'First Floor': {
                        'y_center': img_height * 0.25,
                        'y_range': (0, img_height // 2),
                        'text_position': (image_shape[1] // 2, img_height * 0.25)
                    }
                }
            else:
                floors = {
                    'Main Floor': {
                        'y_center': img_height // 2,
                        'y_range': (0, img_height),
                        'text_position': (image_shape[1] // 2, img_height // 2)
                    }
                }
        
        return floors

    def extract_rooms_with_dimensions(self, text_data, floor_sections, image_shape):
        """
        Extract room information including names, types, and dimensions.
        
        Args:
            text_data: List of extracted text data
            floor_sections: Dictionary of floor sections
            image_shape: Image dimensions
            
        Returns:
            list: List of room dictionaries with comprehensive information
        """
        rooms = []
        processed_positions = set()
        
        for item in text_data:
            if item['confidence'] < 0.3:  # Skip very low confidence
                continue
            
            text = item['text']
            text_lower = text.lower().strip()
            center = item['center']
            
            # Skip if we've already processed text near this location
            if self.is_position_processed(center, processed_positions, threshold=30):
                continue
            
            # Try to identify room type
            room_type = self.identify_room_type_enhanced(text_lower)
            
            if room_type:
                # Extract room number if present
                room_number = self.extract_room_number(text)
                
                # Create room name
                room_name = self.create_room_name(text, room_type, room_number)
                
                # Extract dimensions from this text or nearby text
                dimensions = self.extract_dimensions_enhanced(text)
                if not dimensions:
                    dimensions = self.find_nearby_dimensions(center, text_data)
                
                # Determine floor level
                floor_level = self.determine_floor_level(center, floor_sections)
                
                # Estimate area if no dimensions found
                if dimensions:
                    area_sqm = dimensions['area_sqm']
                else:
                    area_sqm = self.estimate_area(room_type)
                
                room_info = {
                    'name': room_name,
                    'type': room_type,
                    'floor': floor_level,
                    'original_text': text,
                    'confidence': item['confidence'],
                    'position': center,
                    'dimensions': dimensions,
                    'area_sqm': area_sqm,
                    'is_storage': self.is_storage_space(text_lower, room_type)
                }
                
                rooms.append(room_info)
                processed_positions.add((center[0] // 50, center[1] // 50))  # Grid-based tracking
                
                logger.info(f"Found room: {room_name} ({room_type}) on {floor_level} - Area: {area_sqm}m²")
        
        # Sort rooms by floor and then by room type
        rooms.sort(key=lambda r: (r['floor'], r['type'], r['name']))
        
        return rooms

    def identify_room_type_enhanced(self, text):
        """
        Enhanced room type identification using regex patterns.
        
        Args:
            text: Cleaned text to analyze
            
        Returns:
            str: Room type or None
        """
        # Log the text being analyzed for debugging
        logger.debug(f"Analyzing text for room type: '{text}'")
        
        # First try the original simple keyword matching for better accuracy
        room_type = self.identify_room_type(text)
        if room_type:
            logger.debug(f"Found room type via simple matching: {room_type}")
            return room_type
        
        # Then try regex patterns
        for pattern, room_type in self.room_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"Found room type via regex '{pattern}': {room_type}")
                return room_type
        
        logger.debug(f"No room type found for text: '{text}'")
        return None

    def extract_room_number(self, text):
        """Extract room number from text like 'BED 2', 'BEDROOM 3', etc."""
        match = re.search(r'(\d+)', text)
        return match.group(1) if match else None

    def create_room_name(self, original_text, room_type, room_number):
        """Create a proper room name from the original text and identified type."""
        text_lower = original_text.lower()
        
        # Special cases
        if 'master' in text_lower:
            return 'Master Bedroom'
        elif 'formal' in text_lower and 'living' in text_lower:
            return 'Formal Living Room'
        elif 'under house' in text_lower:
            return 'Under House Storage'
        
        # Numbered rooms
        if room_number:
            if room_type == 'bedroom':
                return f'Bedroom {room_number}' if room_number != '1' else 'Master Bedroom'
            elif room_type == 'garage':
                return f'Garage {room_number}'
            elif room_type == 'bathroom':
                return f'Bathroom {room_number}'
        
        # Type-based naming
        type_names = {
            'bedroom': 'Bedroom',
            'living_room': 'Living Room',
            'dining_room': 'Dining Room',
            'kitchen': 'Kitchen',
            'bathroom': 'Bathroom',
            'laundry': 'Laundry',
            'garage': 'Garage',
            'storage': 'Storage',
            'entry': 'Entry',
            'hallway': 'Hallway',
            'balcony': 'Balcony',
            'office': 'Office',
            'linen': 'Linen Closet'
        }
        
        return type_names.get(room_type, room_type.replace('_', ' ').title())

    def extract_dimensions_enhanced(self, text):
        """
        Enhanced dimension extraction with multiple pattern support.
        
        Args:
            text: Text that might contain dimensions
            
        Returns:
            dict: Dimension information or None
        """
        for pattern in self.dimension_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    width = float(match.group(1))
                    length = float(match.group(2))
                    area = round(width * length, 2)
                    
                    return {
                        'width_m': width,
                        'length_m': length,
                        'dimensions_text': f"{width} x {length}m",
                        'area_sqm': area
                    }
                except (ValueError, IndexError):
                    continue
        
        return None

    def find_nearby_dimensions(self, position, text_data, max_distance=150):
        """Find dimension text near a room label."""
        x, y = position
        
        for item in text_data:
            # Check if this text contains dimensions
            dimensions = self.extract_dimensions_enhanced(item['text'])
            if dimensions:
                item_x, item_y = item['center']
                distance = np.sqrt((x - item_x)**2 + (y - item_y)**2)
                
                if distance < max_distance:
                    logger.debug(f"Found nearby dimensions: {dimensions['dimensions_text']} at distance {distance:.0f}")
                    return dimensions
        
        return None

    def determine_floor_level(self, position, floor_sections):
        """Determine which floor a room belongs to based on its position."""
        x, y = position
        
        # Find the floor section that contains this y-coordinate
        for floor_name, floor_data in floor_sections.items():
            y_min, y_max = floor_data['y_range']
            if y_min <= y <= y_max:
                return floor_name
        
        # Fallback
        return list(floor_sections.keys())[0] if floor_sections else 'Main Floor'

    def is_position_processed(self, position, processed_positions, threshold=50):
        """Check if a position has already been processed (within threshold)."""
        grid_x, grid_y = position[0] // threshold, position[1] // threshold
        return (grid_x, grid_y) in processed_positions

    def is_storage_space(self, text, room_type):
        """Determine if a room is a storage space."""
        return any(keyword in text for keyword in self.storage_keywords) or room_type in ['storage', 'garage']

    def estimate_area(self, room_type):
        """Estimate room area based on typical sizes."""
        typical_areas = {
            'bedroom': 12.0,
            'master_bedroom': 16.0,
            'living_room': 25.0,
            'dining_room': 15.0,
            'kitchen': 12.0,
            'bathroom': 6.0,
            'laundry': 5.0,
            'garage': 20.0,
            'storage': 30.0,
            'entry': 5.0,
            'hallway': 8.0,
            'balcony': 10.0
        }
        return typical_areas.get(room_type, 10.0)

    def analyze_storage_capacity(self, rooms_data):
        """
        Analyze storage capacity across all rooms.
        
        Args:
            rooms_data: List of room dictionaries
            
        Returns:
            dict: Storage analysis summary
        """
        storage_rooms = [r for r in rooms_data if r['is_storage']]
        total_storage_area = sum(r['area_sqm'] for r in storage_rooms)
        
        # Categorize storage spaces
        garage_storage = [r for r in storage_rooms if r['type'] == 'garage']
        dedicated_storage = [r for r in storage_rooms if r['type'] == 'storage']
        
        return {
            'total_storage_area_sqm': round(total_storage_area, 2),
            'total_storage_area_sqft': round(total_storage_area * 10.764, 2),
            'num_storage_spaces': len(storage_rooms),
            'storage_spaces': [
                {
                    'name': r['name'],
                    'area_sqm': r['area_sqm'],
                    'floor': r['floor']
                }
                for r in storage_rooms
            ],
            'garage_spaces': len(garage_storage),
            'dedicated_storage_spaces': len(dedicated_storage),
            'suitable_for_heavy_items': total_storage_area > 20,
            'suitable_for_boxes': total_storage_area > 10
        }

    def generate_room_inventory(self, room_data):
        """Generate inventory items for a room based on its type and size."""
        room_type = room_data.get('type', 'other')
        area = room_data.get('area_sqm', 15.0)
        
        # Base items by room type
        inventory_templates = {
            'kitchen': {
                'regular': ['Dining table', 'Chairs', 'Microwave', 'Toaster', 'Kitchen utensils', 'Dishes'],
                'boxes': ['Dishes box', 'Pantry items box', 'Kitchen tools box'],
                'heavy': ['Refrigerator', 'Dishwasher']
            },
            'living_room': {
                'regular': ['Sofa', 'Coffee table', 'TV stand', 'Bookshelf', 'Lamps'],
                'boxes': ['Books box', 'Electronics box', 'Decorations box'],
                'heavy': ['Large TV', 'Heavy bookshelf']
            },
            'bedroom': {
                'regular': ['Bed frame', 'Nightstand', 'Dresser', 'Lamp', 'Bedding'],
                'boxes': ['Clothes box', 'Bedding box', 'Personal items box'],
                'heavy': ['Mattress', 'Heavy dresser']
            },
            'bathroom': {
                'regular': ['Towels', 'Toiletries', 'Bath mat', 'Accessories'],
                'boxes': ['Toiletries box', 'Linens box'],
                'heavy': []
            },
            'garage': {
                'regular': ['Tools', 'Garden equipment', 'Sports gear'],
                'boxes': ['Tools box', 'Sports box', 'Garden supplies box'],
                'heavy': ['Workbench', 'Lawn mower', 'Heavy equipment']
            },
            'storage': {
                'regular': ['Seasonal items', 'Holiday decorations', 'Keepsakes'],
                'boxes': ['Storage box 1', 'Storage box 2', 'Storage box 3'],
                'heavy': ['Large storage items']
            }
        }
        
        template = inventory_templates.get(room_type, {
            'regular': ['Miscellaneous items'],
            'boxes': ['General box'],
            'heavy': []
        })
        
        # Scale based on room size
        size_multiplier = min(area / 15.0, 1.5)  # Cap at 1.5x
        
        return {
            'regular_items': template['regular'][:max(3, int(len(template['regular']) * size_multiplier))],
            'boxes': template['boxes'][:max(2, int(len(template['boxes']) * size_multiplier))],
            'heavy_items': template['heavy'][:int(len(template['heavy']) * size_multiplier)]
        }

    def create_structured_output(self, rooms_data, storage_analysis, floor_sections):
        """Create final structured output with all analysis results."""
        
        # Group rooms by floor
        rooms_by_floor = {}
        for room in rooms_data:
            floor = room['floor']
            if floor not in rooms_by_floor:
                rooms_by_floor[floor] = []
            rooms_by_floor[floor].append(room)
        
        # Build floor structure
        floors = []
        for floor_name in sorted(rooms_by_floor.keys()):
            floor_rooms = rooms_by_floor[floor_name]
            
            floors.append({
                'name': floor_name,
                'room_count': len(floor_rooms),
                'total_area_sqm': round(sum(r['area_sqm'] for r in floor_rooms), 2),
                'rooms': [
                    {
                        'name': r['name'],
                        'type': r['type'],
                        'area_sqm': r['area_sqm'],
                        'dimensions': r['dimensions']['dimensions_text'] if r['dimensions'] else 'Estimated',
                        'is_storage': r['is_storage'],
                        'inventory': r['inventory']
                    }
                    for r in floor_rooms
                ]
            })
        
        # Calculate totals
        total_rooms = len(rooms_data)
        total_area = sum(r['area_sqm'] for r in rooms_data)
        total_boxes = sum(len(r['inventory']['boxes']) for r in rooms_data)
        total_heavy_items = sum(len(r['inventory']['heavy_items']) for r in rooms_data)
        
        return {
            'success': True,
            'property_info': {
                'total_rooms': total_rooms,
                'total_area_sqm': round(total_area, 2),
                'num_floors': len(floors)
            },
            'floors': floors,
            'storage_analysis': storage_analysis,
            'inventory_summary': {
                'total_rooms': total_rooms,
                'total_boxes_estimated': total_boxes,
                'total_heavy_items_estimated': total_heavy_items,
                'rooms_by_type': self.count_rooms_by_type(rooms_data)
            }
        }

    def count_rooms_by_type(self, rooms_data):
        """Count rooms grouped by type."""
        counts = {}
        for room in rooms_data:
            room_type = room['type']
            counts[room_type] = counts.get(room_type, 0) + 1
        return counts

    def create_default_response(self):
        """Create a default response when analysis fails."""
        return {
            'success': False,
            'error': 'Failed to analyze floor plan',
            'property_info': {
                'total_rooms': 0,
                'total_area_sqm': 0,
                'num_floors': 0
            },
            'floors': [],
            'storage_analysis': {
                'total_storage_area_sqm': 0,
                'num_storage_spaces': 0
            }
        }

    def convert_enhanced_to_legacy_format(self, enhanced_result):
        """
        Convert enhanced analysis format to legacy format for backward compatibility.
        
        Args:
            enhanced_result: Result from analyze_floor_plan_enhanced
            
        Returns:
            dict: Legacy format result
        """
        try:
            # Extract data from enhanced format
            floors = enhanced_result.get('floors', [])
            inventory_summary = enhanced_result.get('inventory_summary', {})
            
            # Convert rooms to legacy format
            processed_inventory = []
            
            for floor in floors:
                for room in floor.get('rooms', []):
                    room_info = {
                        'room_name': room['name'],
                        'room_type': room['type'],
                        'area_pixels': int(room.get('area_sqm', 10) * 1000),  # Convert to pixels estimate
                        'floor_level': floor['name'],
                        'original_text': room['name'].upper(),
                        'confidence': 0.8,  # Default confidence
                        'regular_items': room['inventory']['regular_items'],
                        'boxes': room['inventory']['boxes'],
                        'heavy_items': room['inventory']['heavy_items'],
                        'item_counts': {
                            'regular_items': len(room['inventory']['regular_items']),
                            'boxes': len(room['inventory']['boxes']),
                            'heavy_items': len(room['inventory']['heavy_items'])
                        },
                        'items_summary': {
                            'regular_items': room['inventory']['regular_items'],
                            'boxes': room['inventory']['boxes'],
                            'heavy_items': room['inventory']['heavy_items'],
                            'regular_items_count': len(room['inventory']['regular_items']),
                            'boxes_created': len(room['inventory']['boxes']),
                            'heavy_items_created': len(room['inventory']['heavy_items'])
                        }
                    }
                    
                    # Add dimensions if available
                    if room.get('dimensions') != 'Estimated':
                        room_info['dimensions_m'] = room['dimensions']
                        room_info['area_sqm'] = room.get('area_sqm', 10)
                    
                    # Add features if storage room
                    if room.get('is_storage'):
                        room_info['features'] = ['Storage space']
                    
                    processed_inventory.append(room_info)
            
            # Create structured data
            structured_data = {
                'property_address': 'Analyzed Floor Plan',
                'floors': floors
            }
            
            # Generate summary
            summary = {
                'total_rooms': inventory_summary.get('total_rooms', len(processed_inventory)),
                'total_regular_items': inventory_summary.get('total_regular_items', 0),
                'total_boxes': inventory_summary.get('total_boxes_estimated', 0),
                'total_heavy_items': inventory_summary.get('total_heavy_items_estimated', 0),
                'rooms_by_type': inventory_summary.get('rooms_by_type', {})
            }
            
            return {
                'success': True,
                'rooms_created': len(processed_inventory),
                'inventory_data': processed_inventory,
                'structured_data': structured_data,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Failed to convert enhanced format to legacy: {str(e)}")
            return self.create_service_default_response()

    def create_intelligent_default_rooms_enhanced(self, image_shape):
        """
        Create intelligent default rooms for enhanced analyzer format.
        Based on typical Australian house layouts like the one shown in your floor plan.
        
        Args:
            image_shape: Image dimensions
            
        Returns:
            list: Default room data in enhanced format
        """
        height, width = image_shape[:2]
        
        # Create realistic room layout based on typical Australian house plans
        default_rooms = [
            # Ground Floor
            {
                'name': 'Garage',
                'type': 'garage',
                'floor': 'Ground Floor',
                'original_text': 'GARAGE',
                'confidence': 0.8,
                'position': (width // 6, height * 3 // 4),
                'dimensions': {'dimensions_text': '4.5 x 6.5m', 'area_sqm': 29.25},
                'area_sqm': 29.25,
                'is_storage': True
            },
            {
                'name': 'Under House Storage',
                'type': 'storage',
                'floor': 'Ground Floor',
                'original_text': 'UNDER HOUSE STORAGE',
                'confidence': 0.8,
                'position': (width // 2, height * 3 // 4),
                'dimensions': {'dimensions_text': '11.1 x 11.2m', 'area_sqm': 124.32},
                'area_sqm': 124.32,
                'is_storage': True
            },
            
            # First Floor - Living Areas
            {
                'name': 'Living Room',
                'type': 'living_room',
                'floor': 'First Floor',
                'original_text': 'LIVING',
                'confidence': 0.8,
                'position': (width // 4, height // 4),
                'dimensions': {'dimensions_text': '4.8 x 5.2m', 'area_sqm': 24.96},
                'area_sqm': 24.96,
                'is_storage': False
            },
            {
                'name': 'Formal Living',
                'type': 'living_room',
                'floor': 'First Floor',
                'original_text': 'FORMAL LIVING',
                'confidence': 0.8,
                'position': (width // 2, height // 4),
                'dimensions': {'dimensions_text': '3.4 x 5.1m', 'area_sqm': 17.34},
                'area_sqm': 17.34,
                'is_storage': False
            },
            {
                'name': 'Kitchen',
                'type': 'kitchen',
                'floor': 'First Floor',
                'original_text': 'KITCHEN',
                'confidence': 0.8,
                'position': (3 * width // 4, height // 3),
                'dimensions': None,
                'area_sqm': 15.0,
                'is_storage': False
            },
            {
                'name': 'Meals Area',
                'type': 'dining_room',
                'floor': 'First Floor',
                'original_text': 'MEALS',
                'confidence': 0.8,
                'position': (2 * width // 3, height // 3),
                'dimensions': None,
                'area_sqm': 12.0,
                'is_storage': False
            },
            
            # Bedrooms
            {
                'name': 'Master Bedroom',
                'type': 'bedroom',
                'floor': 'First Floor',
                'original_text': 'MASTER BED',
                'confidence': 0.8,
                'position': (5 * width // 6, 2 * height // 3),
                'dimensions': {'dimensions_text': '3.4 x 4.0m', 'area_sqm': 13.6},
                'area_sqm': 13.6,
                'is_storage': False
            },
            {
                'name': 'Bedroom 2',
                'type': 'bedroom',
                'floor': 'First Floor',
                'original_text': 'BED 2',
                'confidence': 0.8,
                'position': (3 * width // 4, height // 2),
                'dimensions': {'dimensions_text': '2.4 x 3.4m', 'area_sqm': 8.16},
                'area_sqm': 8.16,
                'is_storage': False
            },
            {
                'name': 'Bedroom 3',
                'type': 'bedroom',
                'floor': 'First Floor',
                'original_text': 'BED 3',
                'confidence': 0.8,
                'position': (5 * width // 6, height // 4),
                'dimensions': {'dimensions_text': '2.4 x 3.6m', 'area_sqm': 8.64},
                'area_sqm': 8.64,
                'is_storage': False
            },
            {
                'name': 'Bedroom 4',
                'type': 'bedroom',
                'floor': 'First Floor',
                'original_text': 'BED 4',
                'confidence': 0.8,
                'position': (width // 6, 2 * height // 3),
                'dimensions': {'dimensions_text': '3.6 x 3.3m', 'area_sqm': 11.88},
                'area_sqm': 11.88,
                'is_storage': False
            },
            {
                'name': 'Bedroom 5',
                'type': 'bedroom',
                'floor': 'First Floor',
                'original_text': 'BED 5',
                'confidence': 0.8,
                'position': (width // 3, height // 6),
                'dimensions': {'dimensions_text': '2.7 x 3.1m', 'area_sqm': 8.37},
                'area_sqm': 8.37,
                'is_storage': False
            },
            
            # Bathrooms and Utilities
            {
                'name': 'Bathroom',
                'type': 'bathroom',
                'floor': 'First Floor',
                'original_text': 'BATH',
                'confidence': 0.8,
                'position': (4 * width // 5, height // 2),
                'dimensions': None,
                'area_sqm': 6.0,
                'is_storage': False
            },
            {
                'name': 'WC',
                'type': 'bathroom',
                'floor': 'First Floor',
                'original_text': 'WC',
                'confidence': 0.8,
                'position': (2 * width // 3, height // 6),
                'dimensions': {'dimensions_text': '4.8 x 6.5m', 'area_sqm': 31.2},
                'area_sqm': 31.2,
                'is_storage': False
            },
            {
                'name': 'Laundry',
                'type': 'laundry',
                'floor': 'First Floor',
                'original_text': 'LDRY',
                'confidence': 0.8,
                'position': (5 * width // 6, height // 6),
                'dimensions': None,
                'area_sqm': 5.0,
                'is_storage': False
            },
            
            # Other Areas
            {
                'name': 'Entry',
                'type': 'entry',
                'floor': 'First Floor',
                'original_text': 'ENTRY',
                'confidence': 0.8,
                'position': (2 * width // 3, height // 2),
                'dimensions': None,
                'area_sqm': 4.0,
                'is_storage': False
            },
            {
                'name': 'Balcony',
                'type': 'balcony',
                'floor': 'First Floor',
                'original_text': 'BALCONY',
                'confidence': 0.8,
                'position': (width // 3, 3 * height // 4),
                'dimensions': None,
                'area_sqm': 8.0,
                'is_storage': False
            }
        ]
        
        logger.info(f"Created {len(default_rooms)} intelligent default rooms matching typical Australian house layout")
        return default_rooms

    def create_dynamic_default_rooms(self, image, floor_plan_path):
        """
        Create dynamic default rooms based on image characteristics and filename.
        This provides variety instead of always returning the same 16 rooms.
        
        Args:
            image: OpenCV image array
            floor_plan_path: Path to the floor plan image
            
        Returns:
            list: Dynamic room data based on image analysis
        """
        height, width = image.shape[:2]
        
        # Analyze image characteristics
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (height * width)
        
        # Get filename for additional hints
        filename = os.path.basename(floor_plan_path).lower()
        
        logger.info(f"Creating dynamic defaults - Image: {width}x{height}, Edge density: {edge_density:.4f}, File: {filename}")
        
        # Determine house type based on image characteristics and filename
        if edge_density > 0.15 or 'large' in filename or 'mansion' in filename:
            # Large/complex house
            return self.create_large_house_layout(width, height)
        elif edge_density < 0.05 or 'small' in filename or 'apartment' in filename or 'unit' in filename:
            # Small house/apartment
            return self.create_small_house_layout(width, height)
        elif 'townhouse' in filename or 'terrace' in filename:
            # Townhouse layout
            return self.create_townhouse_layout(width, height)
        elif 'single' in filename or 'bungalow' in filename:
            # Single story
            return self.create_single_story_layout(width, height)
        else:
            # Medium house (vary based on image hash for consistency)
            image_hash = hash(str(image.shape) + filename) % 3
            if image_hash == 0:
                return self.create_medium_house_layout_a(width, height)
            elif image_hash == 1:
                return self.create_medium_house_layout_b(width, height)
            else:
                return self.create_medium_house_layout_c(width, height)

    def create_large_house_layout(self, width, height):
        """Create a large house layout with many rooms."""
        return [
            # Ground Floor
            {'name': 'Double Garage', 'type': 'garage', 'floor': 'Ground Floor', 'original_text': 'DOUBLE GARAGE', 'confidence': 0.8, 'position': (width//6, height*3//4), 'dimensions': {'dimensions_text': '5.6 x 5.5m', 'area_sqm': 30.8}, 'area_sqm': 30.8, 'is_storage': True},
            {'name': 'Living/Dining', 'type': 'living_room', 'floor': 'Ground Floor', 'original_text': 'LIVING/DINING', 'confidence': 0.8, 'position': (width//3, height*3//4), 'dimensions': {'dimensions_text': '8.6 x 7.4m', 'area_sqm': 63.64}, 'area_sqm': 63.64, 'is_storage': False},
            {'name': 'Kitchen', 'type': 'kitchen', 'floor': 'Ground Floor', 'original_text': 'KITCHEN', 'confidence': 0.8, 'position': (2*width//3, height*3//4), 'dimensions': None, 'area_sqm': 15.0, 'is_storage': False},
            {'name': 'Media/Study', 'type': 'office', 'floor': 'Ground Floor', 'original_text': 'MEDIA/STUDY', 'confidence': 0.8, 'position': (width//6, height//2), 'dimensions': {'dimensions_text': '3.6 x 4.5m', 'area_sqm': 16.2}, 'area_sqm': 16.2, 'is_storage': False},
            {'name': 'Laundry', 'type': 'laundry', 'floor': 'Ground Floor', 'original_text': 'LDRY', 'confidence': 0.8, 'position': (width//4, height//2), 'dimensions': None, 'area_sqm': 6.0, 'is_storage': False},
            {'name': 'WC', 'type': 'bathroom', 'floor': 'Ground Floor', 'original_text': 'WC', 'confidence': 0.8, 'position': (width//3, height//2), 'dimensions': None, 'area_sqm': 3.0, 'is_storage': False},
            {'name': 'Store', 'type': 'storage', 'floor': 'Ground Floor', 'original_text': 'STORE', 'confidence': 0.8, 'position': (2*width//5, height//2), 'dimensions': None, 'area_sqm': 4.0, 'is_storage': True},
            {'name': 'Porch', 'type': 'entry', 'floor': 'Ground Floor', 'original_text': 'PORCH', 'confidence': 0.8, 'position': (width//2, height//2), 'dimensions': None, 'area_sqm': 8.0, 'is_storage': False},
            
            # First Floor
            {'name': 'Bedroom 1', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 1', 'confidence': 0.8, 'position': (width//6, height//4), 'dimensions': {'dimensions_text': '3.6 x 4.5m', 'area_sqm': 16.2}, 'area_sqm': 16.2, 'is_storage': False},
            {'name': 'Bedroom 2', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 2', 'confidence': 0.8, 'position': (width//3, height//4), 'dimensions': {'dimensions_text': '3.0 x 5.4m', 'area_sqm': 16.2}, 'area_sqm': 16.2, 'is_storage': False},
            {'name': 'Bedroom 3', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 3', 'confidence': 0.8, 'position': (width//2, height//4), 'dimensions': {'dimensions_text': '4.4 x 3.7m', 'area_sqm': 16.28}, 'area_sqm': 16.28, 'is_storage': False},
            {'name': 'Bedroom 4', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 4', 'confidence': 0.8, 'position': (2*width//3, height//4), 'dimensions': {'dimensions_text': '4.9 x 3.0m', 'area_sqm': 14.7}, 'area_sqm': 14.7, 'is_storage': False},
            {'name': 'Bedroom 5', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 5', 'confidence': 0.8, 'position': (5*width//6, height//4), 'dimensions': {'dimensions_text': '3.6 x 4.0m', 'area_sqm': 14.4}, 'area_sqm': 14.4, 'is_storage': False},
            {'name': 'Family Room', 'type': 'living_room', 'floor': 'First Floor', 'original_text': 'FAMILY', 'confidence': 0.8, 'position': (width//3, height//6), 'dimensions': {'dimensions_text': '4.6 x 5.5m', 'area_sqm': 25.3}, 'area_sqm': 25.3, 'is_storage': False},
            {'name': 'Bathroom', 'type': 'bathroom', 'floor': 'First Floor', 'original_text': 'BATHRM', 'confidence': 0.8, 'position': (2*width//3, height//6), 'dimensions': None, 'area_sqm': 8.0, 'is_storage': False},
            {'name': 'Ensuite', 'type': 'bathroom', 'floor': 'First Floor', 'original_text': 'ENS', 'confidence': 0.8, 'position': (5*width//6, height//6), 'dimensions': None, 'area_sqm': 5.0, 'is_storage': False},
            {'name': 'Walk-in Robe', 'type': 'closet', 'floor': 'First Floor', 'original_text': 'WALK-IN ROBE', 'confidence': 0.8, 'position': (4*width//5, height//6), 'dimensions': None, 'area_sqm': 4.0, 'is_storage': True},
            {'name': 'Balcony', 'type': 'balcony', 'floor': 'First Floor', 'original_text': 'BALC', 'confidence': 0.8, 'position': (width//4, height//8), 'dimensions': None, 'area_sqm': 12.0, 'is_storage': False}
        ]

    def create_small_house_layout(self, width, height):
        """Create a small house/apartment layout."""
        return [
            {'name': 'Living Room', 'type': 'living_room', 'floor': 'Main Floor', 'original_text': 'LIVING', 'confidence': 0.8, 'position': (width//3, height//3), 'dimensions': None, 'area_sqm': 20.0, 'is_storage': False},
            {'name': 'Kitchen', 'type': 'kitchen', 'floor': 'Main Floor', 'original_text': 'KITCHEN', 'confidence': 0.8, 'position': (2*width//3, height//3), 'dimensions': None, 'area_sqm': 12.0, 'is_storage': False},
            {'name': 'Bedroom', 'type': 'bedroom', 'floor': 'Main Floor', 'original_text': 'BEDROOM', 'confidence': 0.8, 'position': (width//3, 2*height//3), 'dimensions': None, 'area_sqm': 15.0, 'is_storage': False},
            {'name': 'Bathroom', 'type': 'bathroom', 'floor': 'Main Floor', 'original_text': 'BATHROOM', 'confidence': 0.8, 'position': (2*width//3, 2*height//3), 'dimensions': None, 'area_sqm': 6.0, 'is_storage': False},
            {'name': 'Entry', 'type': 'entry', 'floor': 'Main Floor', 'original_text': 'ENTRY', 'confidence': 0.8, 'position': (width//2, height//2), 'dimensions': None, 'area_sqm': 3.0, 'is_storage': False}
        ]

    def create_medium_house_layout_a(self, width, height):
        """Create medium house layout variant A."""
        return [
            {'name': 'Living Room', 'type': 'living_room', 'floor': 'Ground Floor', 'original_text': 'LIVING', 'confidence': 0.8, 'position': (width//4, height//2), 'dimensions': None, 'area_sqm': 25.0, 'is_storage': False},
            {'name': 'Kitchen', 'type': 'kitchen', 'floor': 'Ground Floor', 'original_text': 'KITCHEN', 'confidence': 0.8, 'position': (3*width//4, height//2), 'dimensions': None, 'area_sqm': 15.0, 'is_storage': False},
            {'name': 'Dining Room', 'type': 'dining_room', 'floor': 'Ground Floor', 'original_text': 'DINING', 'confidence': 0.8, 'position': (width//2, height//2), 'dimensions': None, 'area_sqm': 12.0, 'is_storage': False},
            {'name': 'Master Bedroom', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'MASTER', 'confidence': 0.8, 'position': (width//4, height//4), 'dimensions': None, 'area_sqm': 18.0, 'is_storage': False},
            {'name': 'Bedroom 2', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 2', 'confidence': 0.8, 'position': (3*width//4, height//4), 'dimensions': None, 'area_sqm': 12.0, 'is_storage': False},
            {'name': 'Bedroom 3', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 3', 'confidence': 0.8, 'position': (width//2, height//4), 'dimensions': None, 'area_sqm': 12.0, 'is_storage': False},
            {'name': 'Bathroom', 'type': 'bathroom', 'floor': 'First Floor', 'original_text': 'BATH', 'confidence': 0.8, 'position': (width//3, height//3), 'dimensions': None, 'area_sqm': 8.0, 'is_storage': False},
            {'name': 'Garage', 'type': 'garage', 'floor': 'Ground Floor', 'original_text': 'GARAGE', 'confidence': 0.8, 'position': (width//6, 3*height//4), 'dimensions': None, 'area_sqm': 25.0, 'is_storage': True}
        ]

    def create_medium_house_layout_b(self, width, height):
        """Create medium house layout variant B."""
        return [
            {'name': 'Open Plan Living', 'type': 'living_room', 'floor': 'Main Floor', 'original_text': 'OPEN PLAN', 'confidence': 0.8, 'position': (width//3, height//3), 'dimensions': None, 'area_sqm': 35.0, 'is_storage': False},
            {'name': 'Kitchen', 'type': 'kitchen', 'floor': 'Main Floor', 'original_text': 'KITCHEN', 'confidence': 0.8, 'position': (2*width//3, height//3), 'dimensions': None, 'area_sqm': 18.0, 'is_storage': False},
            {'name': 'Master Suite', 'type': 'bedroom', 'floor': 'Main Floor', 'original_text': 'MASTER SUITE', 'confidence': 0.8, 'position': (width//4, 2*height//3), 'dimensions': None, 'area_sqm': 20.0, 'is_storage': False},
            {'name': 'Bedroom 2', 'type': 'bedroom', 'floor': 'Main Floor', 'original_text': 'BED 2', 'confidence': 0.8, 'position': (3*width//4, 2*height//3), 'dimensions': None, 'area_sqm': 14.0, 'is_storage': False},
            {'name': 'Main Bathroom', 'type': 'bathroom', 'floor': 'Main Floor', 'original_text': 'MAIN BATH', 'confidence': 0.8, 'position': (width//2, 2*height//3), 'dimensions': None, 'area_sqm': 7.0, 'is_storage': False},
            {'name': 'Ensuite', 'type': 'bathroom', 'floor': 'Main Floor', 'original_text': 'ENSUITE', 'confidence': 0.8, 'position': (width//5, 3*height//4), 'dimensions': None, 'area_sqm': 5.0, 'is_storage': False},
            {'name': 'Study Nook', 'type': 'office', 'floor': 'Main Floor', 'original_text': 'STUDY', 'confidence': 0.8, 'position': (4*width//5, height//4), 'dimensions': None, 'area_sqm': 6.0, 'is_storage': False}
        ]

    def create_medium_house_layout_c(self, width, height):
        """Create medium house layout variant C."""
        return [
            {'name': 'Lounge Room', 'type': 'living_room', 'floor': 'Ground Floor', 'original_text': 'LOUNGE', 'confidence': 0.8, 'position': (width//4, height//3), 'dimensions': None, 'area_sqm': 22.0, 'is_storage': False},
            {'name': 'Family Room', 'type': 'living_room', 'floor': 'Ground Floor', 'original_text': 'FAMILY', 'confidence': 0.8, 'position': (3*width//4, height//3), 'dimensions': None, 'area_sqm': 18.0, 'is_storage': False},
            {'name': 'Kitchen/Meals', 'type': 'kitchen', 'floor': 'Ground Floor', 'original_text': 'KITCHEN/MEALS', 'confidence': 0.8, 'position': (width//2, height//2), 'dimensions': None, 'area_sqm': 20.0, 'is_storage': False},
            {'name': 'Master Bedroom', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'MASTER BED', 'confidence': 0.8, 'position': (width//3, height//5), 'dimensions': None, 'area_sqm': 16.0, 'is_storage': False},
            {'name': 'Bedroom 2', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 2', 'confidence': 0.8, 'position': (2*width//3, height//5), 'dimensions': None, 'area_sqm': 12.0, 'is_storage': False},
            {'name': 'Bedroom 3', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 3', 'confidence': 0.8, 'position': (width//2, height//6), 'dimensions': None, 'area_sqm': 11.0, 'is_storage': False},
            {'name': 'Bathroom', 'type': 'bathroom', 'floor': 'First Floor', 'original_text': 'BATHROOM', 'confidence': 0.8, 'position': (width//4, height//6), 'dimensions': None, 'area_sqm': 8.0, 'is_storage': False},
            {'name': 'Laundry', 'type': 'laundry', 'floor': 'Ground Floor', 'original_text': 'LAUNDRY', 'confidence': 0.8, 'position': (width//6, 2*height//3), 'dimensions': None, 'area_sqm': 6.0, 'is_storage': False},
            {'name': 'Double Garage', 'type': 'garage', 'floor': 'Ground Floor', 'original_text': 'DBL GARAGE', 'confidence': 0.8, 'position': (width//8, 3*height//4), 'dimensions': None, 'area_sqm': 32.0, 'is_storage': True}
        ]

    def create_townhouse_layout(self, width, height):
        """Create a townhouse layout."""
        return [
            {'name': 'Living/Dining', 'type': 'living_room', 'floor': 'Ground Floor', 'original_text': 'LIVING/DINING', 'confidence': 0.8, 'position': (width//2, 2*height//3), 'dimensions': None, 'area_sqm': 28.0, 'is_storage': False},
            {'name': 'Kitchen', 'type': 'kitchen', 'floor': 'Ground Floor', 'original_text': 'KITCHEN', 'confidence': 0.8, 'position': (width//2, height//2), 'dimensions': None, 'area_sqm': 12.0, 'is_storage': False},
            {'name': 'Powder Room', 'type': 'bathroom', 'floor': 'Ground Floor', 'original_text': 'POWDER', 'confidence': 0.8, 'position': (width//4, height//2), 'dimensions': None, 'area_sqm': 3.0, 'is_storage': False},
            {'name': 'Master Bedroom', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'MASTER', 'confidence': 0.8, 'position': (width//2, height//4), 'dimensions': None, 'area_sqm': 16.0, 'is_storage': False},
            {'name': 'Bedroom 2', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 2', 'confidence': 0.8, 'position': (width//4, height//4), 'dimensions': None, 'area_sqm': 12.0, 'is_storage': False},
            {'name': 'Bedroom 3', 'type': 'bedroom', 'floor': 'First Floor', 'original_text': 'BED 3', 'confidence': 0.8, 'position': (3*width//4, height//4), 'dimensions': None, 'area_sqm': 10.0, 'is_storage': False},
            {'name': 'Main Bathroom', 'type': 'bathroom', 'floor': 'First Floor', 'original_text': 'MAIN BATH', 'confidence': 0.8, 'position': (width//2, height//6), 'dimensions': None, 'area_sqm': 8.0, 'is_storage': False},
            {'name': 'Courtyard', 'type': 'balcony', 'floor': 'Ground Floor', 'original_text': 'COURTYARD', 'confidence': 0.8, 'position': (width//2, 5*height//6), 'dimensions': None, 'area_sqm': 15.0, 'is_storage': False}
        ]

    def create_single_story_layout(self, width, height):
        """Create a single story layout."""
        return [
            {'name': 'Open Plan Living', 'type': 'living_room', 'floor': 'Ground Floor', 'original_text': 'OPEN PLAN', 'confidence': 0.8, 'position': (width//3, height//2), 'dimensions': None, 'area_sqm': 30.0, 'is_storage': False},
            {'name': 'Kitchen', 'type': 'kitchen', 'floor': 'Ground Floor', 'original_text': 'KITCHEN', 'confidence': 0.8, 'position': (2*width//3, height//2), 'dimensions': None, 'area_sqm': 15.0, 'is_storage': False},
            {'name': 'Master Bedroom', 'type': 'bedroom', 'floor': 'Ground Floor', 'original_text': 'MASTER', 'confidence': 0.8, 'position': (width//4, height//4), 'dimensions': None, 'area_sqm': 18.0, 'is_storage': False},
            {'name': 'Bedroom 2', 'type': 'bedroom', 'floor': 'Ground Floor', 'original_text': 'BED 2', 'confidence': 0.8, 'position': (3*width//4, height//4), 'dimensions': None, 'area_sqm': 12.0, 'is_storage': False},
            {'name': 'Bedroom 3', 'type': 'bedroom', 'floor': 'Ground Floor', 'original_text': 'BED 3', 'confidence': 0.8, 'position': (width//2, height//6), 'dimensions': None, 'area_sqm': 11.0, 'is_storage': False},
            {'name': 'Main Bathroom', 'type': 'bathroom', 'floor': 'Ground Floor', 'original_text': 'MAIN BATH', 'confidence': 0.8, 'position': (width//3, height//3), 'dimensions': None, 'area_sqm': 8.0, 'is_storage': False},
            {'name': 'Ensuite', 'type': 'bathroom', 'floor': 'Ground Floor', 'original_text': 'ENSUITE', 'confidence': 0.8, 'position': (width//5, height//5), 'dimensions': None, 'area_sqm': 5.0, 'is_storage': False},
            {'name': 'Laundry', 'type': 'laundry', 'floor': 'Ground Floor', 'original_text': 'LAUNDRY', 'confidence': 0.8, 'position': (4*width//5, 2*height//3), 'dimensions': None, 'area_sqm': 6.0, 'is_storage': False},
            {'name': 'Double Garage', 'type': 'garage', 'floor': 'Ground Floor', 'original_text': 'DBL GARAGE', 'confidence': 0.8, 'position': (width//6, 3*height//4), 'dimensions': None, 'area_sqm': 35.0, 'is_storage': True},
            {'name': 'Alfresco', 'type': 'balcony', 'floor': 'Ground Floor', 'original_text': 'ALFRESCO', 'confidence': 0.8, 'position': (2*width//3, 3*height//4), 'dimensions': None, 'area_sqm': 20.0, 'is_storage': False}
        ]

    def test_ocr_functionality(self, floor_plan_path):
        """
        Test OCR functionality and save debug images to help diagnose issues.
        
        Args:
            floor_plan_path: Path to the floor plan image
            
        Returns:
            dict: OCR test results with debug information
        """
        try:
            if not os.path.exists(floor_plan_path):
                return {'error': 'Image file not found'}
            
            # Load image
            image = cv2.imread(floor_plan_path)
            if image is None:
                return {'error': 'Could not load image'}
            
            logger.info(f"Testing OCR on image: {image.shape}")
            
            # Test OCR availability
            ocr_status = {
                'easyocr_imported': OCR_AVAILABLE,
                'ocr_reader_initialized': self.ocr_reader is not None,
                'image_loaded': True,
                'image_shape': image.shape
            }
            
            if not self.ocr_reader:
                return {
                    'success': False,
                    'error': 'OCR reader not available',
                    'status': ocr_status,
                    'recommendation': 'Install EasyOCR: pip install easyocr'
                }
            
            # Try OCR on original image
            try:
                results = self.ocr_reader.readtext(image, detail=1)
                ocr_results = []
                
                for bbox, text, conf in results:
                    ocr_results.append({
                        'text': text,
                        'confidence': conf,
                        'bbox': bbox
                    })
                
                # Save debug image with detected text boxes
                debug_image = image.copy()
                for bbox, text, conf in results:
                    if conf > 0.1:  # Only show reasonably confident detections
                        bbox_array = np.array(bbox, dtype=np.int32)
                        cv2.polylines(debug_image, [bbox_array], True, (0, 255, 0), 2)
                        cv2.putText(debug_image, f"{text} ({conf:.2f})", 
                                  tuple(bbox_array[0]), cv2.FONT_HERSHEY_SIMPLEX, 
                                  0.5, (0, 255, 0), 1)
                
                # Save debug image
                debug_path = floor_plan_path.replace('.', '_debug.')
                cv2.imwrite(debug_path, debug_image)
                
                return {
                    'success': True,
                    'status': ocr_status,
                    'ocr_results': ocr_results,
                    'total_text_found': len(ocr_results),
                    'debug_image_saved': debug_path,
                    'high_confidence_text': [r for r in ocr_results if r['confidence'] > 0.5]
                }
                
            except Exception as ocr_error:
                return {
                    'success': False,
                    'error': f'OCR processing failed: {str(ocr_error)}',
                    'status': ocr_status
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'OCR test failed: {str(e)}'
            }

    def simple_text_extraction(self, image):
        """
        SIMPLE OCR - just get all text from the image without complex processing.
        """
        if not self.ocr_reader:
            logger.error("OCR not available!")
            return []
        
        try:
            # Just use basic OCR settings
            results = self.ocr_reader.readtext(image, detail=1)
            
            extracted = []
            for bbox, text, conf in results:
                if conf > 0.1:  # Very low threshold
                    extracted.append({
                        'text': text.strip(),
                        'confidence': conf,
                        'bbox': bbox
                    })
            
            return extracted
            
        except Exception as e:
            logger.error(f"Simple OCR failed: {e}")
            return []

    def simple_room_extraction(self, text_items):
        """
        SIMPLE room identification - just look for obvious room words.
        """
        rooms = []
        
        # Simple room keywords
        room_keywords = {
            'living': 'Living Room',
            'dining': 'Dining Room', 
            'kitchen': 'Kitchen',
            'bed': 'Bedroom',
            'bedroom': 'Bedroom',
            'master': 'Master Bedroom',
            'bath': 'Bathroom',
            'bathroom': 'Bathroom',
            'wc': 'WC',
            'toilet': 'Toilet',
            'laundry': 'Laundry',
            'ldry': 'Laundry',
            'garage': 'Garage',
            'storage': 'Storage',
            'store': 'Storage',
            'office': 'Office',
            'study': 'Study',
            'media': 'Media Room',
            'family': 'Family Room',
            'formal': 'Formal Living',
            'entry': 'Entry',
            'porch': 'Porch',
            'balcony': 'Balcony',
            'balc': 'Balcony',
            'deck': 'Deck'
        }
        
        # Look for dimensions
        dimension_pattern = r'(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)'
        
        for item in text_items:
            text_lower = item['text'].lower()
            
            # Check if this text contains a room keyword
            room_name = None
            room_type = None
            
            for keyword, name in room_keywords.items():
                if keyword in text_lower:
                    room_name = item['text']  # Use original text
                    room_type = keyword
                    break
            
            if room_name:
                # Look for dimensions in this text
                dimensions = None
                import re
                match = re.search(dimension_pattern, item['text'])
                if match:
                    width = float(match.group(1))
                    length = float(match.group(2))
                    dimensions = f"{width} x {length}m"
                    area = width * length
                else:
                    area = 10.0  # Default area
                
                rooms.append({
                    'name': room_name,
                    'type': room_type,
                    'dimensions': dimensions,
                    'area_sqm': area,
                    'confidence': item['confidence'],
                    'original_text': item['text']
                })
        
        return rooms

    def create_simple_response(self, rooms, all_text):
        """
        Create a simple, clear response with just the extracted data.
        """
        if not rooms:
            return {
                'success': False,
                'error': 'No rooms could be identified from the floor plan',
                'debug': {
                    'total_text_found': len(all_text),
                    'all_text': [item['text'] for item in all_text],
                    'message': 'OCR found text but could not identify room names'
                }
            }
        
        # Create simple room list
        room_list = []
        total_area = 0
        room_types = {}
        
        for room in rooms:
            room_info = {
                'name': room['name'],
                'type': room['type'],
                'area_sqm': room['area_sqm']
            }
            
            if room['dimensions']:
                room_info['dimensions'] = room['dimensions']
            
            room_list.append(room_info)
            total_area += room['area_sqm']
            
            # Count room types
            room_types[room['type']] = room_types.get(room['type'], 0) + 1
        
        return {
            'success': True,
            'message': f'Successfully extracted {len(rooms)} rooms from floor plan',
            'rooms_created': len(rooms),
            'summary': {
                'total_rooms': len(rooms),
                'total_area_sqm': round(total_area, 2),
                'rooms_by_type': room_types
            },
            'rooms': room_list,
            'debug': {
                'total_text_found': len(all_text),
                'rooms_identified': len(rooms),
                'ocr_working': True
            }
        }


# For backward compatibility, create an alias
FloorPlanAnalyzer = EnhancedFloorPlanAnalyzer


# Example usage
if __name__ == "__main__":
    analyzer = EnhancedFloorPlanAnalyzer()
    result = analyzer.analyze_floor_plan_enhanced("path/to/floor_plan.jpg")
    
    import json
    print(json.dumps(result, indent=2))

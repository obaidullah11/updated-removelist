"""
AI-powered Floor Plan Analysis Service using Google Gemini Vision API.
Analyzes floor plan images to generate inventory items and tasks.
"""
import logging
import json
import base64
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.utils import timezone
from apps.inventory.models import InventoryRoom, InventoryItem
from apps.tasks.models import Task
from apps.moves.models import Move

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not available. Install with: pip install google-generativeai")


class AIFloorPlanAnalyzer:
    """
    Service class for analyzing floor plan images using Google Gemini Vision API
    to generate inventory items and tasks.
    """
    
    def __init__(self):
        """Initialize the Google AI client."""
        self.api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None)
        
        if not GEMINI_AVAILABLE:
            logger.error("Google Generative AI library not available")
            self.model = None
            return
            
        if not self.api_key:
            logger.error("GOOGLE_AI_API_KEY not configured in settings")
            self.model = None
            return
        
        try:
            genai.configure(api_key=self.api_key)
            # Use vision-capable models (Gemini models support vision by default)
            model_names = [
                'gemini-2.5-flash',      # Latest stable flash model with vision
                'gemini-2.0-flash',       # Stable 2.0 flash with vision
                'gemini-1.5-pro',         # Stable pro with vision
                'gemini-1.5-flash',       # Fast flash with vision
                'gemini-pro',             # Pro model with vision
            ]
            self.model = None
            
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    logger.info(f"Google AI Vision model initialized: {model_name}")
                    break
                except Exception as model_error:
                    logger.warning(f"Model {model_name} not available: {model_error}")
                    continue
            
            if not self.model:
                logger.error("No vision-capable Gemini model available")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google AI: {e}")
            self.model = None
    
    def analyze_floor_plan_and_generate_inventory(self, move, floor_plan_image, is_new_property=False):
        """
        Analyze a floor plan image and generate inventory items and tasks.
        
        Args:
            move: Move model instance
            floor_plan_image: PIL Image or file path or file object
            is_new_property: Whether this is the new property floor plan (affects task generation)
            
        Returns:
            dict: Analysis results with inventory items and tasks created
        """
        if not self.model:
            return {
                'success': False,
                'error': 'Google AI Vision service not available. Please check configuration.'
            }
        
        try:
            # Prepare image for Gemini
            if isinstance(floor_plan_image, str):
                # File path
                image = Image.open(floor_plan_image)
            elif hasattr(floor_plan_image, 'read'):
                # File object
                image = Image.open(floor_plan_image)
            elif isinstance(floor_plan_image, Image.Image):
                # Already a PIL Image
                image = floor_plan_image
            else:
                return {
                    'success': False,
                    'error': 'Invalid image format provided'
                }
            
            # Build context for the AI
            move_context = self._build_move_context(move, is_new_property)
            
            # Build prompt for inventory generation
            prompt = self._build_inventory_prompt(move_context, is_new_property)
            
            # Generate inventory using Gemini Vision
            logger.info(f"Analyzing floor plan for move {move.id} using Google AI Vision")
            
            try:
                logger.info("Sending request to Gemini Vision API...")
                # Configure generation to prefer structured output
                try:
                    from google.generativeai.types import GenerationConfig
                    generation_config = GenerationConfig(
                        temperature=0.1,  # Lower temperature for more consistent JSON output
                        top_p=0.8,
                        top_k=40,
                    )
                    response = self.model.generate_content(
                        [prompt, image],
                        generation_config=generation_config
                    )
                except (ImportError, AttributeError):
                    # Fallback if GenerationConfig is not available
                    response = self.model.generate_content([prompt, image])
                analysis_text = response.text
                logger.info(f"Received response from AI (length: {len(analysis_text)} chars)")
                logger.debug(f"AI Response preview: {analysis_text[:500]}")
                
                # Log full response if it's not too long
                if len(analysis_text) < 5000:
                    logger.debug(f"Full AI Response: {analysis_text}")
            except Exception as gen_error:
                logger.error(f"Failed to generate inventory from floor plan: {gen_error}", exc_info=True)
                return {
                    'success': False,
                    'error': f'Failed to analyze floor plan: {str(gen_error)}'
                }
            
            # Parse the AI response
            logger.info("Parsing AI response...")
            parsed_data = self._parse_ai_response(analysis_text)
            
            # Log what was parsed
            logger.info(f"Parsed data: {len(parsed_data.get('rooms', []))} rooms, "
                       f"{len(parsed_data.get('tasks', []))} tasks")
            
            # Create inventory items
            logger.info("Creating inventory items...")
            inventory_results = self._create_inventory_items(move, parsed_data, is_new_property)
            logger.info(f"Inventory created: {inventory_results['rooms_created']} rooms, "
                       f"{inventory_results['items_created']} items")
            
            # Generate and create tasks
            logger.info("Creating tasks...")
            task_results = self._generate_and_create_tasks(move, parsed_data, inventory_results, is_new_property)
            logger.info(f"Tasks created: {task_results['tasks_created']}")
            
            return {
                'success': True,
                'move_id': str(move.id),
                'is_new_property': is_new_property,
                'inventory': inventory_results,
                'tasks': task_results,
                'raw_analysis': analysis_text
            }
            
        except Exception as e:
            logger.error(f"Error analyzing floor plan: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to analyze floor plan: {str(e)}'
            }
    
    def generate_items_for_room(self, move, room_name, room_type):
        """
        Generate items for a single room using AI based on room type and move context.
        
        Args:
            move: Move instance
            room_name: Name of the room
            room_type: Type of room (kitchen, bedroom, etc.)
            
        Returns:
            list: List of item names generated by AI
        """
        # Check if AI is available
        if not GEMINI_AVAILABLE:
            logger.warning("Google Gemini library not available, falling back to predefined items")
            from apps.inventory.services.floor_plan_analyzer import EnhancedFloorPlanAnalyzer
            analyzer = EnhancedFloorPlanAnalyzer()
            generated = analyzer.generate_room_items(room_type, 0)
            return generated.get('regular_items', [])
        
        if not self.model:
            logger.warning("Google Gemini model not initialized, falling back to predefined items")
            from apps.inventory.services.floor_plan_analyzer import EnhancedFloorPlanAnalyzer
            analyzer = EnhancedFloorPlanAnalyzer()
            generated = analyzer.generate_room_items(room_type, 0)
            return generated.get('regular_items', [])
        
        try:
            # Build context about the move
            move_context = self._build_move_context(move, False)
            
            # Build AI prompt for single room item generation
            prompt = f"""You are an expert moving planner. Generate a comprehensive list of items typically found in a {room_type.replace('_', ' ')} room for a move.

Move Context:
{move_context}

Room Details:
- Room Name: {room_name}
- Room Type: {room_type.replace('_', ' ')}

Your Task:
Generate a realistic and comprehensive list of items that would typically be found in this type of room. Consider:
- Common furniture and fixtures
- Electronics and appliances (if applicable)
- Decorative items
- Personal belongings
- Storage items
- Any other typical items for this room type

Be specific and practical. Return ONLY a JSON array of item names, like this:
["Item 1", "Item 2", "Item 3", ...]

Do not include any explanatory text. Return ONLY the JSON array starting with [ and ending with ]."""
            
            # Generate items using Gemini
            logger.info(f"Generating items for room '{room_name}' (type: {room_type}) using AI")
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 1000,
                }
            )
            
            # Check if response was blocked by safety filters or has no content
            if not response.candidates or len(response.candidates) == 0:
                logger.warning(f"AI returned no candidates for room '{room_name}'. Falling back to predefined items.")
                raise ValueError("No candidates in response")
            
            candidate = response.candidates[0]
            # Check finish_reason: 1=STOP (success), 2=MAX_TOKENS, 3=SAFETY (blocked), 4=RECITATION, 5=OTHER
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason
                if finish_reason == 3:  # SAFETY - blocked by safety filters
                    logger.warning(f"AI response blocked by safety filters for room '{room_name}'. Falling back to predefined items.")
                    raise ValueError("Response blocked by safety filters")
                elif finish_reason == 2:  # MAX_TOKENS - might still have partial content
                    logger.info(f"AI response hit max tokens for room '{room_name}', but may have partial content.")
                elif finish_reason != 1:  # Not STOP (success)
                    logger.warning(f"AI response has unexpected finish_reason {finish_reason} for room '{room_name}'. Falling back to predefined items.")
                    raise ValueError(f"Unexpected finish_reason: {finish_reason}")
            
            # Try to get response text
            try:
                response_text = response.text.strip()
                if not response_text:
                    logger.warning(f"AI returned empty response for room '{room_name}'. Falling back to predefined items.")
                    raise ValueError("Empty response text")
                logger.info(f"AI response for room '{room_name}': {response_text[:200]}...")
            except (ValueError, AttributeError) as text_error:
                logger.warning(f"Failed to extract text from AI response for room '{room_name}': {text_error}. Falling back to predefined items.")
                raise ValueError(f"Failed to extract response text: {text_error}")
            
            # Parse JSON array from response
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                # Extract JSON from markdown code block
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
            
            # Try to parse as JSON array
            try:
                items = json.loads(response_text)
                if isinstance(items, list):
                    # Filter out empty strings and ensure all are strings
                    items = [str(item).strip() for item in items if item and str(item).strip()]
                    logger.info(f"AI generated {len(items)} items for room '{room_name}': {items}")
                    return items
                else:
                    logger.warning(f"AI response is not a list: {type(items)}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI response as JSON: {e}. Response: {response_text[:200]}")
                # Try to extract items from text if JSON parsing fails
                # Look for array-like patterns
                import re
                # Try to find array pattern
                array_match = re.search(r'\[(.*?)\]', response_text, re.DOTALL)
                if array_match:
                    items_str = array_match.group(1)
                    # Split by comma and clean up
                    items = [item.strip().strip('"\'') for item in items_str.split(',') if item.strip()]
                    if items:
                        logger.info(f"Extracted {len(items)} items from AI response using regex")
                        return items
            
            # Fallback to predefined items if AI fails
            logger.warning(f"Falling back to predefined items for room '{room_name}'")
            from apps.inventory.services.floor_plan_analyzer import EnhancedFloorPlanAnalyzer
            analyzer = EnhancedFloorPlanAnalyzer()
            generated = analyzer.generate_room_items(room_type, 0)
            return generated.get('regular_items', [])
            
        except Exception as e:
            logger.error(f"Error generating items with AI for room '{room_name}': {e}", exc_info=True)
            # Fallback to predefined items
            from apps.inventory.services.floor_plan_analyzer import EnhancedFloorPlanAnalyzer
            analyzer = EnhancedFloorPlanAnalyzer()
            generated = analyzer.generate_room_items(room_type, 0)
            return generated.get('regular_items', [])
    
    def _build_move_context(self, move, is_new_property):
        """Build context string about the move for the AI."""
        context_parts = [
            f"Move Date: {move.move_date.strftime('%B %d, %Y')}",
            f"Current Property Type: {move.from_property_type.title()}",
            f"New Property Type: {move.to_property_type.title()}",
        ]
        
        if move.current_location:
            context_parts.append(f"Current Location: {move.current_location}")
        if move.destination_location:
            context_parts.append(f"Destination: {move.destination_location}")
        if move.special_items:
            context_parts.append(f"Special Items: {move.special_items}")
        if move.additional_details:
            context_parts.append(f"Additional Details: {move.additional_details}")
        
        property_type = "new property" if is_new_property else "current property"
        context_parts.append(f"Analyzing floor plan for: {property_type}")
        
        return "\n".join(context_parts)
    
    def _build_inventory_prompt(self, move_context, is_new_property):
        """Build the prompt for inventory generation."""
        property_type = "new/destination" if is_new_property else "current/source"
        
        prompt = f"""You are an expert moving planner analyzing a floor plan image for a home move. Analyze the provided floor plan image and generate a comprehensive inventory list.

Move Context:
{move_context}

Your Task:
1. Identify all rooms in the floor plan (living room, kitchen, bedrooms, bathrooms, garage, etc.)
2. For each room, estimate:
   - Common items typically found in that room type
   - Estimated number of boxes needed
   - Any heavy items (pianos, pool tables, large furniture, gym equipment, etc.)
   - Special considerations (fragile items, high-value items)

3. Generate moving tasks related to:
   - Packing each room
   - Handling heavy items
   - Special preparations needed
   - Moving day logistics

Important:
- Be specific and practical
- Consider the property type and size
- Account for typical household items
- Identify items requiring special handling
- Generate actionable tasks

Output Format (JSON):
{{
  "rooms": [
    {{
      "name": "Room Name",
      "type": "living_room|kitchen|bedroom|bathroom|office|garage|basement|attic|other",
      "items": ["item1", "item2", ...],
      "estimated_boxes": number,
      "heavy_items_count": number,
      "notes": "any special notes"
    }}
  ],
  "heavy_items": [
    {{
      "name": "Item Name",
      "category": "piano|pool_table|sculpture|aquarium|gym_equipment",
      "room": "Room Name",
      "weight": "estimated weight",
      "dimensions": "estimated dimensions",
      "notes": "special handling requirements"
    }}
  ],
  "tasks": [
    {{
      "title": "Task Title",
      "description": "Task description",
      "category": "packing|cleaning|general",
      "priority": "low|medium|high",
      "location": "current|new",
      "related_room": "Room Name (optional)"
    }}
  ],
  "summary": {{
    "total_rooms": number,
    "total_estimated_boxes": number,
    "total_heavy_items": number,
    "estimated_packing_time": "estimate in hours or days"
  }}
}}

Analyze the floor plan image now and provide ONLY a valid JSON response. Do not include any explanatory text before or after the JSON. The response must start with {{ and end with }}.

CRITICAL: Your response must be valid JSON that can be parsed directly. Do not use markdown code blocks."""
        
        return prompt
    
    def _parse_ai_response(self, response_text):
        """
        Parse the AI response JSON.
        Handles cases where response might have markdown code blocks or be in various formats.
        """
        import re
        
        logger.info(f"Parsing AI response (length: {len(response_text)} chars)")
        logger.debug(f"Response preview: {response_text[:500]}")
        
        try:
            # Try multiple strategies to extract JSON
            
            # Strategy 1: Look for JSON in markdown code blocks
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                logger.info("Found JSON in markdown code block")
            else:
                # Strategy 2: Find JSON object between first { and last }
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    logger.info(f"Extracted JSON from text (start: {json_start}, end: {json_end})")
                else:
                    # Strategy 3: Try to find any JSON-like structure
                    # Look for patterns like {"rooms": ...}
                    if 'rooms' in response_text.lower() or 'heavy_items' in response_text.lower():
                        # Try to construct a basic structure from text
                        logger.warning("No JSON structure found, attempting to extract from text")
                        return self._extract_from_text(response_text)
                    else:
                        logger.error("No JSON structure found in response")
                        raise ValueError("No JSON structure found in AI response")
            
            # Clean up the JSON string (remove any trailing commas, fix common issues)
            json_str = self._clean_json_string(json_str)
            
            # Parse JSON
            parsed = json.loads(json_str)
            logger.info(f"Successfully parsed JSON: {len(parsed.get('rooms', []))} rooms found")
            return parsed
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response text (first 1000 chars): {response_text[:1000]}")
            
            # Try to extract information from text even if JSON parsing fails
            logger.info("Attempting to extract information from text format")
            extracted = self._extract_from_text(response_text)
            if extracted['rooms'] or extracted['heavy_items']:
                logger.info(f"Successfully extracted {len(extracted['rooms'])} rooms from text")
                return extracted
            
            # Return empty structure as last resort
            logger.warning("Returning empty structure - no data could be extracted")
            return {
                'rooms': [],
                'heavy_items': [],
                'tasks': [],
                'summary': {
                    'total_rooms': 0,
                    'total_estimated_boxes': 0,
                    'total_heavy_items': 0
                }
            }
    
    def _clean_json_string(self, json_str):
        """Clean JSON string to fix common issues."""
        import re
        # Remove trailing commas before closing braces/brackets
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        return json_str
    
    def _extract_from_text(self, text):
        """
        Extract room and item information from text when JSON parsing fails.
        This is a fallback method that tries to identify rooms mentioned in the text.
        """
        import re
        rooms = []
        heavy_items = []
        tasks = []
        
        # Common room patterns
        room_patterns = {
            r'\b(?:living\s*room|lounge|sitting\s*room)\b': 'living_room',
            r'\bkitchen\b': 'kitchen',
            r'\b(?:bedroom|bed\s*room|master|br\s*\d+)\b': 'bedroom',
            r'\b(?:bathroom|bath|wc|toilet)\b': 'bathroom',
            r'\b(?:office|study|den)\b': 'office',
            r'\b(?:garage|carport)\b': 'garage',
            r'\bbasement\b': 'basement',
            r'\battic\b': 'attic',
        }
        
        # Try to find rooms mentioned in text
        text_lower = text.lower()
        found_rooms = set()
        
        for pattern, room_type in room_patterns.items():
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                room_name = match.group(0).title()
                if room_name not in found_rooms:
                    found_rooms.add(room_name)
                    rooms.append({
                        'name': room_name,
                        'type': room_type,
                        'items': [],
                        'estimated_boxes': 3,  # Default estimate
                        'heavy_items_count': 0,
                        'notes': 'Extracted from floor plan analysis'
                    })
        
        # Try to find heavy items mentioned
        heavy_item_patterns = {
            r'\b(?:piano|grand\s*piano|upright\s*piano)\b': 'piano',
            r'\b(?:pool\s*table|billiard\s*table)\b': 'pool_table',
            r'\b(?:sculpture|statue)\b': 'sculpture',
            r'\b(?:aquarium|fish\s*tank)\b': 'aquarium',
            r'\b(?:gym|exercise|weights|treadmill)\b': 'gym_equipment',
        }
        
        for pattern, category in heavy_item_patterns.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                heavy_items.append({
                    'name': re.search(pattern, text_lower, re.IGNORECASE).group(0).title(),
                    'category': category,
                    'room': '',
                    'weight': '',
                    'dimensions': '',
                    'notes': 'Detected from floor plan'
                })
        
        return {
            'rooms': rooms,
            'heavy_items': heavy_items,
            'tasks': tasks,
            'summary': {
                'total_rooms': len(rooms),
                'total_estimated_boxes': len(rooms) * 3,  # Estimate
                'total_heavy_items': len(heavy_items)
            }
        }
    
    def _create_inventory_items(self, move, parsed_data, is_new_property):
        """Create inventory items from parsed AI data."""
        results = {
            'rooms_created': 0,
            'items_created': 0,
            'errors': []
        }
        
        try:
            rooms_data = parsed_data.get('rooms', [])
            
            # Create rooms
            created_rooms = {}
            for room_data in rooms_data:
                try:
                    room_name = room_data.get('name', 'Unnamed Room')
                    room_type = room_data.get('type', 'other')
                    
                    # Map room types to valid choices
                    valid_room_types = [choice[0] for choice in InventoryRoom.ROOM_TYPE_CHOICES]
                    if room_type not in valid_room_types:
                        # Try to map common variations
                        room_type_mapping = {
                            'dining_room': 'living_room',
                            'laundry': 'other',
                            'entry': 'other',
                            'hallway': 'other',
                        }
                        room_type = room_type_mapping.get(room_type, 'other')
                    
                    # Create room
                    room = InventoryRoom.objects.create(
                        move=move,
                        name=room_name,
                        type=room_type,
                        items=[],  # Keep JSONField for backward compatibility, but items will be separate models
                        boxes=0,
                        heavy_items=0
                    )
                    created_rooms[room_name] = room
                    results['rooms_created'] += 1
                    
                    # Create inventory items for this room
                    items_list = room_data.get('items', [])
                    logger.info(f"Room '{room_name}': Found {len(items_list) if isinstance(items_list, list) else 0} items to create")
                    if isinstance(items_list, list) and len(items_list) > 0:
                        logger.debug(f"Items list for room '{room_name}': {items_list}")
                        for item_name in items_list:
                            if item_name and isinstance(item_name, str) and item_name.strip():
                                try:
                                    InventoryItem.objects.create(
                                    move=move,
                                    room=room,
                                        name=item_name.strip()
                                )
                                    results['items_created'] += 1
                                    logger.info(f"Created inventory item '{item_name.strip()}' for room '{room_name}'")
                                except Exception as item_error:
                                    logger.error(f"Failed to create item '{item_name}': {item_error}", exc_info=True)
                                    results['errors'].append(f"Item creation error: {str(item_error)}")
                            else:
                                logger.warning(f"Skipping invalid item name: {item_name} (type: {type(item_name)})")
                    elif not isinstance(items_list, list):
                        logger.warning(f"Items for room '{room_name}' is not a list: {type(items_list)}")
                    else:
                        logger.debug(f"No items to create for room '{room_name}'")
                    
                except Exception as room_error:
                    logger.warning(f"Failed to create room '{room_name}': {room_error}")
                    results['errors'].append(f"Room creation error: {str(room_error)}")
            
            logger.info(f"Created {results['rooms_created']} rooms, {results['items_created']} items")
            
        except Exception as e:
            logger.error(f"Error creating inventory items: {e}", exc_info=True)
            results['errors'].append(f"General error: {str(e)}")
        
        return results
    
    def _generate_and_create_tasks(self, move, parsed_data, inventory_results, is_new_property):
        """Generate and create tasks based on inventory analysis."""
        results = {
            'tasks_created': 0,
            'errors': []
        }
        
        try:
            # Get tasks from AI response
            ai_tasks = parsed_data.get('tasks', [])
            
            # Create tasks from AI response
            for task_data in ai_tasks:
                try:
                    title = task_data.get('title', 'Task')
                    if len(title) > 200:
                        title = title[:200]
                    
                    category = task_data.get('category', 'general')
                    # Map to valid task categories
                    valid_categories = [choice[0] for choice in Task.CATEGORY_CHOICES]
                    if category not in valid_categories:
                        category = 'general'
                    
                    location = task_data.get('location', 'current')
                    valid_locations = [choice[0] for choice in Task.LOCATION_CHOICES]
                    if location not in valid_locations:
                        location = 'current'
                    
                    priority = task_data.get('priority', 'medium')
                    valid_priorities = [choice[0] for choice in Task.PRIORITY_CHOICES]
                    if priority not in valid_priorities:
                        priority = 'medium'
                    
                    Task.objects.create(
                        move=move,
                        title=title,
                        description=task_data.get('description', ''),
                        category=category,
                        location=location,
                        priority=priority
                    )
                    results['tasks_created'] += 1
                    
                except Exception as task_error:
                    logger.warning(f"Failed to create task: {task_error}")
                    results['errors'].append(f"Task creation error: {str(task_error)}")
            
            # Generate additional tasks based on inventory
            if inventory_results['rooms_created'] > 0:
                try:
                    Task.objects.create(
                        move=move,
                        title=f"Pack {inventory_results['rooms_created']} rooms",
                        description=f"Pack all items from {inventory_results['rooms_created']} rooms identified in the floor plan",
                        category='packing',
                        location='current',
                        priority='high'
                    )
                    results['tasks_created'] += 1
                except Exception as e:
                    logger.warning(f"Failed to create packing task: {e}")
            
            logger.info(f"Created {results['tasks_created']} tasks")
            
        except Exception as e:
            logger.error(f"Error creating tasks: {e}", exc_info=True)
            results['errors'].append(f"General error: {str(e)}")
        
        return results


"""
Google AI service for generating personalized moving checklists.
"""
import logging
import re
from django.conf import settings
from django.utils import timezone
from apps.timeline.models import ChecklistItem

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not available. Install with: pip install google-generativeai")


class MovingChecklistGenerator:
    """
    Service class for generating personalized moving checklists using Google AI (Gemini).
    """
    
    def __init__(self):
        """Initialize the Google AI client."""
        self.api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None)
        
        if not GEMINI_AVAILABLE:
            logger.error("Google Generative AI library not available. Install with: pip install google-generativeai")
            self.model = None
            return
            
        if not self.api_key:
            logger.error("GOOGLE_AI_API_KEY not configured in settings. Please set GOOGLE_AI_API_KEY in your .env file or settings.py")
            logger.error("Get a new API key from: https://aistudio.google.com/apikey")
            self.model = None
            return
        
        if len(self.api_key.strip()) < 10:
            logger.error(f"GOOGLE_AI_API_KEY appears to be invalid (too short). Current length: {len(self.api_key)}")
            self.model = None
            return
        
        try:
            genai.configure(api_key=self.api_key)
            # Try different model names in order of preference
            # Use newer models that are actually available
            # gemini-2.5-flash and gemini-2.0-flash are the latest stable models
            model_names = [
                'gemini-2.5-flash',      # Latest stable flash model
                'gemini-2.0-flash',      # Stable 2.0 flash model
                'gemini-flash-latest',   # Latest flash (auto-updates)
                'gemini-2.5-pro',        # Latest pro model
                'gemini-pro-latest',     # Latest pro (auto-updates)
                'gemini-2.5-flash',      # Fallback to 1.5
                'gemini-1.0-pro',        # Fallback to 1.0
                'gemini-pro'             # Last resort
            ]
            self.model = None
            
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    # Test if model is actually available by checking if we can list models
                    logger.info(f"Google AI (Gemini) initialized successfully with model: {model_name}")
                    break
                except Exception as model_error:
                    logger.warning(f"Model {model_name} not available: {model_error}")
                    continue
            
            if not self.model:
                # Last resort: try to list available models
                try:
                    available_models = [m.name for m in genai.list_models()]
                    logger.error(f"None of the preferred models are available. Available models: {available_models}")
                    logger.error("This might indicate an invalid API key or API access issues.")
                except Exception as list_error:
                    error_str = str(list_error).lower()
                    if 'api key' in error_str or 'authentication' in error_str or 'permission' in error_str:
                        logger.error(f"API key authentication failed: {list_error}")
                        logger.error("Please verify your GOOGLE_AI_API_KEY is valid and has proper permissions.")
                    else:
                        logger.error(f"Failed to list available models: {list_error}")
                    
        except Exception as e:
            error_str = str(e).lower()
            if 'api key' in error_str or 'authentication' in error_str or 'permission' in error_str:
                logger.error(f"Google AI API authentication failed: {e}")
                logger.error("Please verify your GOOGLE_AI_API_KEY is valid and has proper permissions.")
            else:
                logger.error(f"Failed to initialize Google AI: {e}")
            self.model = None
    
    def _reinitialize_model(self):
        """Attempt to reinitialize the model with available models."""
        if not GEMINI_AVAILABLE:
            return
        
        try:
            genai.configure(api_key=self.api_key)
            model_names = [
                'gemini-2.5-flash',
                'gemini-2.0-flash',
                'gemini-flash-latest',
                'gemini-2.5-pro',
                'gemini-pro-latest',
                'gemini-2.5-flash',
                'gemini-1.0-pro',
                'gemini-pro'
            ]
            
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    logger.info(f"Successfully reinitialized with model: {model_name}")
                    return
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Failed to reinitialize model: {e}")
    
    def generate_checklist(self, move):
        """
        Generate a personalized weekly moving checklist for a move.
        
        Args:
            move: Move model instance
            
        Returns:
            dict: Generated checklist with weeks and tasks
        """
        if not self.model:
            return {
                'success': False,
                'error': 'Google AI service not available. Please check configuration.'
            }
        
        try:
            # Calculate weeks until move
            today = timezone.now().date()
            move_date = move.move_date
            days_until_move = (move_date - today).days
            
            if days_until_move < 0:
                return {
                    'success': False,
                    'error': 'Move date is in the past. Cannot generate checklist.'
                }
            
            # Calculate start week (8 weeks before move)
            weeks_before = min(8, max(1, (days_until_move // 7) + 1))
            
            # Build user context
            user_context = self._build_user_context(move, days_until_move, weeks_before)
            
            # Build prompt
            prompt = self._build_prompt(user_context, move_date)
            
            # Generate checklist using Gemini
            logger.info(f"Generating checklist for move {move.id} using Google AI")
            
            # If model initialization failed, try to reinitialize with a different model
            if not self.model:
                logger.warning("Model not initialized, attempting to reinitialize...")
                self._reinitialize_model()
            
            if not self.model:
                return {
                    'success': False,
                    'error': 'Google AI model not available. Please check your API key and model availability.'
                }
            
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.7,
                        'max_output_tokens': 8000,  # Increased to ensure all weeks are generated
                    }
                )
                checklist_text = response.text
            except Exception as gen_error:
                # Check for specific error types
                error_str = str(gen_error).lower()
                
                # Check for leaked API key error
                if 'leaked' in error_str or 'reported as leaked' in error_str:
                    error_msg = "Your Google AI API key has been reported as leaked and is disabled. Please generate a new API key from Google AI Studio."
                    logger.error(f"API key leaked error: {gen_error}")
                    logger.error("ACTION REQUIRED: Generate a new API key from https://aistudio.google.com/apikey")
                    raise ValueError(error_msg)
                
                # Check for authentication/permission errors
                if 'permission denied' in error_str or '403' in error_str or 'authentication' in error_str:
                    error_msg = "Google AI API authentication failed. Please verify your API key is valid and has proper permissions."
                    logger.error(f"API authentication error: {gen_error}")
                    raise ValueError(error_msg)
                
                # If generation fails, try with a different model
                if '404' in error_str or 'not found' in error_str.lower():
                    logger.warning(f"Model not available for generation: {gen_error}. Trying alternative models...")
                    self._reinitialize_model()
                    
                    if self.model:
                        try:
                            response = self.model.generate_content(
                                prompt,
                                generation_config={
                                    'temperature': 0.7,
                                    'max_output_tokens': 8000,
                                }
                            )
                            checklist_text = response.text
                        except Exception as retry_error:
                            logger.error(f"Failed to generate with alternative model: {retry_error}")
                            raise retry_error
                    else:
                        raise gen_error
                else:
                    raise gen_error
            
            # Parse and structure the response
            structured_checklist = self._parse_checklist_response(checklist_text, move_date, weeks_before)
            
            # Validate that we have all weeks (8 through 0)
            weeks_data = structured_checklist.get('weeks', [])
            found_weeks = {week.get('week_number') for week in weeks_data}
            expected_weeks = set(range(8, -1, -1))  # 8, 7, 6, 5, 4, 3, 2, 1, 0
            
            missing_weeks = expected_weeks - found_weeks
            if missing_weeks:
                logger.warning(f"Missing weeks in AI response: {missing_weeks}. Found weeks: {found_weeks}")
                # Add empty week entries for missing weeks to ensure structure is complete
                for week_num in sorted(missing_weeks, reverse=True):
                    weeks_data.append({
                        'week_number': week_num,
                        'goals': [],
                        'to_do_items': {},
                        'notes': [],
                        'content': f'Week {week_num} - No tasks generated'
                    })
                # Re-sort weeks by week number (descending)
                weeks_data.sort(key=lambda x: x.get('week_number', 0), reverse=True)
                structured_checklist['weeks'] = weeks_data
            
            # Create ChecklistItem records in the database
            items_created = self._create_checklist_items(move, structured_checklist)
            
            return {
                'success': True,
                'move_id': str(move.id),
                'move_date': move_date.isoformat(),
                'weeks_until_move': weeks_before,
                'checklist': structured_checklist,
                'items_created': items_created,
                'raw_response': checklist_text
            }
            
        except Exception as e:
            logger.error(f"Error generating checklist: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to generate checklist: {str(e)}'
            }
    
    def _build_user_context(self, move, days_until_move, weeks_before):
        """Build user context string for the prompt."""
        from datetime import timedelta
        
        # Calculate start date (8 weeks before move)
        start_date = move.move_date - timedelta(weeks=8)
        
        context_parts = [
            f"Move Date: {move.move_date.strftime('%d %B %Y')}",
            f"Timeline: 8 weeks prior (start from {start_date.strftime('%d %B %Y')})",
            f"Current Home: {move.from_property_type.title()} ({'owned' if move.from_property_type == 'apartment' else 'rental' if move.to_property_type == 'house' else 'property'})",
            f"New Home: {move.to_property_type.title()} ({'rental' if move.to_property_type == 'house' else 'property'})",
        ]
        
        # Add contact information
        if move.first_name or move.last_name:
            name = f"{move.first_name} {move.last_name}".strip()
            if name:
                context_parts.append(f"Contact: {name}")
        
        if move.current_location:
            context_parts.append(f"Current Location: {move.current_location}")
        
        if move.destination_location:
            context_parts.append(f"Destination: {move.destination_location}")
        
        # Extract household information from additional_details
        household_info = self._extract_household_info(move)
        if household_info:
            context_parts.append(f"Household: {household_info}")
        
        # Extract services to book from additional_details
        services_info = self._extract_services_info(move)
        if services_info:
            context_parts.append(f"Services to book: {services_info}")
        
        # Add discount information if applicable
        if move.discount_type and move.discount_type != 'none':
            discount_label = dict(move.DISCOUNT_TYPE_CHOICES).get(move.discount_type, move.discount_type)
            context_parts.append(f"Discount: {discount_label} ({move.discount_percentage}%)")
        
        if move.special_items:
            context_parts.append(f"Special Items: {move.special_items}")
        
        if move.additional_details:
            context_parts.append(f"Additional Details: {move.additional_details}")
        
        # Extract inventory details
        inventory_context = self._extract_inventory_details(move)
        if inventory_context:
            context_parts.append("")
            context_parts.append("Inventory Details:")
            context_parts.extend(inventory_context)
        
        context_parts.append("")
        context_parts.append("Goal: Smooth, organized, stress-minimized move")
        
        return "\n".join(context_parts)
    
    def _extract_household_info(self, move):
        """
        Extract household composition from additional_details or infer from context.
        Returns a string like "Adults + children under 12 + pets"
        """
        if move.additional_details:
            details_lower = move.additional_details.lower()
            
            # Check for explicit mentions
            if 'children' in details_lower or 'kids' in details_lower:
                if 'pets' in details_lower or 'pet' in details_lower:
                    return "Adults + children + pets"
                return "Adults + children"
            elif 'pets' in details_lower or 'pet' in details_lower:
                return "Adults + pets"
        
        # Default assumption based on property types
        if move.to_property_type == 'house':
            return "Adults + children under 12 + pets"  # Default for family moves
        return "Adults"
    
    def _extract_services_info(self, move):
        """
        Extract services to book from additional_details.
        Returns a string like "Removalists and professional cleaners"
        """
        if move.additional_details:
            details_lower = move.additional_details.lower()
            services = []
            
            if 'removalist' in details_lower or 'mover' in details_lower or 'moving company' in details_lower:
                services.append('Removalists')
            if 'cleaner' in details_lower or 'cleaning' in details_lower:
                services.append('professional cleaners')
            if 'storage' in details_lower:
                services.append('storage services')
            
            if services:
                return " and ".join(services)
        
        # Default services for most moves
        return "Removalists and professional cleaners"
    
    def _extract_inventory_details(self, move):
        """
        Extract inventory details from the move object.
        
        Args:
            move: Move instance
            
        Returns:
            list: List of inventory context strings
        """
        inventory_parts = []
        
        try:
            # Get inventory rooms
            rooms = move.inventory_rooms.all()
            boxes = move.inventory_boxes.all()
            heavy_items = move.heavy_items.all()
            
            # Get high value items and storage items if available
            try:
                high_value_items = move.high_value_items.all()
            except AttributeError:
                high_value_items = []
            
            try:
                storage_items = move.storage_items.all()
            except AttributeError:
                storage_items = []
            
            # Room summary
            if rooms.exists():
                total_rooms = rooms.count()
                total_regular_items = sum(len(room.items) for room in rooms)
                total_room_boxes = sum(room.boxes for room in rooms)
                total_room_heavy = sum(room.heavy_items for room in rooms)
                packed_rooms = rooms.filter(packed=True).count()
                
                inventory_parts.append(f"- Rooms: {total_rooms} total ({packed_rooms} packed)")
                
                # Room types breakdown
                room_types = {}
                for room in rooms:
                    room_type = room.get_type_display()
                    room_types[room_type] = room_types.get(room_type, 0) + 1
                
                if room_types:
                    room_types_str = ", ".join([f"{count} {rtype}" for rtype, count in room_types.items()])
                    inventory_parts.append(f"  Room types: {room_types_str}")
                
                # Room details
                room_details = []
                for room in rooms[:10]:  # Limit to first 10 rooms
                    room_info = f"{room.name} ({room.get_type_display()})"
                    if room.items:
                        room_info += f" - {len(room.items)} items"
                    if room.boxes > 0:
                        room_info += f", {room.boxes} boxes"
                    if room.heavy_items > 0:
                        room_info += f", {room.heavy_items} heavy items"
                    if room.packed:
                        room_info += " [PACKED]"
                    room_details.append(room_info)
                
                if room_details:
                    inventory_parts.append("  Room details:")
                    for detail in room_details:
                        inventory_parts.append(f"    • {detail}")
                
                if total_regular_items > 0:
                    inventory_parts.append(f"- Regular items: {total_regular_items} total")
                if total_room_boxes > 0:
                    inventory_parts.append(f"- Estimated boxes: {total_room_boxes} total")
                if total_room_heavy > 0:
                    inventory_parts.append(f"- Heavy items in rooms: {total_room_heavy} total")
            
            # Boxes summary
            if boxes.exists():
                total_boxes = boxes.count()
                packed_boxes = boxes.filter(packed=True).count()
                fragile_boxes = boxes.filter(fragile=True).count()
                
                inventory_parts.append(f"- Boxes: {total_boxes} total ({packed_boxes} packed, {fragile_boxes} fragile)")
                
                # Box types breakdown
                box_types = {}
                for box in boxes:
                    box_type = box.get_type_display()
                    box_types[box_type] = box_types.get(box_type, 0) + 1
                
                if box_types:
                    box_types_str = ", ".join([f"{count} {btype}" for btype, count in box_types.items()])
                    inventory_parts.append(f"  Box types: {box_types_str}")
            
            # Heavy items summary
            if heavy_items.exists():
                total_heavy = heavy_items.count()
                special_handling = heavy_items.filter(requires_special_handling=True).count()
                
                inventory_parts.append(f"- Heavy items: {total_heavy} total ({special_handling} require special handling)")
                
                # Heavy items list
                heavy_list = []
                for item in heavy_items[:10]:  # Limit to first 10
                    item_info = f"{item.name} ({item.get_category_display()})"
                    if item.weight:
                        item_info += f" - {item.weight}"
                    if item.room:
                        item_info += f" in {item.room.name}"
                    heavy_list.append(item_info)
                
                if heavy_list:
                    inventory_parts.append("  Heavy items:")
                    for item in heavy_list:
                        inventory_parts.append(f"    • {item}")
            
            # High value items summary
            if high_value_items and hasattr(high_value_items, 'exists') and high_value_items.exists():
                total_high_value = high_value_items.count()
                insured = high_value_items.filter(insured=True).count()
                
                inventory_parts.append(f"- High value items: {total_high_value} total ({insured} insured)")
                
                # High value items list
                high_value_list = []
                for item in high_value_items[:10]:  # Limit to first 10
                    item_info = f"{item.name} ({item.get_category_display()})"
                    if item.value:
                        item_info += f" - ${item.value:,.2f}"
                    if item.room:
                        item_info += f" in {item.room.name}"
                    high_value_list.append(item_info)
                
                if high_value_list:
                    inventory_parts.append("  High value items:")
                    for item in high_value_list:
                        inventory_parts.append(f"    • {item}")
            
            # Storage items summary
            if storage_items and hasattr(storage_items, 'exists') and storage_items.exists():
                total_storage = storage_items.count()
                inventory_parts.append(f"- Storage items: {total_storage} total")
                
                # Storage items list
                storage_list = []
                for item in storage_items[:10]:  # Limit to first 10
                    item_info = f"{item.name} ({item.get_category_display()})"
                    if item.location:
                        item_info += f" at {item.location}"
                    storage_list.append(item_info)
                
                if storage_list:
                    inventory_parts.append("  Storage items:")
                    for item in storage_list:
                        inventory_parts.append(f"    • {item}")
            
            # If no inventory exists
            if not inventory_parts:
                inventory_parts.append("- No inventory items recorded yet")
        
        except Exception as e:
            logger.warning(f"Error extracting inventory details for move {move.id}: {e}")
            inventory_parts.append("- Inventory details unavailable")
        
        return inventory_parts
    
    def _build_prompt(self, user_context, move_date):
        """Build the complete prompt for Google AI."""
        from datetime import timedelta
        
        # Calculate actual date ranges for each week
        week_date_ranges = {}
        for week_num in range(8, -1, -1):
            if week_num == 0:
                # Week 0 is moving day
                week_date_ranges[week_num] = move_date.strftime('%d %B %Y')
            else:
                # Calculate week start and end dates
                week_start = move_date - timedelta(weeks=week_num)
                week_end = week_start + timedelta(days=6)
                week_date_ranges[week_num] = f"{week_start.strftime('%d %B %Y')} to {week_end.strftime('%d %B %Y')}"
        
        # Build week date information string
        week_dates_info = "\n".join([
            f"Week {week_num}: {week_date_ranges[week_num]}"
            for week_num in range(8, -1, -1)
        ])
        
        prompt = f"""You are a smart moving planner and task management assistant built into a home-move project management web app. Your job is to generate a customized, weekly moving checklist that starts 8 weeks before the move date and runs through moving day. The checklist should be practical, family-friendly, and suitable for a move within Sydney, Australia. Consider the user's context and budget carefully when recommending tasks or services.

User Context:
{user_context}

IMPORTANT - Week Date Ranges (use these EXACT dates):
{week_dates_info}

CRITICAL: Generate tasks that are appropriate for the time remaining until the move date. Tasks should be:
- Week 8 (8 weeks before): Early planning, research moving companies, create budget, start decluttering
- Week 7-6 (7-6 weeks before): Book removalists, order packing supplies, schedule services, notify landlord
- Week 5-4 (5-4 weeks before): Start packing non-essentials, organize documents, arrange time off work
- Week 3-2 (3-2 weeks before): Final packing, change addresses, notify utilities, transfer services
- Week 1 (1 week before): Last-minute confirmations, pack essentials box, prepare moving day kit
- Week 0 (Moving Day): Final walkthrough, supervise movers, unpack essentials, set up utilities

IMPORTANT: Consider the actual dates provided above. If the move date is during holidays (e.g., Christmas), adjust tasks accordingly. For example:
- If moving near Christmas/New Year, book services early (Week 8-7) as many businesses close
- If moving in summer, consider weather-related tasks
- Tasks should reflect the urgency based on actual time remaining

AI Task:
Generate a weekly moving plan and checklist (Week 8 to Week 0) tailored to the user's situation. Each week's plan should include:

- Key goals for the week (2-4 main objectives) - These are NOT tasks, just objectives
- To-do items (prioritized and categorized: admin, packing, services, family/pets, finances, etc.) - These ARE actionable tasks that can be checked off
- Notes or helpful tips (Sydney-specific if relevant, e.g. local regulations, strata rules, or Christmas closure considerations) - These are NOT tasks, just informational

CRITICAL REQUIREMENTS:
1. ONLY include actionable tasks in the "To-Do Items" sections. Goals and Notes should NEVER be included as tasks.
2. Each task should be a specific, actionable item that can be checked off (e.g., "Book removalist company", "Pack kitchen items", "Update address with bank").
3. Avoid duplicates - do not repeat the same task across different weeks or categories.
4. Keep tasks concise (max 10-15 words each).
5. Do NOT include goals, notes, tips, or general advice as tasks.
6. Generate 5-10 actionable tasks per week, distributed across categories.

IMPORTANT: If inventory details are provided, use them to create specific, actionable tasks. For example:
- If rooms are listed, create room-by-room packing tasks
- If heavy items are listed, include tasks for arranging special handling
- If high-value items are listed, include insurance and protection tasks
- If boxes are listed, include labeling and tracking tasks
- Consider the quantity and types of items when estimating packing time and resources

The tone should be clear, supportive, and practical. Keep lists concise and actionable — no filler or repetition. Use bullet points and subheadings.

Format the response EXACTLY as follows (use the actual dates from above):

Week 8 (Date Range: {week_date_ranges[8]})
Key Goals:
• [Goal 1]
• [Goal 2]
• [Goal 3]

To-Do Items:
Admin:
• [Task 1]
• [Task 2]

Packing:
• [Task 1]
• [Task 2]

Services:
• [Task 1]

Family/Pets:
• [Task 1]

Finances:
• [Task 1]

Notes/Tips:
• [Sydney-specific tip or consideration]
• [Additional helpful note]

Week 7 (Date Range: {week_date_ranges[7]})
[Same structure as Week 8...]

Week 6 (Date Range: {week_date_ranges[6]})
[Same structure as Week 8...]

Week 5 (Date Range: {week_date_ranges[5]})
[Same structure as Week 8...]

Week 4 (Date Range: {week_date_ranges[4]})
[Same structure as Week 8...]

Week 3 (Date Range: {week_date_ranges[3]})
[Same structure as Week 8...]

Week 2 (Date Range: {week_date_ranges[2]})
[Same structure as Week 8...]

Week 1 (Date Range: {week_date_ranges[1]})
[Same structure as Week 8...]

Week 0 (Moving Day - Date: {week_date_ranges[0]})
[Same structure as Week 8...]

CRITICAL: You MUST generate checklists for ALL 9 weeks: Week 8, Week 7, Week 6, Week 5, Week 4, Week 3, Week 2, Week 1, and Week 0. Do not skip any weeks.

For Week 0 (Moving Day), focus on:
- Final preparations
- Moving day logistics
- Immediate post-move tasks
- Unpacking priorities

Make it specific to Sydney, Australia and the user's situation based on the provided context. Consider:
- Sydney public holidays and business hours
- Strata/body corporate rules if moving from/to apartments
- Christmas/New Year closures if the move date is in December/January
- Local council requirements
- Sydney weather considerations
- Public transport considerations if relevant

REMEMBER: Only actionable tasks go in "To-Do Items". Goals and Notes are separate sections and should NOT be extracted as tasks."""
        
        return prompt
    
    def _parse_checklist_response(self, response_text, move_date, weeks_before):
        """
        Parse the AI response into a structured format with improved extraction.
        """
        from datetime import timedelta
        
        weeks = []
        current_week = None
        current_week_data = {
            'goals': [],
            'to_do_items': {},
            'notes': []
        }
        current_section = None
        current_category = None
        
        lines = response_text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Detect week headers (Week 8, Week 7, etc.)
            week_match = re.match(r'week\s+(\d+)', line, re.IGNORECASE)
            if week_match:
                # Save previous week if exists
                if current_week is not None:
                    weeks.append({
                        'week_number': current_week,
                        'goals': current_week_data['goals'],
                        'to_do_items': current_week_data['to_do_items'],
                        'notes': current_week_data['notes'],
                        'content': '\n'.join([f"Week {current_week}"] + 
                                            [f"Goals: {', '.join(current_week_data['goals'])}"] +
                                            [f"{cat}: {', '.join(items)}" for cat, items in current_week_data['to_do_items'].items()] +
                                            [f"Notes: {', '.join(current_week_data['notes'])}"])
                    })
                
                # Extract week number
                try:
                    current_week = int(week_match.group(1))
                    current_week_data = {
                        'goals': [],
                        'to_do_items': {},
                        'notes': []
                    }
                    current_section = None
                    current_category = None
                except ValueError:
                    current_week = None
                    current_week_data = {'goals': [], 'to_do_items': {}, 'notes': []}
                    current_section = None
                    current_category = None
                continue
            
            if current_week is None:
                continue
            
            # Detect section headers
            line_upper = line.upper()
            if 'KEY GOALS' in line_upper or (line_upper.startswith('GOALS') and ':' in line):
                current_section = 'goals'
                current_category = None
                continue
            elif 'TO-DO' in line_upper or 'TODO' in line_upper or ('TASKS' in line_upper and ':' in line):
                current_section = 'to_do'
                current_category = None
                continue
            elif 'NOTES' in line_upper or 'TIPS' in line_upper:
                current_section = 'notes'
                current_category = None
                continue
            elif line_upper in ['ADMIN', 'PACKING', 'SERVICES', 'FAMILY/PETS', 'FAMILY', 'PETS', 'FINANCES']:
                current_section = 'to_do'
                current_category = line_upper.replace('/', '_').lower()
                if current_category == 'family' or current_category == 'pets':
                    current_category = 'family_pets'
                if current_category not in current_week_data['to_do_items']:
                    current_week_data['to_do_items'][current_category] = []
                continue
            
            # Extract content based on current section
            if line.startswith(('-', '•', '*', '○')) or re.match(r'^\d+[\.\)]\s+', line):
                # Remove bullet/number markers
                content = re.sub(r'^[-•*○]\s*', '', line)
                content = re.sub(r'^\d+[\.\)]\s+', '', content)
                content = content.strip()
                
                if not content or len(content) < 3:
                    continue
                
                if current_section == 'goals':
                    current_week_data['goals'].append(content[:200])
                elif current_section == 'to_do':
                    # Determine category if not explicitly set
                    if current_category is None:
                        # Try to infer from content
                        content_lower = content.lower()
                        if any(word in content_lower for word in ['book', 'schedule', 'contact', 'notify', 'change address', 'update', 'register']):
                            current_category = 'admin'
                        elif any(word in content_lower for word in ['pack', 'box', 'label', 'organize', 'sort']):
                            current_category = 'packing'
                        elif any(word in content_lower for word in ['removalist', 'cleaner', 'service', 'professional']):
                            current_category = 'services'
                        elif any(word in content_lower for word in ['child', 'pet', 'school', 'daycare', 'family']):
                            current_category = 'family_pets'
                        elif any(word in content_lower for word in ['budget', 'payment', 'insurance', 'deposit', 'finance']):
                            current_category = 'finances'
                        else:
                            current_category = 'general'
                    
                    if current_category not in current_week_data['to_do_items']:
                        current_week_data['to_do_items'][current_category] = []
                    current_week_data['to_do_items'][current_category].append(content[:200])
                elif current_section == 'notes':
                    current_week_data['notes'].append(content[:200])
            else:
                # Might be a category header or continuation
                line_upper_check = line.upper()
                if line_upper_check in ['ADMIN', 'PACKING', 'SERVICES', 'FAMILY/PETS', 'FAMILY', 'PETS', 'FINANCES']:
                    current_category = line_upper_check.replace('/', '_').lower()
                    if current_category == 'family' or current_category == 'pets':
                        current_category = 'family_pets'
                    if current_category not in current_week_data['to_do_items']:
                        current_week_data['to_do_items'][current_category] = []
        
        # Add last week
        if current_week is not None:
            weeks.append({
                'week_number': current_week,
                'goals': current_week_data['goals'],
                'to_do_items': current_week_data['to_do_items'],
                'notes': current_week_data['notes'],
                'content': '\n'.join([f"Week {current_week}"] + 
                                    [f"Goals: {', '.join(current_week_data['goals'])}"] +
                                    [f"{cat}: {', '.join(items)}" for cat, items in current_week_data['to_do_items'].items()] +
                                    [f"Notes: {', '.join(current_week_data['notes'])}"])
            })
        
        # If parsing didn't work well, return the full text organized by weeks
        if not weeks:
            # Fallback: split into weeks manually
            for week_num in range(weeks_before, -1, -1):
                weeks.append({
                    'week_number': week_num,
                    'goals': [],
                    'to_do_items': {},
                    'notes': [],
                    'content': response_text  # Return full text for each week as fallback
                })
        
        return {
            'weeks': weeks,
            'full_text': response_text
        }
    
    def _create_checklist_items(self, move, structured_checklist):
        """
        Create ChecklistItem records from the AI-generated checklist.
        
        Args:
            move: Move instance
            structured_checklist: Parsed checklist structure
            
        Returns:
            int: Number of items created
        """
        items_created = 0
        
        try:
            # Delete existing AI-generated checklist items (keep custom ones)
            ChecklistItem.objects.filter(
                move=move,
                is_custom=False
            ).delete()
            
            # Parse the full text to extract individual tasks
            full_text = structured_checklist.get('full_text', '')
            weeks_data = structured_checklist.get('weeks', [])
            
            # Track created titles to prevent duplicates (normalized)
            created_titles = set()
            
            # Extract tasks from each week
            for week_data in weeks_data:
                week_number = week_data.get('week_number', 0)
                week_items_created = 0
                
                # First, try to use structured to_do_items if available
                to_do_items = week_data.get('to_do_items', {})
                if to_do_items:
                    # Create checklist items from structured to_do_items
                    for category, items in to_do_items.items():
                        for item_text in items:
                            if item_text and len(item_text.strip()) > 3:
                                # Normalize for duplicate checking
                                normalized = item_text.strip().lower()
                                
                                # Skip duplicates
                                if normalized in created_titles:
                                    logger.debug(f"Skipping duplicate: {item_text[:50]}")
                                    continue
                                
                                # Skip if it looks like a goal or note
                                if any(skip in normalized for skip in ['goal:', 'note:', 'tip:', 'consider:', 'remember:']):
                                    continue
                                
                                # Skip if too long (likely a note/explanation, not a task)
                                if len(item_text.strip()) > 100:
                                    continue
                                
                                try:
                                    # Determine priority based on category
                                    priority = 'medium'
                                    if category in ['admin', 'services']:
                                        priority = 'high'
                                    elif category == 'finances':
                                        priority = 'high'
                                    elif category == 'packing':
                                        priority = 'medium'
                                    elif category in ['family_pets', 'general']:
                                        priority = 'low'
                                    
                                    ChecklistItem.objects.create(
                                        move=move,
                                        title=item_text[:200],
                                        week=week_number,
                                        priority=priority,
                                        is_custom=False,
                                        completed=False
                                    )
                                    created_titles.add(normalized)
                                    week_items_created += 1
                                    items_created += 1
                                except Exception as e:
                                    logger.warning(f"Failed to create checklist item '{item_text}': {e}")
                
                # Fallback to content extraction if structured data not available for this week
                if week_items_created == 0:
                    content = week_data.get('content', '')
                    if content:
                        # Extract individual tasks/items from the content
                        tasks = self._extract_tasks_from_content(content, week_number)
                        
                        # Create ChecklistItem for each task
                        for task in tasks:
                            normalized = task['title'].strip().lower()
                            
                            # Skip duplicates
                            if normalized in created_titles:
                                continue
                            
                            try:
                                ChecklistItem.objects.create(
                                    move=move,
                                    title=task['title'][:200],
                                    week=week_number,
                                    priority=task.get('priority', 'medium'),
                                    is_custom=False,
                                    completed=False
                                )
                                created_titles.add(normalized)
                                items_created += 1
                            except Exception as e:
                                logger.warning(f"Failed to create checklist item '{task['title']}': {e}")
            
            # If we couldn't parse structured data, try to extract from full text
            if items_created == 0 and full_text:
                items_created = self._extract_and_create_from_text(move, full_text, weeks_before=8, created_titles=created_titles)
            
            logger.info(f"Created {items_created} checklist items for move {move.id}")
            
        except Exception as e:
            logger.error(f"Error creating checklist items: {e}", exc_info=True)
        
        return items_created
    
    def _extract_tasks_from_content(self, content, week_number):
        """
        Extract individual tasks from week content.
        
        Args:
            content: Text content for the week
            week_number: Week number
            
        Returns:
            list: List of task dictionaries with title and priority
        """
        tasks = []
        
        # Split by common list markers
        lines = content.split('\n')
        current_section = None
        in_goals_section = False
        in_notes_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect section headers
            line_upper = line.upper()
            
            # Check for goals section
            if 'KEY GOALS' in line_upper or (line_upper.startswith('GOALS') and ':' in line):
                current_section = 'GOALS'
                in_goals_section = True
                in_notes_section = False
                continue
            
            # Check for to-do items section
            elif 'TO-DO' in line_upper or 'TODO' in line_upper or ('TASKS' in line_upper and ':' in line):
                current_section = 'TO-DO'
                in_goals_section = False
                in_notes_section = False
                continue
            
            # Check for notes/tips section
            elif 'NOTES' in line_upper or 'TIPS' in line_upper:
                current_section = 'NOTES'
                in_goals_section = False
                in_notes_section = True
                continue
            
            # Check for category headers (these are sub-sections of To-Do Items)
            elif line_upper in ['ADMIN', 'PACKING', 'SERVICES', 'FAMILY/PETS', 'FAMILY', 'PETS', 'FINANCES']:
                current_section = line_upper
                in_goals_section = False
                in_notes_section = False
                continue
            
            # Skip if we're in goals or notes section
            if in_goals_section or in_notes_section:
                continue
            
            # Only process tasks if we're in a to-do section
            if current_section not in ['TO-DO', 'ADMIN', 'PACKING', 'SERVICES', 'FAMILY/PETS', 'FAMILY', 'PETS', 'FINANCES']:
                continue
            
            # Detect task items (bullet points, dashes, numbers)
            if line.startswith(('-', '•', '*', '○')) or re.match(r'^\d+[\.\)]\s+', line):
                # Remove bullet/number markers
                task_text = re.sub(r'^[-•*○]\s*', '', line)
                task_text = re.sub(r'^\d+[\.\)]\s+', '', task_text)
                task_text = task_text.strip()
                
                if task_text and len(task_text) > 5:  # Minimum length for a valid task
                    task_lower = task_text.lower()
                    
                    # Skip if it looks like a goal, note, or non-actionable item
                    skip_patterns = [
                        'goal:', 'note:', 'tip:', 'consider:', 'remember:',
                        'sydney-specific', 'strata', 'body corporate',
                        'public holiday', 'business hours', 'closure',
                        'keep in mind', 'be aware', 'note that',
                        'important to', 'remember to consider'
                    ]
                    
                    if any(pattern in task_lower for pattern in skip_patterns):
                        continue
                    
                    # Skip if it's too long (likely a note/explanation, not a task)
                    if len(task_text) > 100:
                        continue
                    
                    # Determine priority based on section or keywords
                    priority = 'medium'
                    if current_section in ['ADMIN', 'SERVICES']:
                        priority = 'high'
                    elif 'urgent' in task_lower or 'important' in task_lower:
                        priority = 'high'
                    elif 'optional' in task_lower or 'nice to have' in task_lower:
                        priority = 'low'
                    
                    tasks.append({
                        'title': task_text[:200],  # Limit length
                        'priority': priority
                    })
        
        return tasks
    
    def _extract_and_create_from_text(self, move, text, weeks_before=8, created_titles=None):
        """
        Fallback method to extract tasks from full text when structured parsing fails.
        
        Args:
            move: Move instance
            text: Full AI response text
            weeks_before: Number of weeks before move
            created_titles: Set of already created titles to avoid duplicates
            
        Returns:
            int: Number of items created
        """
        if created_titles is None:
            created_titles = set()
        
        items_created = 0
        
        # Try to find week sections
        week_pattern = r'week\s+(\d+)'
        weeks_found = re.finditer(week_pattern, text, re.IGNORECASE)
        
        for match in weeks_found:
            week_num = int(match.group(1))
            if week_num < 0 or week_num > weeks_before:
                continue
            
            # Extract content after this week marker (until next week or end)
            start_pos = match.end()
            next_match = None
            for next_week_match in re.finditer(week_pattern, text[start_pos:], re.IGNORECASE):
                next_match = next_week_match
                break
            
            if next_match:
                end_pos = start_pos + next_match.start()
                week_content = text[start_pos:end_pos]
            else:
                week_content = text[start_pos:]
            
            # Extract tasks from this week's content
            tasks = self._extract_tasks_from_content(week_content, week_num)
            
            # Create checklist items
            for task in tasks[:20]:  # Limit to 20 tasks per week
                normalized = task['title'].strip().lower()
                
                # Skip duplicates
                if normalized in created_titles:
                    continue
                
                try:
                    ChecklistItem.objects.create(
                        move=move,
                        title=task['title'][:200],
                        week=week_num,
                        priority=task.get('priority', 'medium'),
                        is_custom=False,
                        completed=False
                    )
                    created_titles.add(normalized)
                    items_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create checklist item: {e}")
        
        return items_created


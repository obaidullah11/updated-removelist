"""
Views for move management.
"""
import threading
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Move, MoveCollaborator, TaskAssignment, MoveExpense
from .serializers import (
    MoveCreateSerializer, MoveUpdateSerializer, 
    MoveDetailSerializer, MoveListSerializer,
    MoveCollaboratorSerializer, MoveCollaboratorInviteSerializer,
    TaskAssignmentSerializer, MoveExpenseSerializer, MoveExpenseCreateSerializer
)
from .utils import send_collaborator_invitation_email
from .services.moving_checklist_generator import MovingChecklistGenerator
from apps.common.utils import success_response, error_response, paginated_response
from apps.tasks.models import Task
from apps.timeline.models import ChecklistItem
from django.db import models

logger = logging.getLogger(__name__)

# Track ongoing task conversions to prevent duplicate runs
_conversion_in_progress = set()
_conversion_lock = threading.Lock()


def convert_checklist_items_to_tasks(move, max_retries=3, retry_delay=2):
    """
    Convert AI-generated ChecklistItems to Task objects with due dates.
    This creates Task objects from ChecklistItems so they appear in the timeline.
    
    Args:
        move: Move instance
        max_retries: Maximum number of retries if checklist items aren't found
        retry_delay: Delay in seconds between retries
    """
    from apps.tasks.models import Task
    from apps.timeline.models import ChecklistItem
    from datetime import timedelta, datetime
    from django.utils import timezone
    import time
    
    move_id_str = str(move.id)
    
    # Check if conversion is already in progress for this move
    with _conversion_lock:
        if move_id_str in _conversion_in_progress:
            logger.warning(f"Task conversion already in progress for move {move.id}. Skipping duplicate call.")
            return 0
        _conversion_in_progress.add(move_id_str)
    
    try:
        # Refresh move to get latest data
        move.refresh_from_db()
        move_date = move.move_date
        
        # Retry logic to handle timing issues
        checklist_items = None
        total_items = 0
        
        for attempt in range(max_retries):
            # Get all checklist items for this move (refresh from DB)
            checklist_items = ChecklistItem.objects.filter(move=move, is_custom=False)
            total_items = checklist_items.count()
            
            if total_items > 0:
                # Verify that items have week numbers set
                items_with_weeks = checklist_items.exclude(week__isnull=True).count()
                if items_with_weeks > 0:
                    logger.info(f"Found {total_items} checklist items ({items_with_weeks} with week numbers) for move {move.id}")
                    break
                else:
                    logger.warning(f"Found {total_items} checklist items but none have week numbers set for move {move.id}")
            
            if attempt < max_retries - 1:
                logger.info(f"Attempt {attempt + 1}: No checklist items found for move {move.id}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.warning(f"No checklist items found for move {move.id} after {max_retries} attempts. Tasks will be created after checklist generation completes.")
                return 0
        
        if total_items == 0 or checklist_items is None:
            logger.warning(f"No checklist items found for move {move.id}. Tasks will be created after checklist generation completes.")
            return 0
        
        tasks_created = 0
        tasks_skipped = 0
        tasks_failed = 0
        
        # Get all existing tasks for this move to avoid duplicates
        existing_tasks = Task.objects.filter(move=move)
        existing_task_titles = {task.title.lower().strip() for task in existing_tasks}
        
        # Group checklist items by week for logging
        items_by_week = {}
        for item in checklist_items:
            week = item.week if item.week is not None else -1
            if week not in items_by_week:
                items_by_week[week] = 0
            items_by_week[week] += 1
        
        logger.info(f"Processing checklist items for move {move.id}: {items_by_week}")
        
        for item in checklist_items:
            # Normalize title for comparison
            normalized_title = item.title.lower().strip()
            
            # Check if task already exists (case-insensitive, trimmed)
            if normalized_title in existing_task_titles:
                # Find the existing task and update if needed
                existing_task = existing_tasks.filter(title__iexact=item.title).first()
                if existing_task:
                    # Update existing task's due_date if it doesn't have one or if week changed
                    week_num = item.week
                    if week_num is not None:
                        if week_num == 0:
                            new_due_date = timezone.make_aware(
                                datetime.combine(move_date, datetime.min.time())
                            )
                        else:
                            weeks_before = timedelta(weeks=week_num)
                            week_start = move_date - weeks_before
                            new_due_date = week_start + timedelta(days=3)
                            new_due_date = timezone.make_aware(
                                datetime.combine(new_due_date, datetime.min.time())
                            )
                        
                        # Only update if due_date is missing or significantly different (more than 1 day)
                        if not existing_task.due_date:
                            existing_task.due_date = new_due_date
                            existing_task.save(update_fields=['due_date'])
                            logger.debug(f"Updated due_date for existing task: {item.title} (Week {week_num})")
                        elif existing_task.due_date:
                            # Check if the due date is more than 1 day off from expected
                            expected_date = new_due_date.date()
                            actual_date = existing_task.due_date.date()
                            days_diff = abs((expected_date - actual_date).days)
                            if days_diff > 1:
                                existing_task.due_date = new_due_date
                                existing_task.save(update_fields=['due_date'])
                                logger.debug(f"Corrected due_date for existing task: {item.title} (Week {week_num}, was {actual_date}, now {expected_date})")
                tasks_skipped += 1
                continue
            
            # Calculate due date based on week number
            week_num = item.week
            if week_num is None:
                logger.warning(f"Checklist item '{item.title}' has no week number. Skipping task creation.")
                tasks_failed += 1
                continue
                
            if week_num == 0:
                # Moving day - due date is the move date
                due_date = timezone.make_aware(
                    datetime.combine(move_date, datetime.min.time())
                )
            else:
                # Calculate date for this week (middle of the week)
                weeks_before = timedelta(weeks=week_num)
                week_start = move_date - weeks_before
                # Set due date to middle of the week (3 days into the week)
                due_date = week_start + timedelta(days=3)
                due_date = timezone.make_aware(
                    datetime.combine(due_date, datetime.min.time())
                )
            
            # Determine task category from checklist item title/content
            category = 'general'
            location = 'current'
            title_lower = item.title.lower()
            
            # Map categories based on keywords in title
            if any(word in title_lower for word in ['pack', 'box', 'organize items', 'label']):
                category = 'packing'
            elif any(word in title_lower for word in ['utility', 'electricity', 'gas', 'water', 'internet', 'phone', 'power']):
                category = 'utilities'
                if 'new' in title_lower or 'transfer' in title_lower or 'connect' in title_lower or 'set up' in title_lower:
                    location = 'new'
            elif any(word in title_lower for word in ['address', 'change address', 'update address', 'notify', 'bank', 'update']):
                category = 'address_change'
                if 'bank' in title_lower or 'insurance' in title_lower or 'financial' in title_lower:
                    location = 'utilities'
            elif any(word in title_lower for word in ['clean', 'cleaning', 'walkthrough', 'inspect']):
                category = 'cleaning'
            elif any(word in title_lower for word in ['insurance']):
                category = 'insurance'
            elif any(word in title_lower for word in ['first night', 'unpack', 'essentials', 'overnight']):
                category = 'first_night'
                if 'unpack' in title_lower or 'new' in title_lower:
                    location = 'new'
            elif any(word in title_lower for word in ['council', 'permit', 'registration']):
                category = 'council'
            elif any(word in title_lower for word in ['book', 'schedule', 'hire', 'removalist', 'mover']):
                category = 'general'
                location = 'current'
            elif any(word in title_lower for word in ['budget', 'finance', 'payment', 'deposit']):
                category = 'general'
                location = 'current'
            
            try:
                # Double-check that task doesn't exist (race condition protection)
                final_check = Task.objects.filter(
                    move=move,
                    title__iexact=item.title
                ).first()
                
                if final_check:
                    logger.debug(f"Task '{item.title}' already exists, skipping creation (race condition avoided)")
                    tasks_skipped += 1
                    continue
                
                task = Task.objects.create(
                    move=move,
                    title=item.title,
                    category=category,
                    priority=item.priority,
                    location=location,
                    due_date=due_date,
                    assigned_to=move.user,
                    completed=item.completed,  # Sync completion status
                    description=f"Generated from AI checklist (Week {week_num})"
                )
                tasks_created += 1
                # Add to existing set to prevent duplicates in same run
                existing_task_titles.add(normalized_title)
                
                # Verify the due_date was set correctly
                if task.due_date:
                    days_from_move = (move_date - task.due_date.date()).days
                    calculated_week = round((days_from_move + 3) / 7)
                    logger.debug(
                        f"Created task: {item.title} "
                        f"(Checklist Week: {week_num}, Due: {task.due_date.date()}, "
                        f"Days from move: {days_from_move}, Calculated week: {calculated_week})"
                    )
                else:
                    logger.warning(f"Task '{item.title}' created without due_date!")
            except Exception as e:
                tasks_failed += 1
                logger.error(f"Failed to create task from checklist item '{item.title}': {e}", exc_info=True)
        
        # Log summary by week
        created_tasks = Task.objects.filter(move=move).exclude(due_date__isnull=True)
        tasks_by_week = {}
        for task in created_tasks:
            # Calculate week from due_date for verification
            if task.due_date:
                days_diff = (move_date - task.due_date.date()).days
                week = max(0, min(8, round((days_diff + 3) / 7)))
                if week not in tasks_by_week:
                    tasks_by_week[week] = 0
                tasks_by_week[week] += 1
        
        logger.info(
            f"Task conversion complete for move {move.id}: "
            f"{tasks_created} created, {tasks_skipped} skipped, {tasks_failed} failed "
            f"(from {total_items} checklist items). "
            f"Tasks by week: {tasks_by_week}"
        )
        
        return tasks_created
    finally:
        # Remove from in-progress set
        with _conversion_lock:
            _conversion_in_progress.discard(move_id_str)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_move(request):
    """
    Create a new move and automatically generate AI-powered moving checklist and inventory from floor plans.
    """
    serializer = MoveCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        move = serializer.save()
        
        # Check if AI services are available before starting background threads
        checklist_available = False
        floor_plan_analyzer_available = False
        
        try:
            generator = MovingChecklistGenerator()
            if generator.model:
                checklist_available = True
                logger.info(f"AI checklist generator is available for move {move.id}")
            else:
                logger.warning(f"AI checklist generator not available for move {move.id} - model not initialized")
        except Exception as e:
            logger.error(f"Failed to initialize checklist generator for move {move.id}: {e}", exc_info=True)
        
        if move.current_property_floor_map or move.new_property_floor_map:
            try:
                from apps.inventory.services.ai_floor_plan_analyzer import AIFloorPlanAnalyzer
                analyzer = AIFloorPlanAnalyzer()
                if analyzer.model:
                    floor_plan_analyzer_available = True
                    logger.info(f"AI floor plan analyzer is available for move {move.id}")
                else:
                    logger.warning(f"AI floor plan analyzer not available for move {move.id} - model not initialized")
            except Exception as e:
                logger.error(f"Failed to initialize floor plan analyzer for move {move.id}: {e}", exc_info=True)
        
        # Automatically generate moving checklist in the background
        def generate_checklist_async():
            """Generate checklist asynchronously without blocking the response."""
            try:
                logger.info(f"Starting automatic checklist generation for move {move.id}")
                generator = MovingChecklistGenerator()
                
                if not generator.model:
                    error_msg = "Google AI model not initialized. Check GOOGLE_AI_API_KEY in settings."
                    logger.error(f"Checklist generation failed for move {move.id}: {error_msg}")
                    return
                
                result = generator.generate_checklist(move)
                
                if result.get('success'):
                    items_created = result.get('items_created', 0)
                    logger.info(f"Checklist generated successfully for move {move.id}: {items_created} items created")
                    
                    # Wait a moment for database to be updated and ensure transaction is committed
                    import time
                    time.sleep(2)  # Increased wait time to ensure DB commit
                    
                    # Refresh move object to get latest data
                    move.refresh_from_db()
                    
                    # Verify checklist items were created with week numbers
                    from apps.timeline.models import ChecklistItem
                    checklist_items = ChecklistItem.objects.filter(move=move, is_custom=False)
                    items_with_weeks = checklist_items.exclude(week__isnull=True).count()
                    
                    if items_with_weeks == 0 and checklist_items.count() > 0:
                        logger.warning(f"Checklist items exist but none have week numbers for move {move.id}. This may indicate a parsing issue.")
                    
                    # Convert checklist items to tasks with due dates
                    try:
                        tasks_created = convert_checklist_items_to_tasks(move, max_retries=3, retry_delay=2)
                        if tasks_created > 0:
                            logger.info(f"Successfully converted {tasks_created} checklist items to tasks for move {move.id}")
                        else:
                            # Check if checklist items exist but conversion failed
                            checklist_count = ChecklistItem.objects.filter(move=move, is_custom=False).count()
                            task_count = Task.objects.filter(move=move).count()
                            logger.warning(
                                f"No new tasks were created from checklist items for move {move.id}. "
                                f"Checklist items: {checklist_count}, Existing tasks: {task_count}"
                            )
                    except Exception as e:
                        logger.error(f"Failed to convert checklist items to tasks for move {move.id}: {e}", exc_info=True)
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Checklist generation failed for move {move.id}: {error_msg}")
                    
                    # Log specific guidance for leaked API key
                    if 'leaked' in error_msg.lower() or 'reported as leaked' in error_msg.lower():
                        logger.error("URGENT: API key has been leaked. Generate a new key at https://aistudio.google.com/apikey")
                    
                    # Try to convert any existing checklist items to tasks even if generation failed
                    try:
                        import time
                        time.sleep(2)  # Wait for any pending DB operations
                        move.refresh_from_db()
                        existing_items = ChecklistItem.objects.filter(move=move, is_custom=False).count()
                        if existing_items > 0:
                            logger.info(f"Found {existing_items} existing checklist items, attempting to convert to tasks...")
                            tasks_created = convert_checklist_items_to_tasks(move, max_retries=2, retry_delay=1)
                            if tasks_created > 0:
                                logger.info(f"Converted {tasks_created} existing checklist items to tasks")
                    except Exception as e:
                        logger.error(f"Failed to convert existing checklist items: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error generating checklist for move {move.id}: {e}", exc_info=True)
        
        # Automatically analyze floor plans and create inventory in the background
        def analyze_floor_plans_async():
            """Analyze floor plans and create inventory asynchronously without blocking the response."""
            try:
                from apps.inventory.services.ai_floor_plan_analyzer import AIFloorPlanAnalyzer
                from PIL import Image
                
                analyzer = AIFloorPlanAnalyzer()
                
                if not analyzer.model:
                    error_msg = "Google AI Vision model not initialized. Check GOOGLE_AI_API_KEY in settings."
                    logger.error(f"AI floor plan analyzer not available for move {move.id}: {error_msg}")
                    return
                
                # Analyze current property floor plan if provided
                if move.current_property_floor_map:
                    floor_plan_file = None
                    try:
                        logger.info(f"Starting floor plan analysis for current property (move {move.id})")
                        # Use Django's file storage to get the file
                        floor_plan_file = move.current_property_floor_map
                        floor_plan_file.open('rb')
                        image = Image.open(floor_plan_file)
                        # Convert to RGB if necessary
                        if image.mode != 'RGB':
                            image = image.convert('RGB')
                        
                        result = analyzer.analyze_floor_plan_and_generate_inventory(
                            move=move,
                            floor_plan_image=image,
                            is_new_property=False
                        )
                        
                        if result.get('success'):
                            inventory_data = result.get('inventory', {})
                            logger.info(f"Inventory created from current property floor plan for move {move.id}: "
                                      f"{inventory_data.get('rooms_created', 0)} rooms, "
                                      f"{inventory_data.get('items_created', 0)} items, "
                                      f"{inventory_data.get('boxes_created', 0)} boxes, "
                                      f"{inventory_data.get('heavy_items_created', 0)} heavy items")
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            logger.warning(f"Floor plan analysis failed for current property (move {move.id}): {error_msg}")
                            
                            # Log specific guidance for leaked API key
                            if 'leaked' in error_msg.lower() or 'reported as leaked' in error_msg.lower():
                                logger.error("URGENT: API key has been leaked. Generate a new key at https://aistudio.google.com/apikey")
                    except Exception as e:
                        logger.error(f"Error analyzing current property floor plan for move {move.id}: {e}", exc_info=True)
                    finally:
                        # Close the file if it was opened
                        if floor_plan_file and hasattr(floor_plan_file, 'closed') and not floor_plan_file.closed:
                            try:
                                floor_plan_file.close()
                            except Exception:
                                pass
                
                # Analyze new property floor plan if provided
                if move.new_property_floor_map:
                    floor_plan_file = None
                    try:
                        logger.info(f"Starting floor plan analysis for new property (move {move.id})")
                        # Use Django's file storage to get the file
                        floor_plan_file = move.new_property_floor_map
                        floor_plan_file.open('rb')
                        image = Image.open(floor_plan_file)
                        # Convert to RGB if necessary
                        if image.mode != 'RGB':
                            image = image.convert('RGB')
                        
                        result = analyzer.analyze_floor_plan_and_generate_inventory(
                            move=move,
                            floor_plan_image=image,
                            is_new_property=True
                        )
                        
                        if result.get('success'):
                            inventory_data = result.get('inventory', {})
                            logger.info(f"Inventory created from new property floor plan for move {move.id}: "
                                      f"{inventory_data.get('rooms_created', 0)} rooms, "
                                      f"{inventory_data.get('items_created', 0)} items, "
                                      f"{inventory_data.get('boxes_created', 0)} boxes, "
                                      f"{inventory_data.get('heavy_items_created', 0)} heavy items")
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            logger.warning(f"Floor plan analysis failed for new property (move {move.id}): {error_msg}")
                            
                            # Log specific guidance for leaked API key
                            if 'leaked' in error_msg.lower() or 'reported as leaked' in error_msg.lower():
                                logger.error("URGENT: API key has been leaked. Generate a new key at https://aistudio.google.com/apikey")
                    except Exception as e:
                        logger.error(f"Error analyzing new property floor plan for move {move.id}: {e}", exc_info=True)
                    finally:
                        # Close the file if it was opened
                        if floor_plan_file and hasattr(floor_plan_file, 'closed') and not floor_plan_file.closed:
                            try:
                                floor_plan_file.close()
                            except Exception:
                                pass
                        
            except ImportError as e:
                logger.warning(f"Floor plan analyzer not available: {e}")
            except Exception as e:
                logger.error(f"Error in floor plan analysis for move {move.id}: {e}", exc_info=True)
        
        # Start checklist generation in a background thread if available
        if checklist_available:
            checklist_thread = threading.Thread(target=generate_checklist_async, daemon=True)
            checklist_thread.start()
            logger.info(f"Started background checklist generation thread for move {move.id}")
        else:
            logger.warning(f"Skipping checklist generation for move {move.id} - AI service not available")
            # Try to convert any existing checklist items to tasks even if AI is not available
            try:
                import time
                time.sleep(3)  # Wait a bit longer in case checklist items are being created
                move.refresh_from_db()
                existing_items = ChecklistItem.objects.filter(move=move, is_custom=False).count()
                if existing_items > 0:
                    logger.info(f"Found {existing_items} existing checklist items, converting to tasks...")
                    tasks_created = convert_checklist_items_to_tasks(move, max_retries=2, retry_delay=1)
                    if tasks_created > 0:
                        logger.info(f"Converted {tasks_created} existing checklist items to tasks")
            except Exception as e:
                logger.error(f"Failed to convert existing checklist items: {e}", exc_info=True)
        
        # Start floor plan analysis in a background thread if floor plans are provided and analyzer is available
        if (move.current_property_floor_map or move.new_property_floor_map) and floor_plan_analyzer_available:
            floor_plan_thread = threading.Thread(target=analyze_floor_plans_async, daemon=True)
            floor_plan_thread.start()
            logger.info(f"Started background floor plan analysis thread for move {move.id}")
        elif move.current_property_floor_map or move.new_property_floor_map:
            logger.warning(f"Skipping floor plan analysis for move {move.id} - AI service not available")
        
        # Return detailed move data
        detail_serializer = MoveDetailSerializer(move)
        
        # Build response message based on what's actually happening
        message = "Move created successfully."
        warnings = []
        
        if checklist_available:
            message += " AI checklist is being generated in the background."
        else:
            warnings.append("AI checklist generation is not available. Please check your Google AI API key configuration.")
        
        if move.current_property_floor_map or move.new_property_floor_map:
            if floor_plan_analyzer_available:
                message += " Floor plan analysis and inventory generation is in progress."
            else:
                warnings.append("AI floor plan analysis is not available. Please check your Google AI API key configuration.")
        
        # Include warnings in response if any
        response_data = detail_serializer.data
        if warnings:
            response_data['ai_warnings'] = warnings
        
        return success_response(
            message,
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Move creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_move(request, move_id):
    """
    Get move details by ID.
    """
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    # Update progress before returning
    move.calculate_progress()
    
    serializer = MoveDetailSerializer(move)
    
    return success_response(
        "Move details retrieved",
        serializer.data
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_moves(request):
    """
    Get all moves for the authenticated user.
    """
    moves = Move.objects.filter(user=request.user)
    
    # Update progress for all moves
    for move in moves:
        move.calculate_progress()
    
    # Check if pagination is requested
    if request.GET.get('page'):
        return paginated_response(
            moves, 
            MoveListSerializer, 
            request, 
            "Moves retrieved successfully"
        )
    
    # Return all moves without pagination
    serializer = MoveListSerializer(moves, many=True)
    
    return success_response(
        "Moves retrieved successfully",
        serializer.data
    )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_move(request, move_id):
    """
    Update a move.
    """
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    # Check if move date is being changed and if user has permission
    if 'move_date' in request.data and request.data['move_date'] != str(move.move_date):
        if not request.user.can_change_date():
            return error_response(
                "Date change not allowed",
                {'detail': ['You have reached your date change limit for your current plan']},
                status.HTTP_403_FORBIDDEN
            )
    
    serializer = MoveUpdateSerializer(move, data=request.data, partial=True)
    
    if serializer.is_valid():
        # If date is being changed, increment the user's date changes counter
        if 'move_date' in request.data and request.data['move_date'] != str(move.move_date):
            request.user.date_changes_used += 1
            request.user.save()
        
        serializer.save()
        
        # Return updated move data
        detail_serializer = MoveDetailSerializer(move)
        
        return success_response(
            "Move updated successfully",
            detail_serializer.data
        )
    
    return error_response(
        "Move update failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_move(request, move_id):
    """
    Delete a move.
    """
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    # Check if move can be deleted (not in progress or completed)
    if move.status in ['in_progress', 'completed']:
        return error_response(
            "Cannot delete move",
            {'detail': ['Cannot delete a move that is in progress or completed']},
            status.HTTP_400_BAD_REQUEST
        )
    
    move.delete()
    
    return success_response("Move deleted successfully")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_collaborator(request):
    """
    Invite a collaborator to a move.
    """
    serializer = MoveCollaboratorInviteSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        collaborator = serializer.save()
        
        # Send invitation email
        email_sent = send_collaborator_invitation_email(collaborator)
        
        response_serializer = MoveCollaboratorSerializer(collaborator)
        message = "Collaborator invited successfully"
        if email_sent:
            message += " and invitation email sent"
        else:
            message += " but failed to send invitation email"
            
        return success_response(
            message,
            response_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Invitation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_invitation(request):
    """
    Accept a collaborator invitation using invitation token.
    """
    invitation_token = request.data.get('invitation_token')
    
    if not invitation_token:
        return error_response(
            "Invitation token is required",
            {"invitation_token": ["This field is required."]},
            status.HTTP_400_BAD_REQUEST
        )
    
    try:
        collaborator = MoveCollaborator.objects.get(
            invitation_token=invitation_token,
            is_active=True,
            accepted_at__isnull=True
        )
        
        # Link collaborator to the current user
        collaborator.user = request.user
        collaborator.accepted_at = timezone.now()
        collaborator.save()
        
        # Return move details
        move_serializer = MoveDetailSerializer(collaborator.move)
        return success_response(
            "Invitation accepted successfully",
            {
                "collaborator": MoveCollaboratorSerializer(collaborator).data,
                "move": move_serializer.data
            },
            status.HTTP_200_OK
        )
        
    except MoveCollaborator.DoesNotExist:
        return error_response(
            "Invalid or expired invitation token",
            {"invitation_token": ["Invalid invitation token."]},
            status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
def get_invitation_details(request, invitation_token):
    """
    Get invitation details using invitation token (no auth required).
    """
    try:
        collaborator = MoveCollaborator.objects.get(
            invitation_token=invitation_token,
            is_active=True,
            accepted_at__isnull=True
        )
        
        # Return limited move and collaborator details
        return success_response(
            "Invitation details retrieved",
            {
                "collaborator_name": f"{collaborator.first_name} {collaborator.last_name}".strip(),
                "role": collaborator.role,
                "move": {
                    "move_date": collaborator.move.move_date,
                    "current_location": collaborator.move.current_location,
                    "destination_location": collaborator.move.destination_location,
                    "owner_name": f"{collaborator.move.user.first_name} {collaborator.move.user.last_name}".strip()
                }
            }
        )
        
    except MoveCollaborator.DoesNotExist:
        return error_response(
            "Invalid or expired invitation token",
            {"invitation_token": ["Invalid invitation token."]},
            status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_collaborator_moves(request):
    """
    Get all moves where the user is a collaborator.
    """
    collaborations = MoveCollaborator.objects.filter(
        user=request.user,
        is_active=True,
        accepted_at__isnull=False
    ).select_related('move')
    
    moves_data = []
    for collaboration in collaborations:
        move_serializer = MoveListSerializer(collaboration.move)
        move_data = move_serializer.data
        move_data['collaboration_role'] = collaboration.role
        move_data['collaboration_permissions'] = collaboration.permissions
        moves_data.append(move_data)
    
    return success_response(
        "Collaborator moves retrieved successfully",
        moves_data
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_collaborators(request, move_id):
    """
    Get all collaborators for a move.
    """
    move = get_object_or_404(Move, id=move_id, user=request.user)
    collaborators = MoveCollaborator.objects.filter(move=move, is_active=True)
    
    serializer = MoveCollaboratorSerializer(collaborators, many=True)
    return success_response(
        "Collaborators retrieved successfully",
        serializer.data
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_collaborator(request, collaborator_id):
    """
    Remove a collaborator from a move.
    """
    collaborator = get_object_or_404(
        MoveCollaborator, 
        id=collaborator_id, 
        move__user=request.user
    )
    
    # Soft delete - mark as inactive
    collaborator.is_active = False
    collaborator.save()
    
    return success_response("Collaborator removed successfully")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_task(request):
    """
    Assign a task to a collaborator.
    """
    serializer = TaskAssignmentSerializer(data=request.data)
    
    if serializer.is_valid():
        # Verify that the user owns the move
        timeline_event = serializer.validated_data['timeline_event']
        if timeline_event.move.user != request.user:
            return error_response(
                "Permission denied",
                {'detail': ['You can only assign tasks for your own moves']},
                status.HTTP_403_FORBIDDEN
            )
        
        # Verify that the collaborator belongs to the same move
        collaborator = serializer.validated_data['collaborator']
        if collaborator.move != timeline_event.move:
            return error_response(
                "Invalid assignment",
                {'detail': ['Collaborator must belong to the same move as the task']},
                status.HTTP_400_BAD_REQUEST
            )
        
        assignment = serializer.save(assigned_by=request.user)
        
        return success_response(
            "Task assigned successfully",
            TaskAssignmentSerializer(assignment).data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Task assignment failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_assignments(request, move_id):
    """
    Get all task assignments for a move.
    """
    move = get_object_or_404(Move, id=move_id, user=request.user)
    assignments = TaskAssignment.objects.filter(
        timeline_event__move=move
    ).select_related('collaborator', 'timeline_event')
    
    serializer = TaskAssignmentSerializer(assignments, many=True)
    return success_response(
        "Task assignments retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_moving_checklist(request, move_id):
    """
    Generate a personalized weekly moving checklist using Google AI.
    Also converts checklist items to tasks with due dates.
    
    POST /move/generate-checklist/{move_id}/
    """
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    # Initialize the checklist generator
    generator = MovingChecklistGenerator()
    
    # Generate the checklist
    result = generator.generate_checklist(move)
    
    if result.get('success'):
        # Convert checklist items to tasks
        try:
            import time
            time.sleep(2)  # Brief wait for DB to update
            move.refresh_from_db()
            tasks_created = convert_checklist_items_to_tasks(move, max_retries=3, retry_delay=1)
            logger.info(f"Converted {tasks_created} checklist items to tasks for move {move.id}")
        except Exception as e:
            logger.error(f"Failed to convert checklist items to tasks: {e}", exc_info=True)
        
        return success_response(
            "Moving checklist generated successfully",
            {
                'move_id': result['move_id'],
                'move_date': result['move_date'],
                'weeks_until_move': result['weeks_until_move'],
                'checklist': result['checklist'],
                'tasks_created': tasks_created if 'tasks_created' in locals() else 0
            },
            status.HTTP_200_OK
        )
    else:
        return error_response(
            "Failed to generate checklist",
            {'error': result.get('error', 'Unknown error occurred')},
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_checklist_to_tasks(request, move_id):
    """
    Manually convert checklist items to tasks for a move.
    This is useful if checklist items exist but tasks weren't created.
    
    POST /move/convert-checklist-to-tasks/{move_id}/
    """
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    try:
        tasks_created = convert_checklist_items_to_tasks(move)
        
        if tasks_created > 0:
            return success_response(
                f"Successfully converted {tasks_created} checklist items to tasks",
                {'tasks_created': tasks_created},
                status.HTTP_200_OK
            )
        else:
            # Check if checklist items exist
            from apps.timeline.models import ChecklistItem
            checklist_count = ChecklistItem.objects.filter(move=move, is_custom=False).count()
            
            if checklist_count == 0:
                return error_response(
                    "No checklist items found",
                    {'error': 'No checklist items exist for this move. Please generate checklist first.'},
                    status.HTTP_400_BAD_REQUEST
                )
            else:
                return success_response(
                    "No new tasks created",
                    {
                        'tasks_created': 0,
                        'message': f'Found {checklist_count} checklist items, but tasks may already exist or conversion failed.'
                    },
                    status.HTTP_200_OK
                )
    except Exception as e:
        logger.error(f"Error converting checklist to tasks for move {move.id}: {e}", exc_info=True)
        return error_response(
            "Failed to convert checklist to tasks",
            {'error': str(e)},
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_move_expenses(request, move_id):
    """Get all expenses for a move."""
    move = get_object_or_404(Move, id=move_id, user=request.user)
    expenses = MoveExpense.objects.filter(move=move)
    serializer = MoveExpenseSerializer(expenses, many=True, context={'request': request})
    
    # Calculate totals
    total_spent = expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    budget = move.estimated_budget or 0
    remaining = float(budget) - float(total_spent)
    
    return success_response(
        "Expenses retrieved successfully",
        {
            'expenses': serializer.data,
            'summary': {
                'total_spent': float(total_spent),
                'budget': float(budget),
                'remaining': float(remaining),
                'percentage_used': (float(total_spent) / float(budget) * 100) if budget > 0 else 0
            }
        },
        status.HTTP_200_OK
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_move_expense(request):
    """Create a new expense for a move."""
    serializer = MoveExpenseCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        expense = serializer.save()
        response_serializer = MoveExpenseSerializer(expense, context={'request': request})
        return success_response(
            "Expense created successfully",
            response_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Failed to create expense",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_move_expense(request, expense_id):
    """Update an existing expense."""
    expense = get_object_or_404(MoveExpense, id=expense_id)
    
    # Verify ownership
    if expense.move.user != request.user:
        return error_response(
            "Permission denied",
            {'error': 'You can only update expenses for your own moves.'},
            status.HTTP_403_FORBIDDEN
        )
    
    serializer = MoveExpenseCreateSerializer(expense, data=request.data, context={'request': request}, partial=True)
    
    if serializer.is_valid():
        expense = serializer.save()
        response_serializer = MoveExpenseSerializer(expense, context={'request': request})
        return success_response(
            "Expense updated successfully",
            response_serializer.data,
            status.HTTP_200_OK
        )
    
    return error_response(
        "Failed to update expense",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_move_expense(request, expense_id):
    """Delete an expense."""
    expense = get_object_or_404(MoveExpense, id=expense_id)
    
    # Verify ownership
    if expense.move.user != request.user:
        return error_response(
            "Permission denied",
            {'error': 'You can only delete expenses for your own moves.'},
            status.HTTP_403_FORBIDDEN
        )
    
    expense.delete()
    return success_response(
        "Expense deleted successfully",
        None,
        status.HTTP_200_OK
    )

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
from .models import Move, MoveCollaborator, TaskAssignment
from .serializers import (
    MoveCreateSerializer, MoveUpdateSerializer, 
    MoveDetailSerializer, MoveListSerializer,
    MoveCollaboratorSerializer, MoveCollaboratorInviteSerializer,
    TaskAssignmentSerializer
)
from .utils import send_collaborator_invitation_email
from .services.moving_checklist_generator import MovingChecklistGenerator
from apps.common.utils import success_response, error_response, paginated_response

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_move(request):
    """
    Create a new move and automatically generate AI-powered moving checklist and inventory from floor plans.
    """
    serializer = MoveCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        move = serializer.save()
        
        # Automatically generate moving checklist in the background
        def generate_checklist_async():
            """Generate checklist asynchronously without blocking the response."""
            try:
                logger.info(f"Starting automatic checklist generation for move {move.id}")
                generator = MovingChecklistGenerator()
                result = generator.generate_checklist(move)
                
                if result.get('success'):
                    logger.info(f"Checklist generated successfully for move {move.id}")
                else:
                    logger.warning(f"Checklist generation failed for move {move.id}: {result.get('error')}")
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
                    logger.warning(f"AI floor plan analyzer not available for move {move.id}")
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
                            logger.warning(f"Floor plan analysis failed for current property (move {move.id}): "
                                         f"{result.get('error')}")
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
                            logger.warning(f"Floor plan analysis failed for new property (move {move.id}): "
                                         f"{result.get('error')}")
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
        
        # Start checklist generation in a background thread
        checklist_thread = threading.Thread(target=generate_checklist_async, daemon=True)
        checklist_thread.start()
        logger.info(f"Started background checklist generation thread for move {move.id}")
        
        # Start floor plan analysis in a background thread if floor plans are provided
        if move.current_property_floor_map or move.new_property_floor_map:
            floor_plan_thread = threading.Thread(target=analyze_floor_plans_async, daemon=True)
            floor_plan_thread.start()
            logger.info(f"Started background floor plan analysis thread for move {move.id}")
        
        # Return detailed move data
        detail_serializer = MoveDetailSerializer(move)
        
        message = "Move created successfully. AI checklist is being generated in the background."
        if move.current_property_floor_map or move.new_property_floor_map:
            message += " Floor plan analysis and inventory generation is in progress."
        
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
    
    POST /move/generate-checklist/{move_id}/
    """
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    # Initialize the checklist generator
    generator = MovingChecklistGenerator()
    
    # Generate the checklist
    result = generator.generate_checklist(move)
    
    if result.get('success'):
        return success_response(
            "Moving checklist generated successfully",
            {
                'move_id': result['move_id'],
                'move_date': result['move_date'],
                'weeks_until_move': result['weeks_until_move'],
                'checklist': result['checklist']
            },
            status.HTTP_200_OK
        )
    else:
        return error_response(
            "Failed to generate checklist",
            {'error': result.get('error', 'Unknown error occurred')},
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

"""
Views for timeline and task management.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from collections import defaultdict
from .models import TimelineEvent, ChecklistItem, ChecklistTemplate
from .serializers import (
    TimelineEventSerializer, TimelineEventUpdateSerializer,
    ChecklistItemSerializer, ChecklistItemCreateSerializer,
    ChecklistItemUpdateSerializer, ChecklistWeekSerializer
)
from apps.moves.models import Move
from apps.common.utils import success_response, error_response, paginated_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_timeline_events(request):
    """
    Get timeline events for a specific move.
    """
    move_id = request.GET.get('move_id')
    
    if not move_id:
        return error_response(
            "Move ID required",
            {'move_id': ['This parameter is required']},
            status.HTTP_400_BAD_REQUEST
        )
    
    # Verify move belongs to user
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    # Get timeline events for this move
    events = TimelineEvent.objects.filter(move=move)
    
    # Check if pagination is requested
    if request.GET.get('page'):
        return paginated_response(
            events,
            TimelineEventSerializer,
            request,
            "Timeline events retrieved"
        )
    
    # Return all events without pagination
    serializer = TimelineEventSerializer(events, many=True)
    
    return success_response(
        "Timeline events retrieved",
        serializer.data
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_timeline_event(request, event_id):
    """
    Update a timeline event (mainly completion status).
    """
    event = get_object_or_404(TimelineEvent, id=event_id, move__user=request.user)
    
    serializer = TimelineEventUpdateSerializer(event, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        
        # Return updated event data
        detail_serializer = TimelineEventSerializer(event)
        
        return success_response(
            "Timeline event updated",
            detail_serializer.data
        )
    
    return error_response(
        "Timeline event update failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_checklist_items(request):
    """
    Get checklist items for a specific move, grouped by week.
    """
    move_id = request.GET.get('move_id')
    
    if not move_id:
        return error_response(
            "Move ID required",
            {'move_id': ['This parameter is required']},
            status.HTTP_400_BAD_REQUEST
        )
    
    # Verify move belongs to user
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    # Only create default checklist items if none exist AND no AI-generated items exist
    # (AI generation happens in background, so we check for any items, not just custom ones)
    if not ChecklistItem.objects.filter(move=move).exists():
        create_default_checklist_items(move)
    
    # Get checklist items for this move
    items = ChecklistItem.objects.filter(move=move)
    
    # Group items by week
    weeks_data = defaultdict(list)
    for item in items:
        weeks_data[item.week].append(item)
    
    # Create week summaries
    week_titles = {
        8: ("8 Weeks Before", "Research & Planning"),
        7: ("7 Weeks Before", "Early Preparation"),
        6: ("6 Weeks Before", "Booking & Preparation"),
        5: ("5 Weeks Before", "Planning & Organization"),
        4: ("4 Weeks Before", "Organization & Supplies"),
        3: ("3 Weeks Before", "Packing & Preparation"),
        2: ("2 Weeks Before", "Final Preparations"),
        1: ("1 Week Before", "Last Minute Tasks"),
        0: ("Moving Day", "Day of Move"),
    }
    
    result = []
    for week in sorted(weeks_data.keys(), reverse=True):
        tasks = weeks_data[week]
        completed_count = sum(1 for task in tasks if task.completed)
        total_count = len(tasks)
        progress = int((completed_count / total_count) * 100) if total_count > 0 else 0
        
        title, subtitle = week_titles.get(week, (f"{week} Weeks Before", "Custom Tasks"))
        
        week_data = {
            'week': week,
            'title': title,
            'subtitle': subtitle,
            'progress': progress,
            'tasks': ChecklistItemSerializer(tasks, many=True).data
        }
        result.append(week_data)
    
    return success_response(
        "Checklist items retrieved",
        result
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_checklist_item(request, item_id):
    """
    Update a checklist item (mainly completion status).
    """
    item = get_object_or_404(ChecklistItem, id=item_id, move__user=request.user)
    
    serializer = ChecklistItemUpdateSerializer(item, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        
        # Return updated item data
        detail_serializer = ChecklistItemSerializer(item)
        
        return success_response(
            "Checklist item updated",
            detail_serializer.data
        )
    
    return error_response(
        "Checklist item update failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_custom_task(request):
    """
    Add a custom checklist item.
    """
    serializer = ChecklistItemCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        item = serializer.save()
        
        # Return created item data
        detail_serializer = ChecklistItemSerializer(item)
        
        return success_response(
            "Custom task added successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Custom task creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_custom_task(request, item_id):
    """
    Delete a custom checklist item.
    """
    item = get_object_or_404(ChecklistItem, id=item_id, move__user=request.user)
    
    # Only allow deletion of custom tasks
    if not item.is_custom:
        return error_response(
            "Cannot delete default task",
            {'detail': ['Only custom tasks can be deleted']},
            status.HTTP_400_BAD_REQUEST
        )
    
    item.delete()
    
    return success_response("Custom task deleted successfully")


def create_default_checklist_items(move):
    """
    Create default checklist items for a new move based on templates.
    """
    templates = ChecklistTemplate.objects.filter(is_active=True)
    
    for template in templates:
        ChecklistItem.objects.create(
            move=move,
            title=template.title,
            week=template.week,
            priority=template.priority,
            is_custom=False
        )

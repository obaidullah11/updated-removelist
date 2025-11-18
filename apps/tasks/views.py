"""
Views for task management.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Task, TaskTimer, TaskTemplate
from .serializers import (
    TaskCreateSerializer, TaskDetailSerializer, TaskListSerializer, TaskUpdateSerializer,
    TaskTimerCreateSerializer, TaskTimerDetailSerializer, TaskTimerUpdateSerializer,
    TaskTemplateSerializer
)
from apps.moves.models import Move
from apps.common.utils import success_response, error_response, paginated_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tasks(request):
    """
    Get tasks for a specific move.
    """
    move_id = request.GET.get('move_id')
    location = request.GET.get('location')  # Filter by location
    category = request.GET.get('category')  # Filter by category
    completed = request.GET.get('completed')  # Filter by completion status
    
    if not move_id:
        return error_response(
            "Move ID required",
            {'move_id': ['This parameter is required']},
            status.HTTP_400_BAD_REQUEST
        )
    
    # Verify move belongs to user
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    # Get tasks for this move
    tasks = Task.objects.filter(move=move).select_related('assigned_to', 'collaborator')
    
    # Apply filters
    if location:
        tasks = tasks.filter(location=location)
    
    if category:
        tasks = tasks.filter(category=category)
    
    if completed is not None:
        is_completed = completed.lower() in ['true', '1', 'yes']
        tasks = tasks.filter(completed=is_completed)
    
    # Check if pagination is requested
    if request.GET.get('page'):
        return paginated_response(
            tasks,
            TaskListSerializer,
            request,
            "Tasks retrieved successfully"
        )
    
    # Return all tasks without pagination
    serializer = TaskDetailSerializer(tasks, many=True)
    
    return success_response(
        "Tasks retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_task(request):
    """
    Create a new task.
    """
    serializer = TaskCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        task = serializer.save()
        
        # Return detailed task data
        detail_serializer = TaskDetailSerializer(task)
        
        return success_response(
            "Task created successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Task creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task(request, task_id):
    """
    Get task details by ID.
    """
    task = get_object_or_404(Task, id=task_id, move__user=request.user)
    
    serializer = TaskDetailSerializer(task)
    
    return success_response(
        "Task details retrieved",
        serializer.data
    )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_task(request, task_id):
    """
    Update a task.
    """
    task = get_object_or_404(Task, id=task_id, move__user=request.user)
    
    serializer = TaskUpdateSerializer(task, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        
        # Return updated task data
        detail_serializer = TaskDetailSerializer(task)
        
        return success_response(
            "Task updated successfully",
            detail_serializer.data
        )
    
    return error_response(
        "Task update failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_task(request, task_id):
    """
    Delete a task.
    """
    task = get_object_or_404(Task, id=task_id, move__user=request.user)
    
    task.delete()
    
    return success_response("Task deleted successfully")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_task_from_template(request):
    """
    Create a task from a template.
    """
    template_id = request.data.get('template_id')
    move_id = request.data.get('move_id')
    assigned_to_id = request.data.get('assigned_to')
    collaborator_id = request.data.get('collaborator_id')
    
    if not template_id or not move_id:
        return error_response(
            "Template ID and Move ID required",
            {'template_id': ['This field is required'], 'move_id': ['This field is required']},
            status.HTTP_400_BAD_REQUEST
        )
    
    # Verify move belongs to user
    move = get_object_or_404(Move, id=move_id, user=request.user)
    
    # Get template
    template = get_object_or_404(TaskTemplate, id=template_id, is_active=True)
    
    # Get assigned user and collaborator if provided
    assigned_to = None
    collaborator = None
    
    if assigned_to_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        assigned_to = get_object_or_404(User, id=assigned_to_id)
    
    if collaborator_id:
        from apps.moves.models import MoveCollaborator
        collaborator = get_object_or_404(MoveCollaborator, id=collaborator_id, move=move)
    
    # Create task from template
    task = template.create_task_for_move(move, assigned_to, collaborator)
    
    # Return created task data
    detail_serializer = TaskDetailSerializer(task)
    
    return success_response(
        "Task created from template successfully",
        detail_serializer.data,
        status.HTTP_201_CREATED
    )


# ============= TASK TIMER VIEWS =============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_timers(request):
    """
    Get task timers for a specific task or user.
    """
    task_id = request.GET.get('task_id')
    
    if task_id:
        # Get timers for a specific task
        task = get_object_or_404(Task, id=task_id, move__user=request.user)
        timers = TaskTimer.objects.filter(task=task).select_related('user', 'task')
    else:
        # Get all timers for the user
        timers = TaskTimer.objects.filter(user=request.user).select_related('user', 'task')
    
    # Check if pagination is requested
    if request.GET.get('page'):
        return paginated_response(
            timers,
            TaskTimerDetailSerializer,
            request,
            "Task timers retrieved successfully"
        )
    
    # Return all timers without pagination
    serializer = TaskTimerDetailSerializer(timers, many=True)
    
    return success_response(
        "Task timers retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_task_timer(request):
    """
    Start a timer for a task.
    """
    # Check if user has any active timers
    active_timer = TaskTimer.objects.filter(
        user=request.user, 
        end_time__isnull=True
    ).first()
    
    if active_timer:
        return error_response(
            "Timer already active",
            {'detail': ['You already have an active timer. Stop it before starting a new one.']},
            status.HTTP_400_BAD_REQUEST
        )
    
    # Set start time to now if not provided
    data = request.data.copy()
    if 'start_time' not in data:
        data['start_time'] = timezone.now()
    
    serializer = TaskTimerCreateSerializer(data=data, context={'request': request})
    
    if serializer.is_valid():
        timer = serializer.save()
        
        # Return timer data
        detail_serializer = TaskTimerDetailSerializer(timer)
        
        return success_response(
            "Task timer started successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Failed to start task timer",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def stop_task_timer(request, timer_id):
    """
    Stop a task timer.
    """
    timer = get_object_or_404(TaskTimer, id=timer_id, user=request.user)
    
    if timer.end_time:
        return error_response(
            "Timer already stopped",
            {'detail': ['This timer has already been stopped.']},
            status.HTTP_400_BAD_REQUEST
        )
    
    # Set end time to now if not provided
    data = request.data.copy()
    if 'end_time' not in data:
        data['end_time'] = timezone.now()
    
    serializer = TaskTimerUpdateSerializer(timer, data=data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        
        # Return updated timer data
        detail_serializer = TaskTimerDetailSerializer(timer)
        
        return success_response(
            "Task timer stopped successfully",
            detail_serializer.data
        )
    
    return error_response(
        "Failed to stop task timer",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_active_timer(request):
    """
    Get the user's currently active timer.
    """
    active_timer = TaskTimer.objects.filter(
        user=request.user, 
        end_time__isnull=True
    ).select_related('task').first()
    
    if active_timer:
        serializer = TaskTimerDetailSerializer(active_timer)
        return success_response(
            "Active timer retrieved",
            serializer.data
        )
    
    return success_response(
        "No active timer",
        None
    )


# ============= TASK TEMPLATE VIEWS =============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_templates(request):
    """
    Get all active task templates.
    """
    category = request.GET.get('category')
    location = request.GET.get('location')
    
    templates = TaskTemplate.objects.filter(is_active=True)
    
    # Apply filters
    if category:
        templates = templates.filter(category=category)
    
    if location:
        templates = templates.filter(location=location)
    
    # Check if pagination is requested
    if request.GET.get('page'):
        return paginated_response(
            templates,
            TaskTemplateSerializer,
            request,
            "Task templates retrieved successfully"
        )
    
    # Return all templates without pagination
    serializer = TaskTemplateSerializer(templates, many=True)
    
    return success_response(
        "Task templates retrieved successfully",
        serializer.data
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_template(request, template_id):
    """
    Get task template details by ID.
    """
    template = get_object_or_404(TaskTemplate, id=template_id, is_active=True)
    
    serializer = TaskTemplateSerializer(template)
    
    return success_response(
        "Task template details retrieved",
        serializer.data
    )


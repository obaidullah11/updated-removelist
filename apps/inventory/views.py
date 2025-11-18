"""
Views for inventory management.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from apps.common.utils import success_response, error_response
from apps.moves.models import Move
from .models import InventoryRoom, InventoryItem, InventoryBox, HeavyItem, HighValueItem, StorageItem
from .serializers import (
    InventoryRoomCreateSerializer, InventoryRoomUpdateSerializer,
    InventoryRoomDetailSerializer, InventoryRoomListSerializer,
    InventoryItemCreateSerializer, InventoryItemUpdateSerializer,
    InventoryItemDetailSerializer, InventoryItemListSerializer,
    InventoryBoxCreateSerializer, InventoryBoxDetailSerializer, InventoryBoxListSerializer,
    HeavyItemCreateSerializer, HeavyItemDetailSerializer, HeavyItemListSerializer,
    HighValueItemCreateSerializer, HighValueItemDetailSerializer, HighValueItemListSerializer,
    StorageItemCreateSerializer, StorageItemDetailSerializer, StorageItemListSerializer
)
from .services.floor_plan_analyzer import FloorPlanAnalyzer
from .services.ai_floor_plan_analyzer import AIFloorPlanAnalyzer
from PIL import Image
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])  # No authentication required
def analyze_floor_plan_service(request):
    """
    Standalone service to analyze floor plan images and extract room/inventory data.
    No authentication required - useful for testing and demonstrations.
    
    Expected request:
    - Method: POST
    - Content-Type: multipart/form-data
    - Field: 'floor_plan' (image file)
    
    Returns:
    - Extracted room data
    - Generated inventory items
    - Analysis summary
    """
    try:
        # Check if image file is provided
        if 'floor_plan' not in request.FILES:
            return error_response(
                "Floor plan image required",
                {"floor_plan": ["Please upload a floor plan image"]},
                status.HTTP_400_BAD_REQUEST
            )
        
        floor_plan_file = request.FILES['floor_plan']
        
        # Validate file type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        file_extension = os.path.splitext(floor_plan_file.name)[1].lower()
        
        if file_extension not in allowed_extensions:
            return error_response(
                "Invalid file type",
                {"floor_plan": [f"Please upload an image file. Allowed types: {', '.join(allowed_extensions)}"]},
                status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if floor_plan_file.size > max_size:
            return error_response(
                "File too large",
                {"floor_plan": ["File size must be less than 10MB"]},
                status.HTTP_400_BAD_REQUEST
            )
        
        # Save the uploaded file temporarily
        temp_file_path = None
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                for chunk in floor_plan_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            logger.info(f"Analyzing floor plan: {floor_plan_file.name} ({floor_plan_file.size} bytes)")
            
            # Initialize the floor plan analyzer
            analyzer = FloorPlanAnalyzer()
            
            # Analyze the floor plan (using a dummy move ID for the service)
            analysis_result = analyzer.analyze_floor_plan_service(temp_file_path)
            
            if analysis_result['success']:
                # Format the response data
                response_data = {
                    'analysis_successful': True,
                    'file_info': {
                        'filename': floor_plan_file.name,
                        'size_bytes': floor_plan_file.size,
                        'file_type': file_extension
                    },
                    'rooms_detected': analysis_result['rooms_created'],
                    'inventory_summary': analysis_result['summary'],
                    'detailed_rooms': []
                }
                
                # Add detailed room information
                for room_info in analysis_result['inventory_data']:
                    room_detail = {
                        'room_name': room_info['room_name'],
                        'room_type': room_info['room_type'],
                        'area_pixels': room_info.get('area', 0),
                        'regular_items': room_info['items_summary']['regular_items'],
                        'boxes': room_info['items_summary']['boxes'],
                        'heavy_items': room_info['items_summary']['heavy_items'],
                        'item_counts': {
                            'regular_items': room_info['items_summary']['regular_items_count'],
                            'boxes': room_info['items_summary']['boxes_created'],
                            'heavy_items': room_info['items_summary']['heavy_items_created']
                        }
                    }
                    response_data['detailed_rooms'].append(room_detail)
                
                return success_response(
                    "Floor plan analyzed successfully",
                    response_data,
                    status.HTTP_200_OK
                )
            else:
                return error_response(
                    "Floor plan analysis failed",
                    {"analysis": [analysis_result.get('error', 'Unknown error occurred')]},
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_file_path}: {e}")
                    
    except Exception as e:
        logger.error(f"Floor plan analysis service error: {str(e)}")
        return error_response(
            "Service error",
            {"error": [str(e)]},
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_floor_plan_with_ai(request):
    """
    Analyze a floor plan image using AI (Google Gemini Vision) to generate inventory and tasks.
    
    Expected request:
    - Method: POST
    - Content-Type: multipart/form-data
    - Fields:
      - 'floor_plan' (image file, required)
      - 'move_id' (UUID, required)
      - 'is_new_property' (boolean, optional, default: false)
    
    Returns:
    - Created inventory items (rooms, boxes, heavy items)
    - Generated tasks
    - Analysis summary
    """
    try:
        # Check if image file is provided
        if 'floor_plan' not in request.FILES:
            return error_response(
                "Floor plan image required",
                {"floor_plan": ["Please upload a floor plan image"]},
                status.HTTP_400_BAD_REQUEST
            )
        
        # Check if move_id is provided
        move_id = request.data.get('move_id')
        if not move_id:
            return error_response(
                "Move ID required",
                {"move_id": ["move_id is required"]},
                status.HTTP_400_BAD_REQUEST
            )
        
        # Get the move
        move = get_object_or_404(Move, id=move_id, user=request.user)
        
        floor_plan_file = request.FILES['floor_plan']
        is_new_property = request.data.get('is_new_property', 'false').lower() == 'true'
        
        # Validate file type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        file_extension = os.path.splitext(floor_plan_file.name)[1].lower()
        
        if file_extension not in allowed_extensions:
            return error_response(
                "Invalid file type",
                {"floor_plan": [f"Please upload an image file. Allowed types: {', '.join(allowed_extensions)}"]},
                status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 20MB for AI processing)
        max_size = 20 * 1024 * 1024  # 20MB
        if floor_plan_file.size > max_size:
            return error_response(
                "File too large",
                {"floor_plan": ["File size must be less than 20MB"]},
                status.HTTP_400_BAD_REQUEST
            )
        
        # Process the image
        try:
            # Open image with PIL
            floor_plan_file.seek(0)  # Reset file pointer
            image = Image.open(floor_plan_file)
            
            # Convert to RGB if necessary (for compatibility)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            logger.info(f"Analyzing floor plan with AI for move {move_id}: {floor_plan_file.name} "
                       f"(size: {floor_plan_file.size} bytes, format: {image.format})")
            
            # Initialize AI analyzer
            analyzer = AIFloorPlanAnalyzer()
            
            if not analyzer.model:
                logger.error("AI model not initialized - check GOOGLE_AI_API_KEY")
                return error_response(
                    "AI service not available",
                    {"error": ["Google AI service is not configured or unavailable"]},
                    status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Analyze and generate inventory
            logger.info("Starting AI analysis...")
            result = analyzer.analyze_floor_plan_and_generate_inventory(
                move=move,
                floor_plan_image=image,
                is_new_property=is_new_property
            )
            logger.info(f"AI analysis completed. Success: {result.get('success')}")
            
            if result.get('success'):
                # Format response
                response_data = {
                    'move_id': result['move_id'],
                    'is_new_property': result['is_new_property'],
                    'inventory_summary': {
                        'rooms_created': result['inventory']['rooms_created'],
                        'items_created': result['inventory'].get('items_created', 0),
                        'boxes_created': result['inventory']['boxes_created'],
                        'heavy_items_created': result['inventory']['heavy_items_created'],
                        'errors': result['inventory'].get('errors', [])
                    },
                    'tasks_summary': {
                        'tasks_created': result['tasks']['tasks_created'],
                        'errors': result['tasks'].get('errors', [])
                    },
                    'analysis_available': True,
                    'raw_analysis_preview': result.get('raw_analysis', '')[:500] if result.get('raw_analysis') else None
                }
                
                # Log summary
                logger.info(f"Analysis complete: {response_data['inventory_summary']['rooms_created']} rooms, "
                           f"{response_data['inventory_summary']['items_created']} items, "
                           f"{response_data['inventory_summary']['boxes_created']} boxes, "
                           f"{response_data['inventory_summary']['heavy_items_created']} heavy items, "
                           f"{response_data['tasks_summary']['tasks_created']} tasks created")
                
                return success_response(
                    "Floor plan analyzed successfully. Inventory and tasks have been generated.",
                    response_data,
                    status.HTTP_200_OK
                )
            else:
                return error_response(
                    "AI analysis failed",
                    {"error": [result.get('error', 'Unknown error occurred')]},
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as img_error:
            logger.error(f"Error processing floor plan image: {img_error}", exc_info=True)
            return error_response(
                "Image processing error",
                {"error": [f"Failed to process image: {str(img_error)}"]},
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"AI floor plan analysis error: {str(e)}", exc_info=True)
        return error_response(
            "Service error",
            {"error": [str(e)]},
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def floor_plan_service_info(request):
    """
    Get information about the floor plan analysis service.
    """
    info = {
        'service_name': 'Floor Plan Analysis Service',
        'version': '2.0',
        'description': 'Analyzes architectural floor plan images to extract room information and generate inventory checklists',
        'capabilities': [
            'Room detection and classification',
            'Inventory item generation by room type',
            'Packing box estimation',
            'Heavy item identification',
            'OCR text recognition (when available)',
            'Architectural pattern recognition'
        ],
        'supported_formats': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
        'max_file_size': '10MB',
        'usage': {
            'endpoint': '/api/inventory/analyze-floor-plan/',
            'method': 'POST',
            'content_type': 'multipart/form-data',
            'required_field': 'floor_plan',
            'authentication': 'None required'
        },
        'example_response': {
            'analysis_successful': True,
            'rooms_detected': 7,
            'inventory_summary': {
                'total_rooms': 7,
                'total_regular_items': 31,
                'total_boxes': 15,
                'total_heavy_items': 10,
                'rooms_by_type': {
                    'living_room': 2,
                    'bedroom': 4,
                    'bathroom': 1
                }
            }
        }
    }
    
    return success_response(
        "Floor plan analysis service information",
        info,
        status.HTTP_200_OK
    )


# ==================== INVENTORY ROOMS ====================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_rooms(request):
    """Get all rooms for a move (GET) or create a new room (POST)."""
    if request.method == 'POST':
        # Handle room creation with AI item generation
        serializer = InventoryRoomCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            room = serializer.save()
            
            # Automatically generate items for the room using AI (with fallback to predefined items)
            items_created = 0
            try:
                from apps.inventory.services.ai_floor_plan_analyzer import AIFloorPlanAnalyzer
                ai_analyzer = AIFloorPlanAnalyzer()
                
                logger.info(f"Generating items for room '{room.name}' with type '{room.type}' using AI")
                generated_items = ai_analyzer.generate_items_for_room(room.move, room.name, room.type)
                
                logger.info(f"Generated {len(generated_items)} items for room '{room.name}': {generated_items}")
                
                # Create InventoryItem instances for the generated items
                if not generated_items:
                    logger.warning(f"No items generated for room '{room.name}' (type: {room.type})")
                else:
                    for item_name in generated_items:
                        if item_name and isinstance(item_name, str) and item_name.strip():
                            try:
                                InventoryItem.objects.create(
                                    move=room.move,
                                    room=room,
                                    name=item_name.strip()
                                )
                                items_created += 1
                                logger.info(f"Auto-created inventory item '{item_name.strip()}' for room '{room.name}'")
                            except Exception as item_error:
                                logger.error(f"Failed to auto-create item '{item_name}': {item_error}", exc_info=True)
                
                if items_created > 0:
                    logger.info(f"Successfully auto-generated {items_created} items for room '{room.name}' (type: {room.type})")
                else:
                    logger.warning(f"No items were created for room '{room.name}' (type: {room.type}). Generated items: {generated_items}")
            except Exception as e:
                logger.error(f"Failed to auto-generate items for room '{room.name}': {e}", exc_info=True)
                # Continue even if item generation fails - room creation is successful
            
            # Refresh room to get updated relationships
            room.refresh_from_db()
            room = InventoryRoom.objects.prefetch_related('room_items').get(id=room.id)
            detail_serializer = InventoryRoomDetailSerializer(room, context={'request': request})
            return success_response(
                "Room created successfully",
                detail_serializer.data,
                status.HTTP_201_CREATED
            )
        
        return error_response(
            "Room creation failed",
            serializer.errors,
            status.HTTP_400_BAD_REQUEST
        )
    
    # Handle GET request
    move_id = request.GET.get('move_id')
    if not move_id:
        return error_response(
            "Move ID required",
            {"move_id": ["move_id query parameter is required"]},
            status.HTTP_400_BAD_REQUEST
        )
    
    move = get_object_or_404(Move, id=move_id, user=request.user)
    rooms = InventoryRoom.objects.filter(move=move).prefetch_related('room_items')
    serializer = InventoryRoomListSerializer(rooms, many=True, context={'request': request})
    
    return success_response(
        "Rooms retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_room(request):
    """Create a new inventory room and automatically generate items based on room type."""
    serializer = InventoryRoomCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        room = serializer.save()
        
        # Automatically generate items for the room using AI based on its type
        try:
            from apps.inventory.services.ai_floor_plan_analyzer import AIFloorPlanAnalyzer
            ai_analyzer = AIFloorPlanAnalyzer()
            
            logger.info(f"Generating items for room '{room.name}' with type '{room.type}' using AI")
            generated_items = ai_analyzer.generate_items_for_room(room.move, room.name, room.type)
            
            logger.info(f"AI generated {len(generated_items)} items for room '{room.name}': {generated_items}")
            
            # Create InventoryItem instances for the generated items
            items_created = 0
            if not generated_items:
                logger.warning(f"No items generated for room '{room.name}' (type: {room.type})")
            else:
                for item_name in generated_items:
                    if item_name and isinstance(item_name, str) and item_name.strip():
                        try:
                            InventoryItem.objects.create(
                                move=room.move,
                                room=room,
                                name=item_name.strip()
                            )
                            items_created += 1
                            logger.info(f"Auto-created inventory item '{item_name.strip()}' for room '{room.name}'")
                        except Exception as item_error:
                            logger.error(f"Failed to auto-create item '{item_name}': {item_error}", exc_info=True)
            
            if items_created > 0:
                logger.info(f"Successfully auto-generated {items_created} items for room '{room.name}' (type: {room.type}) using AI")
            else:
                logger.warning(f"No items were created for room '{room.name}' (type: {room.type}). Generated items: {generated_items}")
        except Exception as e:
            logger.error(f"Failed to auto-generate items for room '{room.name}': {e}", exc_info=True)
            # Continue even if item generation fails - room creation is successful
        
        # Refresh room to get updated relationships
        room.refresh_from_db()
        room = InventoryRoom.objects.prefetch_related('room_items').get(id=room.id)
        detail_serializer = InventoryRoomDetailSerializer(room, context={'request': request})
        return success_response(
            "Room created successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Room creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def get_room(request, room_id):
    """Get room details or update a room."""
    room = get_object_or_404(InventoryRoom, id=room_id, move__user=request.user)
    
    if request.method in ['PUT', 'PATCH']:
        # Handle update
        serializer = InventoryRoomUpdateSerializer(room, data=request.data, partial=(request.method == 'PATCH'))
        
        if serializer.is_valid():
            # Check if items are being updated (legacy JSONField)
            items_to_add = None
            if 'items' in request.data and isinstance(request.data.get('items'), list):
                current_items = room.items if isinstance(room.items, list) else []
                new_items = request.data.get('items', [])
                # Find items that are new (not in current_items)
                items_to_add = [item for item in new_items if item not in current_items]
            
            serializer.save()
            
            # If new items were added to JSONField, create InventoryItem instances
            if items_to_add:
                for item_name in items_to_add:
                    if item_name and isinstance(item_name, str) and item_name.strip():
                        try:
                            InventoryItem.objects.create(
                                move=room.move,
                                room=room,
                                name=item_name.strip()
                            )
                            logger.info(f"Created inventory item '{item_name.strip()}' for room '{room.name}' from JSONField update")
                        except Exception as e:
                            logger.warning(f"Failed to create inventory item '{item_name}': {e}")
            
            # Refresh room to get updated relationships - prefetch items
            room.refresh_from_db()
            # Re-fetch with prefetch to get updated room_items
            room = InventoryRoom.objects.prefetch_related('room_items').get(id=room_id, move__user=request.user)
            detail_serializer = InventoryRoomDetailSerializer(room, context={'request': request})
            return success_response("Room updated successfully", detail_serializer.data)
        
        return error_response("Room update failed", serializer.errors, status.HTTP_400_BAD_REQUEST)
    
    # Handle GET - prefetch items, boxes, and heavy items for better performance
    room = InventoryRoom.objects.prefetch_related('room_items', 'boxes_in_room', 'heavy_items_in_room').get(id=room_id, move__user=request.user)
    serializer = InventoryRoomDetailSerializer(room, context={'request': request})
    return success_response("Room retrieved successfully", serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_room(request, room_id):
    """Update a room."""
    room = get_object_or_404(InventoryRoom, id=room_id, move__user=request.user)
    serializer = InventoryRoomUpdateSerializer(room, data=request.data, partial=True, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        detail_serializer = InventoryRoomDetailSerializer(room, context={'request': request})
        return success_response("Room updated successfully", detail_serializer.data)
    
    return error_response("Room update failed", serializer.errors, status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH', 'PUT'])
@permission_classes([IsAuthenticated])
def mark_room_packed(request, room_id):
    """Mark a room as packed or unpacked."""
    room = get_object_or_404(InventoryRoom, id=room_id, move__user=request.user)
    
    packed = request.data.get('packed', None)
    if packed is None:
        return error_response(
            "Packed status required",
            {"packed": ["packed field is required"]},
            status.HTTP_400_BAD_REQUEST
        )
    
    room.packed = bool(packed)
    room.save()
    
    # Return updated room data
    detail_serializer = InventoryRoomDetailSerializer(room, context={'request': request})
    return success_response(
        f"Room marked as {'packed' if room.packed else 'unpacked'}",
        detail_serializer.data
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_room(request, room_id):
    """Delete a room."""
    room = get_object_or_404(InventoryRoom, id=room_id, move__user=request.user)
    room.delete()
    return success_response("Room deleted successfully")


# ==================== INVENTORY BOXES ====================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_boxes(request):
    """Get all boxes for a move or create a new box."""
    if request.method == 'POST':
        # Handle box creation
        serializer = InventoryBoxCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            box = serializer.save()
            detail_serializer = InventoryBoxDetailSerializer(box, context={'request': request})
            return success_response(
                "Box created successfully",
                detail_serializer.data,
                status.HTTP_201_CREATED
            )
        
        return error_response(
            "Box creation failed",
            serializer.errors,
            status.HTTP_400_BAD_REQUEST
        )
    
    # Handle GET request
    move_id = request.GET.get('move_id')
    if not move_id:
        return error_response(
            "Move ID required",
            {"move_id": ["move_id query parameter is required"]},
            status.HTTP_400_BAD_REQUEST
        )
    
    move = get_object_or_404(Move, id=move_id, user=request.user)
    boxes = InventoryBox.objects.filter(move=move)
    serializer = InventoryBoxListSerializer(boxes, many=True, context={'request': request})
    
    return success_response(
        "Boxes retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_box(request):
    """Create a new inventory box."""
    # Handle both JSON and FormData (for image uploads)
    if request.content_type and 'multipart/form-data' in request.content_type:
        # FormData - image can be included
        data = request.data.copy()
    else:
        # JSON data
        data = request.data
    
    serializer = InventoryBoxCreateSerializer(data=data, context={'request': request})
    
    if serializer.is_valid():
        box = serializer.save()
        detail_serializer = InventoryBoxDetailSerializer(box, context={'request': request})
        return success_response(
            "Box created successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Box creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_box(request, box_id):
    """Get box details."""
    box = get_object_or_404(InventoryBox, id=box_id, move__user=request.user)
    serializer = InventoryBoxDetailSerializer(box, context={'request': request})
    return success_response("Box retrieved successfully", serializer.data)


@api_view(['PATCH', 'PUT'])
@permission_classes([IsAuthenticated])
def mark_box_packed(request, box_id):
    """Mark a box as packed or unpacked."""
    box = get_object_or_404(InventoryBox, id=box_id, move__user=request.user)
    
    packed = request.data.get('packed', None)
    if packed is None:
        return error_response(
            "Packed status required",
            {"packed": ["packed field is required"]},
            status.HTTP_400_BAD_REQUEST
        )
    
    box.packed = bool(packed)
    box.save()
    
    # Return updated box data
    detail_serializer = InventoryBoxDetailSerializer(box, context={'request': request})
    return success_response(
        f"Box marked as {'packed' if box.packed else 'unpacked'}",
        detail_serializer.data
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_box(request, box_id):
    """Update a box."""
    box = get_object_or_404(InventoryBox, id=box_id, move__user=request.user)
    
    # Handle image upload separately if it's FormData
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Handle FormData for image upload
        data = request.data.copy()
        # The image field will be handled by the serializer
    else:
        data = request.data
    
    serializer = InventoryBoxDetailSerializer(box, data=data, partial=True, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        # Refresh to get updated data
        box.refresh_from_db()
        detail_serializer = InventoryBoxDetailSerializer(box, context={'request': request})
        return success_response("Box updated successfully", detail_serializer.data)
    
    return error_response("Box update failed", serializer.errors, status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_box(request, box_id):
    """Delete a box."""
    box = get_object_or_404(InventoryBox, id=box_id, move__user=request.user)
    box.delete()
    return success_response("Box deleted successfully")


# ==================== HEAVY ITEMS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_heavy_items(request):
    """Get all heavy items for a move."""
    move_id = request.GET.get('move_id')
    if not move_id:
        return error_response(
            "Move ID required",
            {"move_id": ["move_id query parameter is required"]},
            status.HTTP_400_BAD_REQUEST
        )
    
    move = get_object_or_404(Move, id=move_id, user=request.user)
    items = HeavyItem.objects.filter(move=move)
    serializer = HeavyItemListSerializer(items, many=True, context={'request': request})
    
    return success_response(
        "Heavy items retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_heavy_item(request):
    """Create a new heavy item."""
    # Handle both JSON and FormData (for image uploads)
    if request.content_type and 'multipart/form-data' in request.content_type:
        # FormData - image can be included
        data = request.data.copy()
    else:
        # JSON data
        data = request.data
    
    serializer = HeavyItemCreateSerializer(data=data, context={'request': request})
    
    if serializer.is_valid():
        item = serializer.save()
        detail_serializer = HeavyItemDetailSerializer(item, context={'request': request})
        return success_response(
            "Heavy item created successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Heavy item creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_heavy_item(request, item_id):
    """Get heavy item details."""
    item = get_object_or_404(HeavyItem, id=item_id, move__user=request.user)
    serializer = HeavyItemDetailSerializer(item, context={'request': request})
    return success_response("Heavy item retrieved successfully", serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_heavy_item(request, item_id):
    """Update a heavy item."""
    item = get_object_or_404(HeavyItem, id=item_id, move__user=request.user)
    
    # Handle image upload separately if it's FormData
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Handle FormData for image upload
        data = request.data.copy()
    else:
        data = request.data
    
    serializer = HeavyItemDetailSerializer(item, data=data, partial=True, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        # Refresh to get updated data
        item.refresh_from_db()
        detail_serializer = HeavyItemDetailSerializer(item, context={'request': request})
        return success_response("Heavy item updated successfully", detail_serializer.data)
    
    return error_response("Heavy item update failed", serializer.errors, status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_heavy_item(request, item_id):
    """Delete a heavy item."""
    item = get_object_or_404(HeavyItem, id=item_id, move__user=request.user)
    item.delete()
    return success_response("Heavy item deleted successfully")


# ==================== HIGH VALUE ITEMS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_high_value_items(request):
    """Get all high value items for a move."""
    move_id = request.GET.get('move_id')
    if not move_id:
        return error_response(
            "Move ID required",
            {"move_id": ["move_id query parameter is required"]},
            status.HTTP_400_BAD_REQUEST
        )
    
    move = get_object_or_404(Move, id=move_id, user=request.user)
    items = HighValueItem.objects.filter(move=move)
    serializer = HighValueItemListSerializer(items, many=True)
    
    return success_response(
        "High value items retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_high_value_item(request):
    """Create a new high value item."""
    serializer = HighValueItemCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        item = serializer.save()
        detail_serializer = HighValueItemDetailSerializer(item)
        return success_response(
            "High value item created successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "High value item creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_high_value_item(request, item_id):
    """Get high value item details."""
    item = get_object_or_404(HighValueItem, id=item_id, move__user=request.user)
    serializer = HighValueItemDetailSerializer(item)
    return success_response("High value item retrieved successfully", serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_high_value_item(request, item_id):
    """Update a high value item."""
    item = get_object_or_404(HighValueItem, id=item_id, move__user=request.user)
    serializer = HighValueItemDetailSerializer(item, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return success_response("High value item updated successfully", serializer.data)
    
    return error_response("High value item update failed", serializer.errors, status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_high_value_item(request, item_id):
    """Delete a high value item."""
    item = get_object_or_404(HighValueItem, id=item_id, move__user=request.user)
    item.delete()
    return success_response("High value item deleted successfully")


# ==================== STORAGE ITEMS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_storage_items(request):
    """Get all storage items for a move."""
    move_id = request.GET.get('move_id')
    if not move_id:
        return error_response(
            "Move ID required",
            {"move_id": ["move_id query parameter is required"]},
            status.HTTP_400_BAD_REQUEST
        )
    
    move = get_object_or_404(Move, id=move_id, user=request.user)
    items = StorageItem.objects.filter(move=move)
    serializer = StorageItemListSerializer(items, many=True)
    
    return success_response(
        "Storage items retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_storage_item(request):
    """Create a new storage item."""
    serializer = StorageItemCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        item = serializer.save()
        detail_serializer = StorageItemDetailSerializer(item)
        return success_response(
            "Storage item created successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Storage item creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_storage_item(request, item_id):
    """Get storage item details."""
    item = get_object_or_404(StorageItem, id=item_id, move__user=request.user)
    serializer = StorageItemDetailSerializer(item)
    return success_response("Storage item retrieved successfully", serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_storage_item(request, item_id):
    """Update a storage item."""
    item = get_object_or_404(StorageItem, id=item_id, move__user=request.user)
    serializer = StorageItemDetailSerializer(item, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return success_response("Storage item updated successfully", serializer.data)
    
    return error_response("Storage item update failed", serializer.errors, status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_storage_item(request, item_id):
    """Delete a storage item."""
    item = get_object_or_404(StorageItem, id=item_id, move__user=request.user)
    item.delete()
    return success_response("Storage item deleted successfully")


# ==================== INVENTORY ITEMS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_items(request):
    """Get all items for a move or room."""
    move_id = request.GET.get('move_id')
    room_id = request.GET.get('room_id')
    
    if not move_id and not room_id:
        return error_response(
            "Move ID or Room ID required",
            {"move_id": ["move_id or room_id query parameter is required"]},
            status.HTTP_400_BAD_REQUEST
        )
    
    if room_id:
        # Get items for a specific room
        room = get_object_or_404(InventoryRoom, id=room_id, move__user=request.user)
        items = InventoryItem.objects.filter(room=room)
    else:
        # Get items for a move
        move = get_object_or_404(Move, id=move_id, user=request.user)
        items = InventoryItem.objects.filter(move=move)
    
    serializer = InventoryItemListSerializer(items, many=True, context={'request': request})
    
    return success_response(
        "Items retrieved successfully",
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_item(request):
    """Create a new inventory item."""
    serializer = InventoryItemCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        item = serializer.save()
        detail_serializer = InventoryItemDetailSerializer(item, context={'request': request})
        return success_response(
            "Item created successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Item creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_item(request, item_id):
    """Get item details."""
    item = get_object_or_404(InventoryItem, id=item_id, move__user=request.user)
    serializer = InventoryItemDetailSerializer(item, context={'request': request})
    return success_response("Item retrieved successfully", serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_item(request, item_id):
    """Update an inventory item."""
    item = get_object_or_404(InventoryItem, id=item_id, move__user=request.user)
    serializer = InventoryItemUpdateSerializer(item, data=request.data, partial=True, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        detail_serializer = InventoryItemDetailSerializer(item, context={'request': request})
        return success_response("Item updated successfully", detail_serializer.data)
    
    return error_response("Item update failed", serializer.errors, status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def toggle_item_checked(request, item_id):
    """Toggle checked status of an inventory item."""
    item = get_object_or_404(InventoryItem, id=item_id, move__user=request.user)
    
    checked = request.data.get('checked', None)
    if checked is None:
        return error_response(
            "Checked status required",
            {"checked": ["checked field is required"]},
            status.HTTP_400_BAD_REQUEST
        )
    
    item.checked = bool(checked)
    item.save()
    
    # Return updated item data
    detail_serializer = InventoryItemDetailSerializer(item, context={'request': request})
    return success_response(
        f"Item marked as {'checked' if item.checked else 'unchecked'}",
        detail_serializer.data
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_item(request, item_id):
    """Delete an inventory item."""
    item = get_object_or_404(InventoryItem, id=item_id, move__user=request.user)
    item.delete()
    return success_response("Item deleted successfully")
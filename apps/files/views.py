"""
Views for file upload and storage.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import FloorPlan, Document
from .serializers import (
    FloorPlanUploadSerializer, DocumentUploadSerializer,
    FloorPlanSerializer, DocumentSerializer, UserFilesSerializer
)
from apps.moves.models import Move
from apps.common.utils import success_response, error_response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_floor_plan(request):
    """
    Upload a floor plan file.
    """
    serializer = FloorPlanUploadSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        floor_plan = serializer.save()
        
        # Return file details
        detail_serializer = FloorPlanSerializer(floor_plan, context={'request': request})
        
        return success_response(
            "Floor plan uploaded successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Floor plan upload failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_document(request):
    """
    Upload a document file.
    """
    serializer = DocumentUploadSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        document = serializer.save()
        
        # Return file details
        detail_serializer = DocumentSerializer(document, context={'request': request})
        
        return success_response(
            "Document uploaded successfully",
            detail_serializer.data,
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Document upload failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_files(request):
    """
    Get all files for a specific move or user.
    """
    move_id = request.GET.get('move_id')
    
    if move_id:
        # Get files for specific move
        move = get_object_or_404(Move, id=move_id, user=request.user)
        floor_plans = FloorPlan.objects.filter(move=move)
        documents = Document.objects.filter(move=move)
    else:
        # Get all files for user
        floor_plans = FloorPlan.objects.filter(move__user=request.user)
        documents = Document.objects.filter(move__user=request.user)
    
    # Serialize the data
    data = {
        'floor_plans': FloorPlanSerializer(floor_plans, many=True, context={'request': request}).data,
        'documents': DocumentSerializer(documents, many=True, context={'request': request}).data,
    }
    
    return success_response(
        "Files retrieved successfully",
        data
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_floor_plan(request, file_id):
    """
    Get floor plan details by ID.
    """
    floor_plan = get_object_or_404(FloorPlan, id=file_id, move__user=request.user)
    
    serializer = FloorPlanSerializer(floor_plan, context={'request': request})
    
    return success_response(
        "Floor plan retrieved successfully",
        serializer.data
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_document(request, file_id):
    """
    Get document details by ID.
    """
    document = get_object_or_404(Document, id=file_id, move__user=request.user)
    
    serializer = DocumentSerializer(document, context={'request': request})
    
    return success_response(
        "Document retrieved successfully",
        serializer.data
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_floor_plan(request, file_id):
    """
    Delete a floor plan file.
    """
    floor_plan = get_object_or_404(FloorPlan, id=file_id, move__user=request.user)
    
    floor_plan.delete()
    
    return success_response("Floor plan deleted successfully")


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_document(request, file_id):
    """
    Delete a document file.
    """
    document = get_object_or_404(Document, id=file_id, move__user=request.user)
    
    document.delete()
    
    return success_response("Document deleted successfully")


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_file(request, file_id):
    """
    Delete any file (floor plan or document) by ID.
    """
    # Try to find the file in either model
    floor_plan = FloorPlan.objects.filter(id=file_id, move__user=request.user).first()
    if floor_plan:
        floor_plan.delete()
        return success_response("File deleted successfully")
    
    document = Document.objects.filter(id=file_id, move__user=request.user).first()
    if document:
        document.delete()
        return success_response("File deleted successfully")
    
    return error_response(
        "File not found",
        {'detail': ['File not found or you do not have permission to delete it']},
        status.HTTP_404_NOT_FOUND
    )

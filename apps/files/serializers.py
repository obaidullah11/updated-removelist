"""
Serializers for file upload and storage.
"""
from rest_framework import serializers
from .models import FloorPlan, Document
from apps.moves.models import Move


class FloorPlanUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for floor plan upload.
    """
    
    class Meta:
        model = FloorPlan
        fields = ['file', 'move_id', 'location_type']
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_location_type(self, value):
        """Validate location type choice."""
        valid_choices = [choice[0] for choice in FloorPlan.LOCATION_TYPE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid location type. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_file(self, value):
        """Validate file upload."""
        # Check file size (10MB limit)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds 10MB limit")
        
        # Check file format
        allowed_extensions = ['pdf', 'png', 'jpg', 'jpeg']
        file_extension = value.name.lower().split('.')[-1]
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError("Unsupported file format. Please use PDF, PNG, JPG, or JPEG")
        
        return value
    
    def create(self, validated_data):
        """Create a floor plan."""
        move = validated_data.pop('move_id')
        return FloorPlan.objects.create(move=move, **validated_data)


class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for document upload.
    """
    
    class Meta:
        model = Document
        fields = ['file', 'document_type', 'move_id']
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_document_type(self, value):
        """Validate document type choice."""
        valid_choices = [choice[0] for choice in Document.DOCUMENT_TYPE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid document type. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_file(self, value):
        """Validate file upload."""
        # Check file size (10MB limit)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds 10MB limit")
        
        # Check file format
        allowed_extensions = ['pdf', 'png', 'jpg', 'jpeg']
        file_extension = value.name.lower().split('.')[-1]
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError("Unsupported file format. Please use PDF, PNG, JPG, or JPEG")
        
        return value
    
    def create(self, validated_data):
        """Create a document."""
        move = validated_data.pop('move_id')
        return Document.objects.create(move=move, **validated_data)


class FloorPlanSerializer(serializers.ModelSerializer):
    """
    Serializer for floor plan details.
    """
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = FloorPlan
        fields = [
            'id', 'filename', 'url', 'size', 'location_type',
            'move_id', 'uploaded_at'
        ]
        read_only_fields = ['id', 'filename', 'size', 'move_id', 'uploaded_at']
    
    def get_url(self, obj):
        """Get file URL."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for document details.
    """
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'filename', 'url', 'size', 'document_type',
            'move_id', 'uploaded_at'
        ]
        read_only_fields = ['id', 'filename', 'size', 'move_id', 'uploaded_at']
    
    def get_url(self, obj):
        """Get file URL."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class UserFilesSerializer(serializers.Serializer):
    """
    Serializer for user files grouped by type.
    """
    floor_plans = FloorPlanSerializer(many=True)
    documents = DocumentSerializer(many=True)

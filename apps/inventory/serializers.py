"""
Serializers for inventory management.
"""
from rest_framework import serializers
from .models import InventoryRoom, InventoryItem, InventoryBox, HeavyItem, HighValueItem, StorageItem
from apps.moves.models import Move


class InventoryRoomCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an inventory room.
    """
    move_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = InventoryRoom
        fields = ['name', 'type', 'move_id']
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return value
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_type(self, value):
        """Validate room type choice."""
        valid_choices = [choice[0] for choice in InventoryRoom.ROOM_TYPE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid room type. Choose from: {', '.join(valid_choices)}")
        return value
    
    def create(self, validated_data):
        """Create an inventory room."""
        move_id = validated_data.pop('move_id')
        # Get the move object using the validated move_id
        user = self.context['request'].user
        move = Move.objects.get(id=move_id, user=user)
        return InventoryRoom.objects.create(move=move, **validated_data)


class InventoryRoomUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an inventory room.
    """
    
    class Meta:
        model = InventoryRoom
        fields = ['name', 'items', 'boxes', 'heavy_items', 'packed']
    
    def validate_items(self, value):
        """Validate items list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Items must be a list")
        
        # Validate each item is a string
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each item must be a string")
            if len(item.strip()) == 0:
                raise serializers.ValidationError("Items cannot be empty strings")
        
        return value
    
    def validate_boxes(self, value):
        """Validate boxes count."""
        if value < 0:
            raise serializers.ValidationError("Boxes count cannot be negative")
        return value
    
    def validate_heavy_items(self, value):
        """Validate heavy items count."""
        if value < 0:
            raise serializers.ValidationError("Heavy items count cannot be negative")
        return value


# Inventory Item Serializers (defined early to avoid forward reference issues)
class InventoryItemListSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory item list.
    """
    room_name = serializers.CharField(source='room.name', read_only=True)
    picture = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'name', 'picture', 'room_name', 'checked', 'created_at'
        ]
        read_only_fields = ['id', 'room_name', 'created_at', 'picture']
    
    def get_picture(self, obj):
        """Get full URL for item picture."""
        if obj.picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.picture.url)
            return obj.picture.url
        return None


class InventoryRoomDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory room details.
    """
    total_items_count = serializers.ReadOnlyField()
    # Use string reference to avoid forward reference issue
    room_items = serializers.SerializerMethodField()
    boxes_count = serializers.SerializerMethodField()
    heavy_items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryRoom
        fields = [
            'id', 'name', 'type', 'items', 'room_items', 'boxes', 'heavy_items',
            'boxes_count', 'heavy_items_count', 'image', 'packed', 'total_items_count', 'move_id', 'created_at'
        ]
        read_only_fields = ['id', 'move_id', 'created_at', 'total_items_count', 'room_items', 'boxes_count', 'heavy_items_count']
    
    def get_room_items(self, obj):
        """Get serialized room items."""
        if hasattr(obj, 'room_items'):
            items = obj.room_items.all()
            request = self.context.get('request')
            return InventoryItemListSerializer(items, many=True, context={'request': request}).data
        return []
    
    def get_boxes_count(self, obj):
        """Get actual count of boxes in this room."""
        if hasattr(obj, 'boxes_in_room'):
            return obj.boxes_in_room.count()
        return 0
    
    def get_heavy_items_count(self, obj):
        """Get actual count of heavy items in this room."""
        if hasattr(obj, 'heavy_items_in_room'):
            return obj.heavy_items_in_room.count()
        return 0


class InventoryRoomListSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory room list (summary view).
    """
    total_items_count = serializers.ReadOnlyField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryRoom
        fields = [
            'id', 'name', 'type', 'boxes', 'heavy_items',
            'packed', 'total_items_count', 'items_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'total_items_count', 'items_count']
    
    def get_items_count(self, obj):
        """Get count of InventoryItem instances for this room."""
        return obj.room_items.count() if hasattr(obj, 'room_items') else 0


class RoomPackedSerializer(serializers.ModelSerializer):
    """
    Serializer for marking room as packed/unpacked.
    """
    
    class Meta:
        model = InventoryRoom
        fields = ['packed']


class RoomImageUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for room image upload.
    """
    
    class Meta:
        model = InventoryRoom
        fields = ['image']
    
    def validate_image(self, value):
        """Validate image file."""
        # Check file size (10MB limit)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds 10MB limit")
        
        # Check file format
        allowed_formats = ['jpeg', 'jpg', 'png']
        file_extension = value.name.lower().split('.')[-1]
        if file_extension not in allowed_formats:
            raise serializers.ValidationError("Unsupported file format. Please use PNG, JPG, or JPEG")
        
        return value


# Box Serializers
class InventoryBoxCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an inventory box.
    """
    move_id = serializers.UUIDField(write_only=True)
    room_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = InventoryBox
        fields = [
            'move_id', 'room_id', 'type', 'label', 'contents', 
            'weight', 'fragile', 'packed', 'destination_room', 'image'
        ]
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_room_id(self, value):
        """Validate that the room belongs to the move."""
        if value:
            try:
                room = InventoryRoom.objects.get(id=value)
                return room
            except InventoryRoom.DoesNotExist:
                raise serializers.ValidationError("Room not found")
        return None
    
    def validate_type(self, value):
        """Validate box type choice."""
        valid_choices = [choice[0] for choice in InventoryBox.BOX_TYPE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid box type. Choose from: {', '.join(valid_choices)}")
        return value
    
    def create(self, validated_data):
        """Create an inventory box."""
        move = validated_data.pop('move_id')
        room = validated_data.pop('room_id', None)
        return InventoryBox.objects.create(move=move, room=room, **validated_data)


class InventoryBoxDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory box details.
    """
    room_name = serializers.CharField(source='room.name', read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = InventoryBox
        fields = [
            'id', 'type', 'label', 'contents', 'weight', 'fragile', 'packed',
            'qr_code', 'image', 'destination_room', 'room_name', 'created_at'
        ]
        read_only_fields = ['id', 'qr_code', 'room_name', 'created_at']
    
    def to_representation(self, instance):
        """Override to return full image URL in response."""
        representation = super().to_representation(instance)
        # Convert image path to full URL
        if representation.get('image'):
            request = self.context.get('request')
            if request:
                representation['image'] = request.build_absolute_uri(instance.image.url)
            else:
                representation['image'] = instance.image.url
        return representation


class InventoryBoxListSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory box list.
    """
    room_name = serializers.CharField(source='room.name', read_only=True)
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryBox
        fields = [
            'id', 'type', 'label', 'fragile', 'packed', 'room_name', 'image', 'created_at'
        ]
        read_only_fields = ['id', 'room_name', 'created_at', 'image']
    
    def get_image(self, obj):
        """Get full URL for box image."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


# Heavy Item Serializers
class HeavyItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a heavy item.
    """
    move_id = serializers.UUIDField(write_only=True)
    room_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = HeavyItem
        fields = [
            'move_id', 'room_id', 'name', 'category', 'weight', 
            'dimensions', 'notes', 'requires_special_handling', 'image'
        ]
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_room_id(self, value):
        """Validate that the room belongs to the move."""
        if value:
            try:
                room = InventoryRoom.objects.get(id=value)
                return room
            except InventoryRoom.DoesNotExist:
                raise serializers.ValidationError("Room not found")
        return None
    
    def validate_category(self, value):
        """Validate heavy item category choice."""
        valid_choices = [choice[0] for choice in HeavyItem.CATEGORY_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid category. Choose from: {', '.join(valid_choices)}")
        return value
    
    def create(self, validated_data):
        """Create a heavy item."""
        move = validated_data.pop('move_id')
        room = validated_data.pop('room_id', None)
        return HeavyItem.objects.create(move=move, room=room, **validated_data)


class HeavyItemDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for heavy item details.
    """
    room_name = serializers.CharField(source='room.name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = HeavyItem
        fields = [
            'id', 'name', 'category', 'category_display', 'weight', 'dimensions',
            'notes', 'requires_special_handling', 'qr_code', 'image', 
            'room_name', 'created_at'
        ]
        read_only_fields = ['id', 'qr_code', 'room_name', 'category_display', 'created_at']
    
    def to_representation(self, instance):
        """Override to return full image URL in response."""
        representation = super().to_representation(instance)
        # Convert image path to full URL
        if representation.get('image'):
            request = self.context.get('request')
            if request:
                representation['image'] = request.build_absolute_uri(instance.image.url)
            else:
                representation['image'] = instance.image.url
        return representation


class HeavyItemListSerializer(serializers.ModelSerializer):
    """
    Serializer for heavy item list.
    """
    room_name = serializers.CharField(source='room.name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = HeavyItem
        fields = [
            'id', 'name', 'category_display', 'requires_special_handling', 
            'room_name', 'image', 'created_at'
        ]
        read_only_fields = ['id', 'room_name', 'category_display', 'created_at', 'image']
    
    def get_image(self, obj):
        """Get full URL for heavy item image."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


# High Value Item Serializers
class HighValueItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a high value item.
    """
    move_id = serializers.UUIDField(write_only=True)
    room_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = HighValueItem
        fields = [
            'move_id', 'room_id', 'name', 'category', 'value', 
            'description', 'insured'
        ]
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_room_id(self, value):
        """Validate that the room belongs to the move."""
        if value:
            try:
                room = InventoryRoom.objects.get(id=value)
                return room
            except InventoryRoom.DoesNotExist:
                raise serializers.ValidationError("Room not found")
        return None
    
    def validate_category(self, value):
        """Validate high value item category choice."""
        valid_choices = [choice[0] for choice in HighValueItem.CATEGORY_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid category. Choose from: {', '.join(valid_choices)}")
        return value
    
    def validate_value(self, value):
        """Validate item value."""
        if value is not None and value < 0:
            raise serializers.ValidationError("Value cannot be negative")
        return value
    
    def create(self, validated_data):
        """Create a high value item."""
        move = validated_data.pop('move_id')
        room = validated_data.pop('room_id', None)
        return HighValueItem.objects.create(move=move, room=room, **validated_data)


class HighValueItemDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for high value item details.
    """
    room_name = serializers.CharField(source='room.name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = HighValueItem
        fields = [
            'id', 'name', 'category', 'category_display', 'value', 'description',
            'insured', 'qr_code', 'photos', 'room_name', 'created_at'
        ]
        read_only_fields = ['id', 'qr_code', 'room_name', 'category_display', 'created_at']


class HighValueItemListSerializer(serializers.ModelSerializer):
    """
    Serializer for high value item list.
    """
    room_name = serializers.CharField(source='room.name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = HighValueItem
        fields = [
            'id', 'name', 'category_display', 'value', 'insured', 
            'room_name', 'created_at'
        ]
        read_only_fields = ['id', 'room_name', 'category_display', 'created_at']


# Storage Item Serializers
class StorageItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a storage item.
    """
    move_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = StorageItem
        fields = [
            'move_id', 'name', 'category', 'size', 'monthly_cost', 'location',
            'access_details', 'contents', 'start_date', 'end_date'
        ]
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_category(self, value):
        """Validate storage category choice."""
        valid_choices = [choice[0] for choice in StorageItem.CATEGORY_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid category. Choose from: {', '.join(valid_choices)}")
        return value
    
    def create(self, validated_data):
        """Create a storage item."""
        move = validated_data.pop('move_id')
        return StorageItem.objects.create(move=move, **validated_data)


class StorageItemDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for storage item details.
    """
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = StorageItem
        fields = [
            'id', 'name', 'category', 'category_display', 'size', 'monthly_cost', 
            'location', 'access_details', 'contents', 'start_date', 'end_date',
            'qr_code', 'contract_file', 'images', 'created_at'
        ]
        read_only_fields = ['id', 'qr_code', 'category_display', 'created_at']


class StorageItemListSerializer(serializers.ModelSerializer):
    """
    Serializer for storage item list.
    """
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = StorageItem
        fields = [
            'id', 'name', 'category_display', 'location', 'monthly_cost', 'created_at'
        ]
        read_only_fields = ['id', 'category_display', 'created_at']


# Inventory Item Serializers
class InventoryItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an inventory item.
    """
    move_id = serializers.UUIDField(write_only=True)
    room_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = InventoryItem
        fields = ['move_id', 'room_id', 'name', 'picture']
    
    def validate_move_id(self, value):
        """Validate that the move belongs to the user."""
        user = self.context['request'].user
        try:
            move = Move.objects.get(id=value, user=user)
            return move
        except Move.DoesNotExist:
            raise serializers.ValidationError("Move not found or doesn't belong to you")
    
    def validate_room_id(self, value):
        """Validate that the room belongs to the move."""
        # Get move_id from the data (it's validated first)
        move_id = self.initial_data.get('move_id')
        if not move_id:
            return value  # Will be caught by move_id validation
        
        try:
            room = InventoryRoom.objects.get(id=value, move_id=move_id)
            return room
        except InventoryRoom.DoesNotExist:
            raise serializers.ValidationError("Room not found or doesn't belong to the specified move")
    
    def validate_picture(self, value):
        """Validate image file."""
        if value:
            # Check file size (10MB limit)
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("File size exceeds 10MB limit")
            
            # Check file format
            allowed_formats = ['jpeg', 'jpg', 'png']
            file_extension = value.name.lower().split('.')[-1]
            if file_extension not in allowed_formats:
                raise serializers.ValidationError("Unsupported file format. Please use PNG, JPG, or JPEG")
        
        return value
    
    def create(self, validated_data):
        """Create an inventory item."""
        move = validated_data.pop('move_id')
        room = validated_data.pop('room_id')
        return InventoryItem.objects.create(move=move, room=room, **validated_data)


class InventoryItemUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an inventory item.
    """
    
    class Meta:
        model = InventoryItem
        fields = ['name', 'picture']
    
    def validate_picture(self, value):
        """Validate image file."""
        if value:
            # Check file size (10MB limit)
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("File size exceeds 10MB limit")
            
            # Check file format
            allowed_formats = ['jpeg', 'jpg', 'png']
            file_extension = value.name.lower().split('.')[-1]
            if file_extension not in allowed_formats:
                raise serializers.ValidationError("Unsupported file format. Please use PNG, JPG, or JPEG")
        
        return value


class InventoryItemDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory item details.
    """
    room_name = serializers.CharField(source='room.name', read_only=True)
    room_id = serializers.UUIDField(source='room.id', read_only=True)
    move_id = serializers.UUIDField(source='move.id', read_only=True)
    picture = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'name', 'picture', 'room_id', 'room_name', 
            'move_id', 'checked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'room_id', 'room_name', 'move_id', 'created_at', 'updated_at', 'picture']
    
    def get_picture(self, obj):
        """Get full URL for item picture."""
        if obj.picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.picture.url)
            return obj.picture.url
        return None

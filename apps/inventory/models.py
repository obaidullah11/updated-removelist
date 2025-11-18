"""
Models for inventory management.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.moves.models import Move
from apps.common.utils import ChoicesMixin
from apps.common.validators import validate_image_file

User = get_user_model()


class InventoryRoom(models.Model, ChoicesMixin):
    """
    Model representing a room in the inventory.
    """
    
    ROOM_TYPE_CHOICES = [
        ('living_room', 'Living Room'),
        ('kitchen', 'Kitchen'),
        ('bedroom', 'Bedroom'),
        ('bathroom', 'Bathroom'),
        ('office', 'Office'),
        ('garage', 'Garage'),
        ('basement', 'Basement'),
        ('attic', 'Attic'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='inventory_rooms')
    
    # Room details
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    items = models.JSONField(default=list, blank=True)  # List of item names
    boxes = models.IntegerField(default=0)
    heavy_items = models.IntegerField(default=0)
    image = models.ImageField(
        upload_to='room_images/', 
        null=True, 
        blank=True,
        validators=[validate_image_file]
    )
    packed = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_rooms'
        verbose_name = 'Inventory Room'
        verbose_name_plural = 'Inventory Rooms'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()}) - {self.move}"
    
    def save(self, *args, **kwargs):
        """Update move progress when room is saved."""
        super().save(*args, **kwargs)
        # Trigger progress calculation for the move
        if hasattr(self.move, 'calculate_progress'):
            self.move.calculate_progress()
    
    @property
    def total_items_count(self):
        """Get total count of items in the room."""
        # Count only InventoryItem instances (new way) + legacy JSONField items
        # Note: boxes and heavy_items are separate entities, not included in total_items_count
        item_count = self.room_items.count() if hasattr(self, 'room_items') else 0
        legacy_items_count = len(self.items) if isinstance(self.items, list) else 0
        
        # If we have InventoryItem instances, use those (they are the source of truth)
        # Only count legacy items if there are no InventoryItem instances
        # This prevents double counting when items exist in both places
        if item_count > 0:
            return item_count
        else:
            return legacy_items_count


class InventoryItem(models.Model):
    """
    Model representing an inventory item in a room.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='inventory_items')
    room = models.ForeignKey(InventoryRoom, on_delete=models.CASCADE, related_name='room_items')
    
    # Item details
    name = models.CharField(max_length=200)
    picture = models.ImageField(
        upload_to='item_images/',
        null=True,
        blank=True,
        validators=[validate_image_file]
    )
    checked = models.BooleanField(default=False)  # For checklist functionality
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_items'
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.name} - {self.room.name} ({self.move})"
    
    def save(self, *args, **kwargs):
        """Update move progress when item is saved."""
        super().save(*args, **kwargs)
        # Trigger progress calculation for the move
        if hasattr(self.move, 'calculate_progress'):
            self.move.calculate_progress()


class InventoryBox(models.Model, ChoicesMixin):
    """
    Model representing a moving box with QR code tracking.
    """
    
    BOX_TYPE_CHOICES = [
        ('small', 'Small Box'),
        ('medium', 'Medium Box'),
        ('large', 'Large / Tea Chest Box'),
        ('extra_large', 'Extra Large'),
        ('book_wine', 'Book/Wine Carton'),
        ('picture_mirror', 'Picture/Mirror Box'),
        ('port_a_robe', 'Port-a-Robe Carton'),
        ('tv_carton', 'TV Carton'),
        ('dish_glassware', 'Dish/Glassware Box'),
        ('audio_file', 'Audio / File Box'),
        ('mattress', 'Mattress Box'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='inventory_boxes')
    room = models.ForeignKey(InventoryRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='boxes_in_room')
    
    # Box details
    type = models.CharField(max_length=20, choices=BOX_TYPE_CHOICES)
    label = models.CharField(max_length=100)  # e.g., "Kitchen Box 1"
    contents = models.TextField(blank=True, null=True)
    weight = models.CharField(max_length=50, blank=True, null=True)  # e.g., "15kg"
    fragile = models.BooleanField(default=False)
    packed = models.BooleanField(default=False)
    qr_code = models.CharField(max_length=500, blank=True, null=True)
    
    # Images
    image = models.ImageField(
        upload_to='box_images/', 
        null=True, 
        blank=True,
        validators=[validate_image_file]
    )
    
    # Destination room (for new address)
    destination_room = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_boxes'
        verbose_name = 'Inventory Box'
        verbose_name_plural = 'Inventory Boxes'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.label} ({self.get_type_display()}) - {self.move}"
    
    def save(self, *args, **kwargs):
        """Generate QR code if not present."""
        if not self.qr_code:
            import json
            import base64
            qr_data = {
                'id': str(self.id),
                'type': 'box',
                'move_id': str(self.move.id),
                'label': self.label,
                'room': self.room.name if self.room else None,
                'timestamp': self.created_at.isoformat() if self.created_at else None
            }
            self.qr_code = base64.b64encode(json.dumps(qr_data).encode()).decode()
        super().save(*args, **kwargs)


class HeavyItem(models.Model, ChoicesMixin):
    """
    Model representing heavy items requiring special handling.
    """
    
    CATEGORY_CHOICES = [
        ('piano', 'Pianos'),
        ('pool_table', 'Pool tables'),
        ('sculpture', 'Large sculptures/statues'),
        ('aquarium', 'Aquariums'),
        ('gym_equipment', 'Home gym equipment'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='heavy_items')
    room = models.ForeignKey(InventoryRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='heavy_items_in_room')
    
    # Item details
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    weight = models.CharField(max_length=50, blank=True, null=True)  # e.g., "300kg"
    dimensions = models.CharField(max_length=100, blank=True, null=True)  # e.g., "150x60x110cm"
    notes = models.TextField(blank=True, null=True)
    requires_special_handling = models.BooleanField(default=True)
    qr_code = models.CharField(max_length=500, blank=True, null=True)
    
    # Images
    image = models.ImageField(
        upload_to='heavy_item_images/', 
        null=True, 
        blank=True,
        validators=[validate_image_file]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'heavy_items'
        verbose_name = 'Heavy Item'
        verbose_name_plural = 'Heavy Items'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()}) - {self.move}"
    
    def save(self, *args, **kwargs):
        """Generate QR code if not present."""
        if not self.qr_code:
            import json
            import base64
            qr_data = {
                'id': str(self.id),
                'type': 'heavy_item',
                'move_id': str(self.move.id),
                'name': self.name,
                'room': self.room.name if self.room else None,
                'timestamp': self.created_at.isoformat() if self.created_at else None
            }
            self.qr_code = base64.b64encode(json.dumps(qr_data).encode()).decode()
        super().save(*args, **kwargs)


class HighValueItem(models.Model, ChoicesMixin):
    """
    Model representing high value items requiring special care and insurance.
    Note: Jewellery and documents are not permitted.
    """
    
    CATEGORY_CHOICES = [
        ('fine_art', 'Fine art/paintings'),
        ('antiques', 'Antiques'),
        ('designer_furniture', 'Designer furniture'),
        ('collectibles', 'Collectibles (e.g., rare books, coins)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='high_value_items')
    room = models.ForeignKey(InventoryRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='high_value_items_in_room')
    
    # Item details
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    insured = models.BooleanField(default=False)
    qr_code = models.CharField(max_length=500, blank=True, null=True)
    
    # Images (multiple photos allowed)
    photos = models.JSONField(default=list, blank=True)  # List of image URLs/paths
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'high_value_items'
        verbose_name = 'High Value Item'
        verbose_name_plural = 'High Value Items'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()}) - {self.move}"
    
    def save(self, *args, **kwargs):
        """Generate QR code if not present."""
        if not self.qr_code:
            import json
            import base64
            qr_data = {
                'id': str(self.id),
                'type': 'high_value_item',
                'move_id': str(self.move.id),
                'name': self.name,
                'room': self.room.name if self.room else None,
                'timestamp': self.created_at.isoformat() if self.created_at else None
            }
            self.qr_code = base64.b64encode(json.dumps(qr_data).encode()).decode()
        super().save(*args, **kwargs)


class StorageItem(models.Model):
    """
    Model representing items going into storage with user-friendly details.
    """
    
    CATEGORY_CHOICES = [
        ('self_storage', 'Self Storage'),
        ('warehouse', 'Warehouse'),
        ('climate_controlled', 'Climate Controlled'),
        ('document_storage', 'Document Storage'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='storage_items')
    
    # User-friendly storage details
    name = models.CharField(max_length=200, default='Storage Item')  # What's being stored
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='self_storage')
    size = models.CharField(max_length=100, blank=True, null=True)  # Unit size
    monthly_cost = models.CharField(max_length=100, blank=True, null=True)  # Cost info
    location = models.CharField(max_length=300, blank=True, null=True)  # Storage facility address
    access_details = models.TextField(blank=True, null=True)  # Access hours, codes, etc.
    contents = models.TextField(blank=True, null=True)  # What items are stored
    start_date = models.DateField(blank=True, null=True)  # Storage start date
    end_date = models.DateField(blank=True, null=True)  # Storage end date
    
    # Legacy vendor fields (kept for backward compatibility)
    vendor_name = models.CharField(max_length=200, blank=True, null=True)
    vendor_contact = models.CharField(max_length=100, blank=True, null=True)
    contract_details = models.TextField(blank=True, null=True)
    storage_unit_number = models.CharField(max_length=50, blank=True, null=True)
    items = models.JSONField(default=list, blank=True)  # List of item descriptions
    
    qr_code = models.CharField(max_length=500, blank=True, null=True)
    
    # Contract upload
    contract_file = models.FileField(
        upload_to='storage_contracts/', 
        null=True, 
        blank=True
    )
    
    # Images
    images = models.JSONField(default=list, blank=True)  # List of image URLs/paths
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'storage_items'
        verbose_name = 'Storage Item'
        verbose_name_plural = 'Storage Items'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.name} - {self.move}"
    
    def save(self, *args, **kwargs):
        """Generate QR code if not present."""
        if not self.qr_code:
            import json
            import base64
            qr_data = {
                'id': str(self.id),
                'type': 'storage',
                'move_id': str(self.move.id),
                'name': self.name,
                'location': self.location,
                'timestamp': self.created_at.isoformat() if self.created_at else None
            }
            self.qr_code = base64.b64encode(json.dumps(qr_data).encode()).decode()
        super().save(*args, **kwargs)
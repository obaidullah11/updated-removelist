from rest_framework import serializers
from .models import PartnerDocument

class PartnerDocumentSerializer(serializers.ModelSerializer):
    # Explicitly define file fields as not required for partial updates
    document_1 = serializers.FileField(required=False, allow_null=True)
    document_2 = serializers.FileField(required=False, allow_null=True)
    document_3 = serializers.FileField(required=False, allow_null=True)
    document_4 = serializers.FileField(required=False, allow_null=True)
    
    class Meta:
        model = PartnerDocument
        fields = '__all__'
        read_only_fields = [
            'is_submitted', 
            'is_verified', 
            'is_rejected', 
            'submitted_at', 
            'verified_at', 
            'rejected_at', 
            'rejection_reason', 
            'partner'
        ]

    def create(self, instance, validated_data):
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Handle file updates properly
        for field_name, file_data in validated_data.items():
            if field_name.startswith('document_') and file_data:
                setattr(instance, field_name, file_data)
            elif not field_name.startswith('document_'):
                setattr(instance, field_name, file_data)
        
        instance.save()
        return instance
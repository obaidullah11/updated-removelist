from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from .models import PartnerDocument
from .serializers import PartnerDocumentSerializer
from django.utils import timezone

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_partner_documents(request):
    print("Request.FILES:", request.FILES)
    print("Request.data:", request.data)
    print("Content-Type:", request.content_type)
    
    doc = PartnerDocument.objects.filter(partner=request.user).first()
    
    if doc and doc.is_verified:
        print("Documents already verified.")
        return Response({'detail': 'Documents already verified.'}, status=status.HTTP_400_BAD_REQUEST)
    
    if doc and doc.is_submitted and not doc.is_rejected:
        print("Documents already submitted and pending review.")
        return Response({'detail': 'Documents already submitted and pending review.'}, status=status.HTTP_400_BAD_REQUEST)
    
    if doc:
        # Update existing document
        print("Updating existing document:", doc)
        serializer = PartnerDocumentSerializer(doc, data=request.data, files=request.FILES, partial=True)
        if serializer.is_valid():
            serializer.save(
                is_submitted=True,
                is_rejected=False,
                rejection_reason='',
                submitted_at=timezone.now()
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        # Create new document
        serializer = PartnerDocumentSerializer(data=request.data, files=request.FILES)
        if serializer.is_valid():
            serializer.save(
                partner=request.user,
                is_submitted=True
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    print("Serializer errors:", serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_partner_documents(request, pk):
    """
    Admin approves partner documents.
    """
    try:
        doc = PartnerDocument.objects.get(pk=pk)
    except PartnerDocument.DoesNotExist:
        return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
    doc.approve()
    doc.partner.is_document_verified = True
    doc.partner.save()
    return Response({'detail': 'Documents approved.'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_partner_documents(request, pk):
    """
    Admin rejects partner documents.
    """
    try:
        doc = PartnerDocument.objects.get(pk=pk)
    except PartnerDocument.DoesNotExist:
        return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
    reason = request.data.get('rejection_reason', '')
    doc.reject(reason)
    doc.partner.is_document_verified = False
    doc.partner.save()
    return Response({'detail': 'Documents rejected.', 'reason': reason}, status=status.HTTP_200_OK)
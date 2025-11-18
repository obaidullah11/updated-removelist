"""
Authentication views for the RemoveList application.
"""
import secrets
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models
from .models import EmailVerificationToken, PasswordResetToken
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    ChangePasswordSerializer, EmailVerificationSerializer, ResendEmailSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, AvatarUploadSerializer,
    UserListSerializer, UserDetailSerializer, UserCreateSerializer,
    UserUpdateSerializer, UserPasswordResetSerializer, UserSearchSerializer
)
# Import functions directly instead of Celery tasks
from .tasks import send_verification_email, send_password_reset_email
from apps.common.utils import success_response, error_response

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def register_email(request):
    """
    Register a new user with email.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        
        # Create verification token
        token = secrets.token_urlsafe(32)
        EmailVerificationToken.objects.create(
            user=user,
            token=token
        )
        
        # Send verification email (direct call instead of Celery task)
        try:
            send_verification_email(user.id, token)
        except Exception as e:
            # Log error but don't fail registration
            print(f"Failed to send verification email: {e}")
        
        return success_response(
            "Registration successful! Please check your email for verification.",
            {
                'user_id': str(user.id),
                'email': user.email,
                'verification_required': True
            },
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "Registration failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login user and return JWT tokens.
    """
    serializer = UserLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Check if email is verified
        if not user.is_email_verified:
            return error_response(
                "Email verification required",
                {'non_field_errors': ['Please verify your email before logging in']},
                status.HTTP_400_BAD_REQUEST
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return success_response(
            "Login successful!",
            {
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_email_verified': user.is_email_verified,
                    'avatar': user.avatar.url if user.avatar else None
                }
            }
        )
    
    return error_response(
        "Invalid credentials",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    """
    Verify user email with token.
    """
    serializer = EmailVerificationSerializer(data=request.data)
    
    if serializer.is_valid():
        token = serializer.validated_data['token']
        
        try:
            verification_token = EmailVerificationToken.objects.get(token=token)
            
            if verification_token.is_used:
                return error_response(
                    "Token already used",
                    {'token': ['This verification link has already been used']},
                    status.HTTP_400_BAD_REQUEST
                )
            
            if verification_token.is_expired:
                return error_response(
                    "This verification link has expired",
                    {'token': ['Token has expired']},
                    status.HTTP_400_BAD_REQUEST
                )
            
            # Mark token as used and verify user
            verification_token.is_used = True
            verification_token.save()
            
            user = verification_token.user
            user.is_email_verified = True
            user.save()
            
            return success_response(
                "Email verified successfully",
                {'verified': True}
            )
            
        except EmailVerificationToken.DoesNotExist:
            return error_response(
                "Invalid verification token",
                {'token': ['Invalid or expired token']},
                status.HTTP_400_BAD_REQUEST
            )
    
    return error_response(
        "Invalid token",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_email(request):
    """
    Resend verification email.
    """
    serializer = ResendEmailSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            if user.is_email_verified:
                return success_response(
                    "If your email is registered, a verification link has been sent."
                )
            
            # Create new verification token
            token = secrets.token_urlsafe(32)
            EmailVerificationToken.objects.create(
                user=user,
                token=token
            )
            
            # Send verification email (direct call instead of Celery task)
            try:
                send_verification_email(user.id, token)
            except Exception as e:
                print(f"Failed to send verification email: {e}")
            
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        
        return success_response(
            "If your email is registered, a verification link has been sent."
        )
    
    return error_response(
        "Invalid email",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    Send password reset email.
    """
    serializer = ForgotPasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Create password reset token
            token = secrets.token_urlsafe(32)
            PasswordResetToken.objects.create(
                user=user,
                token=token
            )
            
            # Send password reset email (direct call instead of Celery task)
            try:
                send_password_reset_email(user.id, token)
            except Exception as e:
                print(f"Failed to send password reset email: {e}")
            
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        
        return success_response(
            "If an account exists with this email, you will receive a password reset link."
        )
    
    return error_response(
        "Invalid email",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Reset password with token.
    """
    serializer = ResetPasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            
            if reset_token.is_used:
                return error_response(
                    "Token already used",
                    {'token': ['This reset link has already been used']},
                    status.HTTP_400_BAD_REQUEST
                )
            
            if reset_token.is_expired:
                return error_response(
                    "This reset link has expired",
                    {'token': ['Token has expired']},
                    status.HTTP_400_BAD_REQUEST
                )
            
            # Reset password and mark token as used
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            
            reset_token.is_used = True
            reset_token.save()
            
            return success_response("Password reset successfully")
            
        except PasswordResetToken.DoesNotExist:
            return error_response(
                "Invalid reset token",
                {'token': ['Invalid or expired token']},
                status.HTTP_400_BAD_REQUEST
            )
    
    return error_response(
        "Invalid data",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change user password (authenticated).
    """
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        new_password = serializer.validated_data['new_password']
        
        user = request.user
        user.set_password(new_password)
        user.save()
        
        return success_response("Password updated successfully")
    
    return error_response(
        "Password change failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout user by blacklisting refresh token.
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return success_response("Logged out successfully")
    
    except Exception as e:
        return error_response(
            "Logout failed",
            {'detail': [str(e)]},
            status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Refresh JWT access token.
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return error_response(
                "Refresh token required",
                {'refresh_token': ['This field is required']},
                status.HTTP_400_BAD_REQUEST
            )
        
        token = RefreshToken(refresh_token)
        
        return success_response(
            "Token refreshed successfully",
            {
                'access_token': str(token.access_token),
                'refresh_token': str(token)
            }
        )
    
    except Exception as e:
        return error_response(
            "Token refresh failed",
            {'detail': [str(e)]},
            status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    Get user profile.
    """
    serializer = UserProfileSerializer(request.user)
    return success_response(
        "Profile retrieved successfully",
        serializer.data
    )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update user profile.
    """
    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return success_response(
            "Profile updated successfully",
            serializer.data
        )
    
    return error_response(
        "Profile update failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar(request):
    """
    Upload user avatar.
    """
    serializer = AvatarUploadSerializer(request.user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return success_response(
            "Avatar updated successfully",
            {'avatar': request.user.avatar.url if request.user.avatar else None}
        )
    
    return error_response(
        "Avatar upload failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


# User Management Views for Admin Panel
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request):
    """
    List all users with filtering and search capabilities.
    """
    # Check if user is admin
    if not request.user.is_staff:
        return error_response(
            "Permission denied",
            {'detail': ['Only admin users can access this endpoint']},
            status.HTTP_403_FORBIDDEN
        )
    
    # Get query parameters
    search = request.GET.get('search', '')
    role_type = request.GET.get('role_type')
    is_active = request.GET.get('is_active')
    is_email_verified = request.GET.get('is_email_verified')
    is_staff = request.GET.get('is_staff')
    ordering = request.GET.get('ordering', '-created_at')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    
    # Build queryset
    queryset = User.objects.all()
    
    # Apply filters
    if search:
        queryset = queryset.filter(
            models.Q(first_name__icontains=search) |
            models.Q(last_name__icontains=search) |
            models.Q(email__icontains=search) |
            models.Q(phone_number__icontains=search)
        )
    
    if role_type:
        queryset = queryset.filter(role_type=role_type)
    
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() == 'true')
    
    if is_email_verified is not None:
        queryset = queryset.filter(is_email_verified=is_email_verified.lower() == 'true')
    
    if is_staff is not None:
        queryset = queryset.filter(is_staff=is_staff.lower() == 'true')
    
    # Apply ordering
    queryset = queryset.order_by(ordering)
    
    # Pagination
    total_count = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    users = queryset[start:end]
    
    # Serialize data
    serializer = UserListSerializer(users, many=True)
    
    return success_response(
        "Users retrieved successfully",
        {
            'users': serializer.data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size
            }
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id):
    """
    Get detailed information about a specific user.
    """
    # Check if user is admin
    if not request.user.is_staff:
        return error_response(
            "Permission denied",
            {'detail': ['Only admin users can access this endpoint']},
            status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        serializer = UserDetailSerializer(user)
        return success_response(
            "User details retrieved successfully",
            serializer.data
        )
    except User.DoesNotExist:
        return error_response(
            "User not found",
            {'detail': ['User with this ID does not exist']},
            status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create(request):
    """
    Create a new user.
    """
    # Check if user is admin
    if not request.user.is_staff:
        return error_response(
            "Permission denied",
            {'detail': ['Only admin users can access this endpoint']},
            status.HTTP_403_FORBIDDEN
        )
    
    serializer = UserCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        return success_response(
            "User created successfully",
            {
                'user_id': str(user.id),
                'email': user.email,
                'full_name': user.full_name
            },
            status.HTTP_201_CREATED
        )
    
    return error_response(
        "User creation failed",
        serializer.errors,
        status.HTTP_400_BAD_REQUEST
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_update(request, user_id):
    """
    Update user information.
    """
    # Check if user is admin
    if not request.user.is_staff:
        return error_response(
            "Permission denied",
            {'detail': ['Only admin users can access this endpoint']},
            status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        partial = request.method == 'PATCH'
        serializer = UserUpdateSerializer(user, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            return success_response(
                "User updated successfully",
                serializer.data
            )
        
        return error_response(
            "User update failed",
            serializer.errors,
            status.HTTP_400_BAD_REQUEST
        )
    except User.DoesNotExist:
        return error_response(
            "User not found",
            {'detail': ['User with this ID does not exist']},
            status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete(request, user_id):
    """
    Delete a user.
    """
    # Check if user is admin
    if not request.user.is_staff:
        return error_response(
            "Permission denied",
            {'detail': ['Only admin users can access this endpoint']},
            status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prevent admin from deleting themselves
        if user.id == request.user.id:
            return error_response(
                "Cannot delete own account",
                {'detail': ['You cannot delete your own account']},
                status.HTTP_400_BAD_REQUEST
            )
        
        user.delete()
        return success_response("User deleted successfully")
    except User.DoesNotExist:
        return error_response(
            "User not found",
            {'detail': ['User with this ID does not exist']},
            status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_reset_password(request, user_id):
    """
    Reset user password (admin only).
    """
    # Check if user is admin
    if not request.user.is_staff:
        return error_response(
            "Permission denied",
            {'detail': ['Only admin users can access this endpoint']},
            status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        serializer = UserPasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            new_password = serializer.validated_data['new_password']
            user.set_password(new_password)
            user.save()
            
            return success_response("User password reset successfully")
        
        return error_response(
            "Password reset failed",
            serializer.errors,
            status.HTTP_400_BAD_REQUEST
        )
    except User.DoesNotExist:
        return error_response(
            "User not found",
            {'detail': ['User with this ID does not exist']},
            status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_toggle_status(request, user_id):
    """
    Toggle user active status.
    """
    # Check if user is admin
    if not request.user.is_staff:
        return error_response(
            "Permission denied",
            {'detail': ['Only admin users can access this endpoint']},
            status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prevent admin from deactivating themselves
        if user.id == request.user.id:
            return error_response(
                "Cannot modify own account status",
                {'detail': ['You cannot modify your own account status']},
                status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = not user.is_active
        user.save()
        
        status_text = "activated" if user.is_active else "deactivated"
        return success_response(f"User {status_text} successfully")
    except User.DoesNotExist:
        return error_response(
            "User not found",
            {'detail': ['User with this ID does not exist']},
            status.HTTP_404_NOT_FOUND
        )


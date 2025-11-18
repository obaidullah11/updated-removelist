"""
Celery tasks for authentication-related email sending.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def send_verification_email(user_id, token):
    """
    Send email verification email.
    """
    try:
        user = User.objects.get(id=user_id)

        verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        # Render HTML email
        html_message = render_to_string('emails/verification_email.html', {
            'first_name': user.first_name,
            'verification_link': verification_link,
        })

        # Send email
        send_mail(
            subject='Welcome to RemoveAList - Verify Your Email',
            message=f"Hi {user.first_name},\n\nPlease verify your email by clicking: {verification_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Verification email sent to {user.email}")

    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")


@shared_task
def send_password_reset_email(user_id, token):
    """
    Send password reset email.
    """
    try:
        user = User.objects.get(id=user_id)

        # Fix: Use path parameter instead of query parameter to match frontend routing
        reset_link = f"{settings.FRONTEND_URL}/reset-password/confirm/{token}"

        # Render HTML email
        html_message = render_to_string('emails/password_reset_email.html', {
            'first_name': user.first_name,
            'reset_link': reset_link,
            'expiry_time': '2 hours',
        })

        # Send email
        send_mail(
            subject='Reset Your Password - RemoveAList',
            message=f"Hi {user.first_name},\n\nReset your password by clicking: {reset_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Password reset email sent to {user.email}")

    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")


@shared_task
def send_booking_confirmation_email(user_id, booking_data):
    """
    Send booking request email.
    Note: Function name kept as 'confirmation' for backward compatibility.
    """
    try:
        user = User.objects.get(id=user_id)

        # Render HTML email
        html_message = render_to_string('emails/booking_confirmation_email.html', {
            'first_name': user.first_name,
            'move_date': booking_data['move_date'],
            'time_slot': booking_data['time_slot'],
            'confirmation_number': booking_data['confirmation_number'],
            'phone_number': booking_data['phone_number'],
            'contact_info': 'For questions, contact us at contactus@removealist.au or call +61406368850',
        })

        # Send email
        send_mail(
            subject='Booking Requested - RemoveAList',
            message=f"Hi {user.first_name},\n\nYour move has been requested for {booking_data['move_date']} at {booking_data['time_slot']}. Request Number: {booking_data['confirmation_number']}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Booking request email sent to {user.email}")

    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
    except Exception as e:
        logger.error(f"Failed to send booking request email: {str(e)}")


@shared_task
def send_move_reminder_email(user_id, move_data):
    """
    Send move reminder email.
    """
    try:
        user = User.objects.get(id=user_id)

        # Render HTML email
        html_message = render_to_string('emails/move_reminder_email.html', {
            'first_name': user.first_name,
            'move_date': move_data['move_date'],
            'days_remaining': move_data['days_remaining'],
            'checklist_progress': move_data['checklist_progress'],
        })

        # Send email
        send_mail(
            subject='Your Move is Coming Up - RemoveAList',
            message=f"Hi {user.first_name},\n\nYour move is in {move_data['days_remaining']} days on {move_data['move_date']}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Move reminder email sent to {user.email}")

    except User.DoesNotExist:
        logger.error(f"User with id {user_id} not found")
    except Exception as e:
        logger.error(f"Failed to send move reminder email: {str(e)}")

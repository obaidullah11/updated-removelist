"""
Utility functions for move management.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


def send_collaborator_invitation_email(collaborator):
    """
    Send invitation email to a collaborator.
    """
    try:
        # Generate invitation URL
        invitation_url = f"{settings.FRONTEND_URL}/accept-invitation?token={collaborator.invitation_token}"
        
        # Prepare email context
        context = {
            'collaborator': collaborator,
            'move': collaborator.move,
            'inviter_name': f"{collaborator.move.user.first_name} {collaborator.move.user.last_name}".strip(),
            'inviter_email': collaborator.move.user.email,
            'invitation_url': invitation_url,
            'move_date': collaborator.move.move_date.strftime('%B %d, %Y'),
            'current_location': collaborator.move.current_location,
            'destination_location': collaborator.move.destination_location,
            'role': collaborator.role,
        }
        
        # Render email template
        html_message = render_to_string('emails/collaborator_invitation.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=f"You're invited to collaborate on {context['inviter_name']}'s move",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[collaborator.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Error sending invitation email: {e}")
        return False


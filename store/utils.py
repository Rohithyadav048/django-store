from django.core.mail import EmailMessage
from django.template.loader import render_to_string

def send_order_confirmation_email(user, order):
    subject = f"Order Confirmation - #{order.id}"
    message = render_to_string("emails/order_confirmation.html", {
        'user': user,
        'order': order
    })
    email = EmailMessage(subject, message, to=[user.email])
    email.content_subtype = "html"  # To send HTML email
    email.send()

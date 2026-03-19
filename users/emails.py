from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_temporary_password_email(user, temp_password):
    if not user.email:
        return

    subject = "Your temporary password for Bookstore"

    context = {
        "user": user,
        "temp_password": temp_password,
    }

    text_body = render_to_string("emails/temporary_password.txt", context)
    html_body = render_to_string("emails/temporary_password.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
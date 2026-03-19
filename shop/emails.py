from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import Order


def send_order_confirmation_email(order_id: int) -> None:
    try:
        order = (
            Order.objects
            .select_related("user", "shipping_method")
            .prefetch_related("items__book")
            .get(id=order_id)
        )
    except Order.DoesNotExist:
        return

    if not order.user.email:
        return

    items = order.items.all()

    subtotal = sum(
        (item.subtotal or Decimal("0.00")) for item in items
    )
    subtotal = subtotal.quantize(Decimal("0.01"))

    shipping_price = (order.shipping_price or Decimal("0.00")).quantize(Decimal("0.01"))
    discount_amount = (order.discount_amount or Decimal("0.00")).quantize(Decimal("0.01"))
    total_amount = (order.total_amount or Decimal("0.00")).quantize(Decimal("0.01"))

    subject = f"Your order R{order.id:08d} confirmation"

    context = {
        "order": order,
        "user": order.user,
        "items": items,
        "subtotal": subtotal,
        "shipping_price": shipping_price,
        "discount_amount": discount_amount,
        "total_amount": total_amount,
    }

    text_body = render_to_string("emails/order_confirmation.txt", context)
    html_body = render_to_string("emails/order_confirmation.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
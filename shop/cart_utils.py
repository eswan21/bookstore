from django.db import transaction
from .models import Order, OrderItem, Book
from django.core.exceptions import ValidationError
from .views import attach_coupon_to_cart

def merge_session_cart_to_db(request, user):
    session_cart = request.session.get("cart", {})
    session_coupon = request.session.get("coupon_code")
    if not session_cart and not session_coupon:
        return

    with transaction.atomic():
        if session_cart:
            cart, _ = Order.objects.get_or_create(
                user=user,
                status=Order.Status.CART
            )

            books = Book.objects.filter(id__in=session_cart.keys())
            books_map = {str(b.id): b for b in books}

            for bid, payload in session_cart.items():
                book = books_map.get(str(bid))
                if not book:
                    continue

                qty = int(payload.get("quantity", 1))
                if qty < 1:
                    qty = 1

                item, created = OrderItem.objects.get_or_create(
                    order=cart,
                    book=book,
                    defaults={
                        "quantity": qty,
                        "unit_price": book.price
                    }
                )

                if not created:
                    item.quantity += qty

                item.unit_price = book.price
                item.save(update_fields=["quantity", "unit_price"])

        if session_coupon and not cart.coupon_id:
            try:
                attach_coupon_to_cart(cart, session_coupon)
            except ValidationError:
                pass

    # очистить session-корзину
    request.session["cart"] = {}
    request.session.pop("coupon_code", None)
    request.session.modified = True
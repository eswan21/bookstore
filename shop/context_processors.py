from .models import Category, Order
from django.db.models import Sum

def categories(request):
    return {
        "menu_categories": Category.objects.order_by("name")
    }

def cart_quantity(request):
    if request.user.is_authenticated:
        cart = Order.objects.filter(
            user=request.user,
            status=Order.Status.CART
        ).first()

        if not cart:
            return {"cart_quantity": 0}

        total_qty = cart.items.aggregate(
            total=Sum("quantity")
        )["total"] or 0

        return {"cart_quantity": total_qty}

    cart = request.session.get("cart", {})
    return {
        "cart_quantity": sum(item["quantity"] for item in cart.values())
    }
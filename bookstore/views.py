from django.shortcuts import render
from shop.models import Book, Order
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce

PAID_STATUSES = [Order.Status.IN_PROGRESS, Order.Status.DELIVERED]  

qs = (
    Book.objects
    .exclude(category__isnull=True)
    .annotate(
        total_sold=Coalesce(
            Sum(
                "order_items__quantity",
                filter=Q(order_items__order__status__in=PAID_STATUSES),
            ),
            0,
        )
    )
    .order_by("-total_sold", "-created_at")
)


def index(request):
    latest_books = Book.objects.order_by("-created_at")[:3]
    top4 = []
    used_categories = set()

    for book in qs:
        if book.category_id in used_categories:
            continue
        used_categories.add(book.category_id)
        top4.append(book)
        if len(top4) == 4:
            break

    if len(top4) < 4:
        for book in qs:
            if book in top4:
                continue
            top4.append(book)
            if len(top4) == 4:
                break

    return render(request, 'home.html',{"latest_books": latest_books, "top_sellers": top4,})





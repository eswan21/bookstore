import json
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from decimal import Decimal, ROUND_HALF_UP
from django.urls import reverse
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Count
from .models import Book, Category, Order, OrderItem, Payment, Coupon, Address
from .forms import ReviewForm, CheckoutAddressForm, CheckoutDeliveryForm, CheckoutPaymentForm, AddressBillingForm, AddressShippingForm
from django.db import transaction
from .emails import send_order_confirmation_email
from django.template.loader import render_to_string


SORT_MAP = {
    "new": "-created_at",
    "popular": "-reviews_count",   
    "price_asc": "price",
    "price_desc": "-price",
}

def catalog(request):
    qs = (Book.objects
          .select_related("category")
          .prefetch_related("authors")
          .annotate(reviews_count=Count("reviews")))
    
    total_count = qs.count()

    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)

    sort = request.GET.get("sort", "new")
    qs = qs.order_by(SORT_MAP.get(sort, "-created_at"))

    paginator = Paginator(qs, 8) 
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.annotate(total=Count("books"))

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "current_sort": sort,
        "current_category": int(category_id) if category_id and category_id.isdigit() else None,
        "total_count": total_count, 
    }
    return render(request, "./books/catalog.html", context)


def book_detail(request, book_id):
    book = get_object_or_404(
        Book.objects.prefetch_related('reviews', 'authors'),  
        id=book_id
    )
    reviews_qs = (book.reviews
                  .filter(status="processed")
                  .select_related("user")
                  .order_by("-created_at"))
    reviews_total = reviews_qs.count()
    paginator = Paginator(reviews_qs, 3)
    page1 = paginator.get_page(1)
    return render(request, "books/book_page.html", {
        "book": book,
        "reviews": page1.object_list, 
        "reviews_total": reviews_total, 
        "has_more_reviews": page1.has_next(),
        "next_reviews_page": 2,  
    })

@require_GET
def book_reviews_more(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    page = int(request.GET.get("page", 1))

    reviews_qs = (book.reviews
                  .filter(status="processed")
                  .select_related("user")
                  .order_by("-created_at"))
    
    paginator = Paginator(reviews_qs, 3)
    page_obj = paginator.get_page(page)

    html = render_to_string("books/_reviews_items.html", {
        "reviews": page_obj.object_list,
    }, request=request)

    return JsonResponse({
        "html": html,
        "has_next": page_obj.has_next(),
        "next_page": page + 1,
    })


def book_page(request):
    return render(request, "./books/catalog.html" )


@login_required(login_url="login")
def add_review(request, book_id):
    book = get_object_or_404(
        Book.objects.prefetch_related('reviews', 'authors'),
        id=book_id
    )

    reviews_qs = (book.reviews
                  .filter(status="processed")
                  .select_related("user")
                  .order_by("-created_at"))

    reviews_total = reviews_qs.count()
    paginator = Paginator(reviews_qs, 3)
    page1 = paginator.get_page(1)

    if request.method == "POST":
        form = ReviewForm(request.POST)

        if form.is_valid():
            review = form.save(commit=False)
            review.book = book
            review.user = request.user
            review.save()

            messages.success(
                request,
                "Thanks for your review. It will be published after admin approval."
            )
            fname = (request.POST.get("fname") or "").strip()
            lname = (request.POST.get("lname") or "").strip()
            fields = []
            if fname:
                request.user.first_name = fname
                fields.append("first_name")
            if lname:
                request.user.last_name = lname
                fields.append("last_name")
            if fields:
                request.user.save(update_fields=fields)

            return redirect("book_detail", book_id=book.id)
    else:
        form = ReviewForm()

    return render(request, "books/book_page.html", {
        "book": book,
        "reviews": page1.object_list,
        "reviews_total": reviews_total,
        "has_more_reviews": page1.has_next(),
        "next_reviews_page": 2,
        "form": form, 
    })

    



def cart_page(request):
    next_url = request.GET.get("next")
    if next_url:
        request.session["cart_next"] = next_url

    if request.user.is_authenticated:
        cart = Order.objects.filter(
            user=request.user,
            status=Order.Status.CART
        ).first()

        if not cart:
            return render(request, "cart/cart.html", {"items": [], "total": Decimal("0.00")})
        
        qs = cart.items.select_related("book")

        items = []
        subtotal = Decimal("0.00")
        total = Decimal("0.00")

        for item in qs:
            unit_price = item.unit_price if item.unit_price is not None else item.book.price
            subtotal_item = (unit_price * item.quantity).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )
            items.append({
                "book": item.book,
                "qty": item.quantity,
                "subtotal": subtotal_item,
            })
            subtotal += subtotal_item
        discount =Decimal("0.00")
        if cart.coupon:
            discount = calculate_coupon_discount(cart, cart.coupon)
        
        subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = (subtotal - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return render(request, "cart/cart.html", {"cart": cart,"items": items,"subtotal": subtotal, "total": total, "discount": discount,})

    cart = request.session.get("cart", {})
    books = Book.objects.filter(id__in=cart.keys())

    items = []
    subtotal = Decimal("0.00")
    total = Decimal("0.00")
    for book in books:
        qty = cart[str(book.id)]["quantity"]
        subtotal_item = (book.price * qty).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
        items.append({"book": book, "qty": qty, "subtotal": subtotal_item})
        subtotal += subtotal_item
    
    discount = Decimal("0.00")
    code = request.session.get("coupon_code")
    if code:
        coupon = Coupon.objects.filter(code=code).first()
        if coupon:
            # discount only on subtotal
            if coupon.discount_type == Coupon.DiscountType.PERCENT:
                discount = (subtotal * (coupon.discount_value / Decimal("100"))).quantize(Decimal("0.01"))
            else:
                discount = coupon.discount_value
            discount = min(discount, subtotal)
    total = (subtotal - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return render(request, "cart/cart.html", {"items": items, "discount": discount, "subtotal": subtotal, "total": total})

def add_book_to_cart(request, book_id):
    quantity=int(request.POST.get("quantity", 1))
    if quantity < 1:
        quantity = 1

    if request.user.is_authenticated:
        book = get_object_or_404(Book, id=book_id)

        with transaction.atomic():
            cart, _ = Order.objects.get_or_create(
                user=request.user,
                status=Order.Status.CART,
            )

            item, created = OrderItem.objects.get_or_create(
                order=cart,
                book=book,
                defaults={"quantity": quantity, "unit_price": book.price},
            )
            if not created:
                item.quantity += quantity
                item.unit_price = book.price
                item.save(update_fields=["quantity", "unit_price"])

        cart_count = sum(cart.items.values_list("quantity", flat=True))

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "ok", "cart_count": cart_count})

        return redirect(request.META.get("HTTP_REFERER", "catalog"))


    cart = request.session.get("cart",{})
    book_id = str(book_id)

    if book_id not in cart:
        cart[book_id] = {"quantity": quantity}
    else:
        cart[book_id]["quantity"] += quantity

    request.session["cart"] = cart
    request.session.modified = True

    cart_count = sum(int(item.get("quantity", 0)) for item in cart.values())

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "status": "ok",
            "cart_count": cart_count,
        })

    return redirect(request.META.get("HTTP_REFERER", "catalog"))

def cart_update(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    
    data = json.loads(request.body)
    quantity = int(data.get("quantity", 1))
    book_id = str(data.get("book_id"))

    if quantity < 1:
        quantity = 1 

    if request.user.is_authenticated:
        book = get_object_or_404(Book, id=book_id)

        with transaction.atomic():
            cart = get_object_or_404(
                Order,
                user=request.user,
                status=Order.Status.CART,
            )

            item = get_object_or_404(
                OrderItem,
                order=cart,
                book=book,
            )

            item.quantity = quantity
            item.unit_price = book.price
            item.save(update_fields=["quantity", "unit_price"])

        subtotal_item = (item.unit_price * quantity).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        subtotal = sum(
            (i.unit_price * i.quantity).quantize(Decimal("0.01"))
            for i in cart.items.all()
        )

        discount =Decimal("0.00")
        if cart.coupon:
            discount = calculate_coupon_discount(cart, cart.coupon)

        total = (subtotal - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return JsonResponse({
            "status": "ok",
            "book_id": book_id,
            "quantity": quantity,
            "subtotal": f"{subtotal_item:.2f}",        
            "cart_subtotal": f"{subtotal:.2f}", 
            "discount": f"{discount:.2f}",
            "total": f"{total:.2f}",
        })

    cart = request.session.get("cart", {})    
    
    if book_id in cart:
        cart[book_id]["quantity"] = quantity

    book = get_object_or_404(Book, id=book_id)

    subtotal = (book.price * quantity).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    total = 0
    for bid, item in cart.items():
        b = Book.objects.get(id=bid)
        total += (b.price * item["quantity"]).quantize(
            Decimal("0.01"))
        
    discount = Decimal("0.00")
    code = request.session.get("coupon_code")
    if code:
        coupon = Coupon.objects.filter(code=code).first()
        if coupon and coupon.status == Coupon.Status.ACTIVE:
            if coupon.discount_type == Coupon.DiscountType.PERCENT:
                discount = total * (coupon.discount_value / Decimal("100"))
            else:
                discount = coupon.discount_value
            discount = min(discount, total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    total_after_discount = (total - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    request.session["cart"] = cart
    request.session.modified = True


    return JsonResponse({
        "status": "ok",
        "book_id": book_id,
        "quantity": quantity,
        "subtotal": f"{subtotal:.2f}",
        "cart_subtotal": f"{total:.2f}",
        "discount": f"{discount:.2f}",
        "total": f"{total_after_discount:.2f}",
    })


def delete_book_from_cart(request, book_id):
    if request.method != "POST":
        return redirect("cart")
    
    book_id = str(book_id)

    if request.user.is_authenticated:
        book = get_object_or_404(Book, id=book_id)

        with transaction.atomic():
            cart = get_object_or_404(
                Order,
                user=request.user,
                status=Order.Status.CART,
            )

            OrderItem.objects.filter(order=cart, book=book).delete()

            if not cart.items.exists():
                cart.delete()

        next_url = request.POST.get("next") or ""
        url = reverse("cart")
        if next_url:
            url = f"{url}?{urlencode({'next': next_url})}"

        return redirect(url)

    cart = request.session.get("cart",{})
    if book_id in cart:
        del cart[book_id]   

    request.session["cart"] = cart
    request.session.modified = True

    next_url = request.POST.get("next") or ""
    url = reverse("cart")
    if next_url:
        url = f"{url}?{urlencode({'next': next_url})}"

    return redirect(url)


@require_POST
def add_coupon(request):
    code = request.POST.get("code")

    try:
        if request.user.is_authenticated:
            cart = Order.objects.filter(
                user=request.user,
                status=Order.Status.CART
            ).first()
            if not cart:
                raise ValidationError("Cart is empty.")

            attach_coupon_to_cart(cart, code)
        else:
            attach_coupon_to_session(request, code)

        messages.success(request, "Coupon applied successfully.")
    except ValidationError as e:
        messages.error(request, e.message)

    return redirect("cart")


def calculate_coupon_discount(cart: Order, coupon: Coupon) -> Decimal:

    if not coupon:
        return Decimal("0.00")

    subtotal = Decimal("0.00")
    for item in cart.items.select_related("book").all():
        unit_price = item.unit_price if item.unit_price is not None else item.book.price
        subtotal += (unit_price * item.quantity)

    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if coupon.discount_type == Coupon.DiscountType.PERCENT:
        if coupon.discount_value > 100:
            raise ValidationError("Invalid percent discount.")
        discount = subtotal * (coupon.discount_value / Decimal("100"))
    else:  
        discount = coupon.discount_value

    discount = min(discount, subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return discount

def attach_coupon_to_cart(cart: Order, code: str) -> Coupon:

    code = (code or "").strip().upper()
    if not code:
        raise ValidationError("Please enter a coupon code.")

    coupon = Coupon.objects.filter(code=code).first()
    if not coupon:
        raise ValidationError("Invalid coupon code.")

    if coupon.status != Coupon.Status.ACTIVE:
        raise ValidationError("This coupon is not active.")

    now = timezone.now()
    if coupon.valid_from and now < coupon.valid_from:
        raise ValidationError("This coupon is not active yet.")
    if coupon.valid_until and now > coupon.valid_until:
        raise ValidationError("This coupon has expired.")

    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        if coupon.max_uses == 1:
            raise ValidationError("This coupon has already been used.")
        raise ValidationError("This coupon has reached its usage limit.")

    cart.coupon = coupon
    cart.save(update_fields=["coupon", "updated_at"])
    return coupon

def attach_coupon_to_session(request, code: str) -> Coupon:
    code = (code or "").strip().upper()
    if not code:
        raise ValidationError("Please enter a coupon code.")

    coupon = Coupon.objects.filter(code=code).first()
    if not coupon:
        raise ValidationError("Invalid coupon code.")

    if  coupon.status != Coupon.Status.ACTIVE:
        raise ValidationError("This coupon is not active.")

    now = timezone.now()
    if coupon.valid_from and now < coupon.valid_from:
        raise ValidationError("This coupon is not active yet.")
    if coupon.valid_until and now > coupon.valid_until:
        raise ValidationError("This coupon has expired.")

    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        if coupon.max_uses == 1:
            raise ValidationError("This coupon has already been used.")
        raise ValidationError("This coupon has reached its usage limit.")

    request.session["coupon_code"] = coupon.code
    request.session.modified = True
    return coupon

def checkout_missing_steps(cart: Order) -> list[str]:
    missing = []

    if not getattr(cart, "address", None):
        missing.append("address")

    if not cart.shipping_method_id or cart.shipping_price is None:
        missing.append("delivery")

    payment = getattr(cart, "payment", None)
    if not payment or not payment.card_last4 or not payment.expiry:
        missing.append("payment")

    return missing

def checkout_progress(cart):
    has_address = bool(getattr(cart, "address", None))
    has_delivery = bool(cart.shipping_method_id and cart.shipping_price is not None)

    payment = getattr(cart, "payment", None)
    has_payment = bool(payment and payment.card_last4 and payment.expiry)

    # Confirm "done" если всё заполнено
    has_confirm = has_address and has_delivery and has_payment

    return {
        "has_address": has_address,
        "has_delivery": has_delivery,
        "has_payment": has_payment,
        "has_confirm": has_confirm,
    }

def checkout_email(request):
    if request.user.is_authenticated:
        return redirect("checkout_address")
    return render(request, "order/checkout_email.html")

@login_required
def checkout_address(request):
    cart = Order.objects.filter(user=request.user, status=Order.Status.CART).first()

    if not cart or not cart.items.exists():
        return redirect("cart")

    subtotal = Decimal("0.00")
    for item in cart.items.select_related("book"):
        unit_price = item.unit_price or item.book.price
        subtotal += (unit_price * item.quantity)
    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount = Decimal("0.00")
    if cart.coupon:
        discount = calculate_coupon_discount(cart, cart.coupon)

    total = subtotal - discount

    existing = getattr(cart, "address", None)

    billing = Address.objects.filter(
        user=request.user,
        is_default_billing=True
    ).first()

    shipping = Address.objects.filter(
        user=request.user,
        is_default_shipping=True
    ).first()

    initial = {}
    if not existing:
        if billing:
            initial.update({
                "billing_first_name": billing.first_name,
                "billing_last_name": billing.last_name,
                "billing_country": billing.country,
                "billing_city": billing.city,
                "billing_address1": billing.address1,
                "billing_postcode": billing.postcode,
                "billing_phone": billing.phone,
            })
        if shipping:
            initial.update({
                "shipping_first_name": shipping.first_name,
                "shipping_last_name": shipping.last_name,
                "shipping_country": shipping.country,
                "shipping_city": shipping.city,
                "shipping_address1": shipping.address1,
                "shipping_postcode": shipping.postcode,
                "shipping_phone": shipping.phone,
            })

    if request.method == "POST":
        data = request.POST.copy()  
        use_billing = data.get("use_billing") in ("1", "on", "true", "True")

        if use_billing:
            pairs = [
                ("billing_first_name", "shipping_first_name"),
                ("billing_last_name", "shipping_last_name"),
                ("billing_country", "shipping_country"),
                ("billing_city", "shipping_city"),
                ("billing_address1", "shipping_address1"),
                ("billing_postcode", "shipping_postcode"),
                ("billing_phone", "shipping_phone"),
            ]
            for src, dst in pairs:
                data[dst] = data.get(src, "")

        form = CheckoutAddressForm(data, instance=existing)
        if form.is_valid():
            with transaction.atomic():
                addr = form.save(commit=False)
                addr.order = cart
                addr.save()

            next_step = request.POST.get("next") or request.GET.get("next")
            if next_step == "confirm":
                return redirect("checkout_confirm")
            return redirect("checkout_delivery")
    else:
        form = CheckoutAddressForm(instance=existing,  initial=initial)
    progress = checkout_progress(cart)
    return render(request, "order/checkout_address.html", {"form": form, "cart": cart, "discount": discount,"subtotal": subtotal, "total": total, "step": 1, **progress,})


@login_required
def checkout_delivery(request):
    cart = Order.objects.filter(user=request.user, status=Order.Status.CART).first()
    if not cart or not cart.items.exists():
        return redirect("cart")
    
    missing = checkout_missing_steps(cart)
    if "address" in missing:
        return redirect("checkout_address")
    
    subtotal = Decimal("0.00")
    for item in cart.items.select_related("book"):
        unit_price = item.unit_price or item.book.price
        subtotal += (unit_price * item.quantity)
    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if request.method == "POST":
        form = CheckoutDeliveryForm(request.POST)
        if form.is_valid():
            method = form.cleaned_data["shipping_method"]

            with transaction.atomic():
                cart.shipping_method = method
                cart.shipping_price = method.price  
                cart.save(update_fields=["shipping_method", "shipping_price", "updated_at"])

            next_step = request.POST.get("next") or request.GET.get("next")
            if next_step == "confirm":
                return redirect("checkout_confirm")
            return redirect("checkout_payment")
    else:
        form = CheckoutDeliveryForm(initial={
            "shipping_method": cart.shipping_method_id
        } if cart.shipping_method_id else None)

    methods = form.fields["shipping_method"].queryset
    shipping_price = cart.shipping_price or Decimal("0.00")
    discount = Decimal("0.00")
    if cart.coupon:
        discount = calculate_coupon_discount(cart, cart.coupon)
    total = subtotal - discount + shipping_price
    progress = checkout_progress(cart) 

    return render(request, "order/checkout_delivery.html", {
        "form": form,
        "methods": methods,              
        "subtotal": subtotal,
        "discount": discount,
        "shipping_price": shipping_price,
        "total": total,
        "step": 2,
        **progress,
    })

@login_required
def checkout_payment(request):
    cart = Order.objects.filter(user=request.user, status=Order.Status.CART).first()
    if not cart or not cart.items.exists():
        return redirect("cart")
    
    missing = checkout_missing_steps(cart)
    if "address" in missing:
        return redirect("checkout_address")
    if "delivery" in missing:
        return redirect("checkout_delivery")
    
    subtotal = Decimal("0.00")
    for item in cart.items.select_related("book"):
        unit_price = item.unit_price or item.book.price
        subtotal += (unit_price * item.quantity)
    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    shipping_price = cart.shipping_price or Decimal("0.00")
    discount = Decimal("0.00")
    if cart.coupon:
        discount = calculate_coupon_discount(cart, cart.coupon)
    
    total = subtotal - discount + shipping_price

    if request.method == "POST":
        form = CheckoutPaymentForm(request.POST)
        if form.is_valid():
            digits = form.cleaned_data["card_number"]
            expiry = form.cleaned_data["expiry"]
            last4 = digits[-4:]

            with transaction.atomic():
                payment, _ = Payment.objects.get_or_create(order=cart)
                payment.card_last4 = last4
                payment.expiry = expiry 
                payment.save(update_fields=["card_last4", "expiry"])

            return redirect("checkout_confirm") 
    else:
        form = CheckoutPaymentForm()
    progress = checkout_progress(cart)

    return render(request, "order/checkout_payment.html", {   
        "form": form,           
        "subtotal": subtotal,
        "discount": discount,
        "shipping_price": shipping_price,
        "total": total,
        "step": 3,
        **progress,
    })

@login_required
def checkout_confirm(request):
    cart = Order.objects.filter(user=request.user, status=Order.Status.CART).first()
    if not cart or not cart.items.exists():
        return redirect("cart")
    
    missing = checkout_missing_steps(cart)
    if "address" in missing:
        return redirect("checkout_address")
    if "delivery" in missing:
        return redirect("checkout_delivery")
    if "payment" in missing:
        return redirect("checkout_payment")
    
    
    items = []
    subtotal = Decimal("0.00")

    for item in cart.items.all():
        unit_price = item.unit_price if item.unit_price is not None else item.book.price
        line_total = (unit_price * item.quantity)

        items.append({
            "obj": item,                 
            "book": item.book,
            "quantity": item.quantity,
            "unit_price": unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "line_total": line_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        })

        subtotal += line_total

    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    shipping_price = (cart.shipping_price or Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount = Decimal("0.00")
    if cart.coupon:
        discount = calculate_coupon_discount(cart, cart.coupon)

    total = subtotal - discount + shipping_price
    total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) 
    progress = checkout_progress(cart)

    return render(request, "order/checkout_confirm.html", {
        "cart": cart,
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "shipping_price": shipping_price,
        "total": total,
        "step": 4,
        **progress,
    })

@login_required
@require_POST
def place_order(request):
    cart = Order.objects.filter(
        user=request.user,
        status=Order.Status.CART
    ).first()

    if not cart or not cart.items.exists():
        return redirect("cart")
    
    missing = checkout_missing_steps(cart)
    if missing:
        messages.error(request, "Please complete all checkout steps before placing the order.")
        if "address" in missing:
            return redirect("checkout_address")
        if "delivery" in missing:
            return redirect("checkout_delivery")
        return redirect("checkout_payment")

    with transaction.atomic():
        subtotal = Decimal("0.00")
        for item in cart.items.select_related("book"):
            unit_price = item.unit_price if item.unit_price is not None else item.book.price
            item.unit_price = unit_price
            item.subtotal = (unit_price * item.quantity).quantize(Decimal("0.01"))
            item.save(update_fields=["unit_price", "subtotal"])
            subtotal += item.subtotal

        shipping = cart.shipping_price or Decimal("0.00")
        discount = Decimal("0.00")
        coupon = None
        if cart.coupon:
            coupon = Coupon.objects.select_for_update().get(id=cart.coupon_id)
            if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
                raise ValidationError("Coupon limit reached.")
            discount = calculate_coupon_discount(cart, cart.coupon)
            cart.coupon.used_count += 1
            cart.coupon.save(update_fields=["used_count"])

        cart.total_amount = (subtotal - discount + shipping).quantize(Decimal("0.01"))
        cart.discount_amount = discount
        cart.status = Order.Status.WAITING
        cart.ordered_at = timezone.now()
        cart.save(update_fields=["total_amount", "status", "ordered_at", "discount_amount"])

        transaction.on_commit(lambda: send_order_confirmation_email(cart.id))

    return redirect("checkout_complete", order_id=cart.id)

@login_required
def checkout_complete(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
        status__in=[Order.Status.WAITING, Order.Status.IN_PROGRESS, Order.Status.IN_DELIVERY, Order.Status.DELIVERED]
    )
    items = order.items.select_related("book").all()
    subtotal = sum((i.subtotal or Decimal("0.00")) for i in items)
    discount = (order.discount_amount or Decimal("0.00")).quantize(Decimal("0.01"))

    return render(request, "order/checkout_complete.html", {
        "order": order,
        "items": items,
        "discount": discount,
        "subtotal": subtotal,
        "email": request.user.email, 
        "step": 5,
        "has_address": True,
        "has_delivery": True,
        "has_payment": True,
        "has_confirm": True, 
    })

@login_required
def view_orders(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .exclude(status=Order.Status.CART)
        .prefetch_related("items__book")
        .order_by("-ordered_at", "-created_at")
    )

    status_map = dict(Order.Status.choices)
    selected_status = request.GET.get("status", "").strip()

    if selected_status and selected_status in status_map:
        orders = orders.filter(status=selected_status)

    return render(request, "order/view_orders.html", {
        "orders": orders,
        "status_map": status_map,
        "selected_status": selected_status,
        "statuses": Order.Status.choices,
    })
    
@login_required
def view_order_details(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
        status__in=[Order.Status.WAITING, Order.Status.IN_PROGRESS, Order.Status.IN_DELIVERY, Order.Status.DELIVERED, Order.Status.CANCELED]
    )
    items = order.items.select_related("book").all()
    subtotal = sum((i.subtotal or Decimal("0.00")) for i in items)
    discount = (order.discount_amount or Decimal("0.00")).quantize(Decimal("0.01"))

    return render(request, "order/view_order_details.html", {
        "order": order,
        "items": items,
        "discount": discount,
        "subtotal": subtotal
    })

@login_required
def settings_page(request):
    billing = Address.objects.filter(
        user=request.user,
        is_default_billing=True
    ).first()

    shipping = Address.objects.filter(
        user=request.user,
        is_default_shipping=True
    ).first()

    billing_form = AddressBillingForm(instance=billing)
    shipping_form = AddressShippingForm(instance=shipping)

    return render(request, "profile/settings.html", {
        "billing_form": billing_form,
        "shipping_form": shipping_form,
        "active_tab": "address",
    })
    

@login_required
def settings_billing_save(request):
    billing = Address.objects.filter(
        user=request.user,
        is_default_billing=True
    ).first()
    if request.method == "POST":
        billing_form = AddressBillingForm(request.POST, instance=billing)
        if billing_form.is_valid():
            obj = billing_form.save(commit=False)
            obj.user = request.user
            obj.is_default_billing = True
            obj.save()
            messages.success(request, "Billing address saved.")
            return redirect("settings_page")

@login_required    
def settings_shipping_save(request):
    shipping = Address.objects.filter(
        user=request.user,
        is_default_shipping=True
    ).first()
    shipping_form = AddressShippingForm(request.POST, instance=shipping)
    if shipping_form.is_valid():
        obj = shipping_form.save(commit=False)
        obj.user = request.user
        obj.is_default_shipping = True
        obj.save()
        messages.success(request, "Shipping address saved.")
        return redirect("settings_page")

@login_required       
def settings_profile_save(request):

    fname = request.POST.get("fname")
    lname = request.POST.get("lname")

    if fname:
        request.user.first_name = fname
    if lname:
        request.user.last_name = lname
        request.user.save()

    avatar = request.FILES.get("avatar")
    if avatar:
        profile = request.user.profile
        profile.avatar = avatar
        profile.save()

    messages.success(request, "Profile updated.")
    return redirect(f"{reverse('settings_page')}?tab=profile")

@login_required
def settings_email_save(request):
    email = (request.POST.get("email") or "").strip()

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Enter a valid email.")
        return redirect(f"{reverse('settings_page')}?tab=privacy")

    request.user.email = email
    request.user.save(update_fields=["email"])

    messages.success(request, "Email updated.")
    return redirect(f"{reverse('settings_page')}?tab=privacy")

def settings_password_save(request):
    old_password = request.POST.get("old_password") or ""
    new_password = request.POST.get("new_password") or ""
    confirm_password = request.POST.get("confirm_password") or ""

    if not request.user.check_password(old_password):
        messages.error(request, "Old password is incorrect.")
        return redirect(f"{reverse('settings_page')}?tab=privacy")

    if not new_password:
        messages.error(request, "New password cannot be empty.")
        return redirect(f"{reverse('settings_page')}?tab=privacy")

    if new_password != confirm_password:
        messages.error(request, "Passwords do not match.")
        return redirect(f"{reverse('settings_page')}?tab=privacy")

    request.user.set_password(new_password)
    request.user.save()

    update_session_auth_hash(request, request.user)  

    messages.success(request, "Password updated.")
    return redirect(f"{reverse('settings_page')}?tab=privacy")
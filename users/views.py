from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.db import transaction
from django.utils.crypto import get_random_string

from .emails import send_temporary_password_email
from shop.cart_utils import merge_session_cart_to_db

def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_active=False
            user.save(update_fields=["is_active"])    
            print(user)
               
            return redirect("home")   
        else:
            print("SIGNUP ERRORS:", form.errors.as_json())
    else:
        form = UserCreationForm()
    return render(request, "sign_up.html", {"form": form})

def log_in(request):
    if request.method == "POST":
        username = request.POST.get("username")  
        password = request.POST.get("password")
        next_url = request.POST.get("next") or request.GET.get("next") or "home"

        user = authenticate(request, username=username, password=password)  
       
        if user is not None:
            login(request, user)
            merge_session_cart_to_db(request, user)
            return redirect(next_url)

        # Ошибка пароля — остаёмся на checkout_email, если логинились оттуда
        if "checkout" in (next_url or ""):
            return render(request, "order/checkout_email.html", {
            "login_error": "Invalid email or password."
        })
        return render(request, "login.html", {
            "error": "Invalid username or password"
        })
    return render(request, "login.html")

def log_out(request):
    logout(request)
    return redirect("home")

def quick_register(request):
    if request.method != "POST":
        return redirect("checkout_email")

    email = (request.POST.get("username") or "").strip().lower()
    next_url = request.POST.get("next") or "checkout_address"

    if not email:
        return render(request, "order/checkout_email.html", {
            "quick_register_error": "Please enter your email."
        })

    if User.objects.filter(username=email).exists():
        return render(request, "order/checkout_email.html", {
            "quick_register_error": "This email is already registered. Please log in."
        })

    temp_password = get_random_string(
        length=10,
        allowed_chars="abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    )

    user = User.objects.create_user(
        username=email,
        email=email,
        password=temp_password,
    )

    transaction.on_commit(lambda: send_temporary_password_email(user, temp_password))

    login(request, user)
    merge_session_cart_to_db(request, user)

    messages.success(
        request,
        "Account created. We sent a temporary password to your email."
    )
    return redirect(next_url)
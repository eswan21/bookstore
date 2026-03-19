from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.db import transaction
from django.utils.crypto import get_random_string
from datetime import timedelta
from django.utils import timezone

from .emails import send_temporary_password_email, send_verification_email
from shop.cart_utils import merge_session_cart_to_db

def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_active=True
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

def forgot_password(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        if not email:
            return render(request, "forgot_password.html", {
                "forgot_password_error": "Please enter your email."
            })
        user = User.objects.filter(username=email).first()
        if not user:
            return render(request, "forgot_password.html", {
                "forgot_password_error": "This email is not registered. Please sign up."
            })
        
        code = get_random_string(length=6, allowed_chars='0123456789')

        expires_at = timezone.now() + timedelta(minutes=10)

        request.session["password_reset_code"] = code
        request.session["password_reset_email"] = email
        request.session["password_reset_expires_at"] = expires_at.isoformat()

        transaction.on_commit(lambda: send_verification_email (user, code))
        return render(request, "verification_code.html")

    return render(request, "forgot_password.html")

def verify_code(request):
    if request.method == "POST":
        entered_code = (request.POST.get("code") or "").strip()

        session_code = request.session.get("password_reset_code")
        email = request.session.get("password_reset_email")
        expires_at_str = request.session.get("password_reset_expires_at")

        if not session_code or not email or not expires_at_str:
            messages.error(request, "Session expired. Please try again.")
            return redirect("forgot_password")

        expires_at = timezone.datetime.fromisoformat(expires_at_str)
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())

        if timezone.now() > expires_at:
            request.session.pop("password_reset_code", None)
            request.session.pop("password_reset_email", None)
            request.session.pop("password_reset_expires_at", None)
            request.session.pop("password_reset_verified", None)

            return render(request, "verification_code.html", {
                "error": "Verification code has expired. Please request a new one."
            })

        if entered_code != session_code:
            return render(request, "verification_code.html", {
                "error": "Invalid verification code."
            })

        request.session.pop("password_reset_code", None)
        request.session.pop("password_reset_expires_at", None)
        request.session["password_reset_verified"] = True

        return redirect("reset_password")

    return redirect("forgot_password")

def reset_password(request):
    email = request.session.get("password_reset_email")
    verified = request.session.get("password_reset_verified")

    if not email or not verified:
        messages.error(request, "Password reset session expired. Please try again.")
        return redirect("forgot_password")

    user = User.objects.filter(username=email).first()
    if not user:
        messages.error(request, "User not found.")
        return redirect("forgot_password")

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)

        if form.is_valid():
            form.save()

            request.session.pop("password_reset_email", None)
            request.session.pop("password_reset_verified", None)
            request.session.pop("password_reset_expires_at", None)

            messages.success(request, "Your password has been changed successfully. Please log in.")
            return redirect("login")
    else:
        form = SetPasswordForm(user)

    return render(request, "reset_password.html", {"form": form})
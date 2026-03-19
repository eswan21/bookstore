from django.urls import path
from . import views

urlpatterns = [
    path("books/", views.catalog, name="catalog"),
    path("books/<int:book_id>/", views.book_detail, name="book_detail"),
    path("books/", views.book_page, name="book_page"),
    path("books/<int:book_id>/reviews/", views.book_reviews_more, name="book_reviews_more"),
    path("books/<int:book_id>/review/", views.add_review, name="add_review"),
    path("cart/", views.cart_page, name="cart"),
    path("cart/add/<int:book_id>/", views.add_book_to_cart,  name="add_book_to_cart"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/delete/<int:book_id>/", views.delete_book_from_cart, name="delete_book_from_cart"),
    path("cart/apply-coupon/", views.add_coupon, name="add_coupon"),
    path("checkout/", views.checkout_email, name="checkout_email"),
    path("checkout/address/", views.checkout_address, name="checkout_address"),
    path("checkout/delivery/", views.checkout_delivery, name="checkout_delivery"),
    path("checkout/payment/", views.checkout_payment, name="checkout_payment"),
    path("checkout/confirm/", views.checkout_confirm, name="checkout_confirm"),
    path("checkout/place_order", views.place_order, name="place_order"),
    path("checkout/complete/<int:order_id>/", views.checkout_complete, name="checkout_complete"),
    path("orders/", views.view_orders, name="view_orders"),
    path("orders/details/<int:order_id>/", views.view_order_details, name="view_order_details"),
    path("settings/", views.settings_page, name="settings_page"),  
    path("settings/address/billing/", views.settings_billing_save, name="settings_billing_save"),
    path("settings/address/shipping/", views.settings_shipping_save, name="settings_shipping_save"),
    path("settings/profile/", views.settings_profile_save, name="settings_profile_save"),
    path("settings/privacy/email/", views.settings_email_save, name="settings_email_save"),
    path("settings/privacy/password/", views.settings_password_save, name="settings_password_save"),
]


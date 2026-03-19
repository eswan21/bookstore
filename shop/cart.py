# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render, get_object_or_404, redirect
# from django.db.models import Count
# from .models import Book, Category
# from .forms import ReviewForm

# CART = {
#  "name_book", "price" ,"quantity"
# }

# def add_book_to_cart(request, book_id, quantity):
#     book = get_object_or_404(Book, id=book_id)
#     CART["name_book"] = book["title"]
#     CART["price"] = book["price"]
#     CART["quantity"] = quantity
#     return redirect()
from django.contrib import admin
from .models import Author, Category, Book, Review, Order, OrderItem, Address, OrderAddress, ShippingMethod, Coupon
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile

User = get_user_model()


class ProfileInline(admin.StackedInline):  
    model = Profile
    can_delete = False
    extra = 0


admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

class OrderAddressInline(admin.StackedInline):
    model = OrderAddress
    extra = 0
    can_delete = False

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name")
    search_fields = ("first_name", "last_name")
    ordering = ("last_name", "first_name")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "get_authors", "category", "price", "publication_year", "created_at")
    list_filter = ("category", "publication_year")
    search_fields = ("title", "description", "authors__first_name", "authors__last_name")
    autocomplete_fields = ("category",)
    filter_horizontal = ("authors",)  # удобный виджет для M2M
    readonly_fields = ("created_at",)

    def get_authors(self, obj):
        return ", ".join(str(a) for a in obj.authors.all())
    get_authors.short_description = "Authors"

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total_amount", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username",)
    inlines = [OrderItemInline, OrderAddressInline]
    readonly_fields = ("created_at", "updated_at")

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("book__title", "user__username", "comment")
    readonly_fields = ("created_at",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "address1",
        "city",
        "country",
        "is_default_shipping",
        "is_default_billing",
        "created_at",
    )
    list_filter = ("country", "is_default_shipping", "is_default_billing")
    search_fields = ("user__username", "address1", "city", "postcode")

@admin.register(OrderAddress)
class OrderAddressAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "billing_city",
        "billing_country",
        "shipping_city",
        "shipping_country",
    )
    search_fields = (
        "billing_city",
        "shipping_city",
        "billing_postcode",
        "shipping_postcode",
    )

@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "delivery_time", "price", "is_active", "sort_order")
    list_editable = ("delivery_time", "price", "is_active", "sort_order")
    ordering = ("sort_order", "price")

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "status",
        "max_uses",
        "used_count",
        "valid_until",
    )

    list_filter = (
        "status",
        "discount_type",
    )

    search_fields = ("code",)

    readonly_fields = ("used_count", "created_at")

    ordering = ("-created_at",)
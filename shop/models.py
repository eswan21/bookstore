from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django_countries.fields import CountryField

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.user.username} profile"


class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100)
    description = models.TextField(max_length=2000, blank=True)

    class Meta:
        unique_together = ('first_name', 'last_name')
        ordering = ('last_name', 'first_name')

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200, unique=True)

    authors = models.ManyToManyField(Author, related_name='books', blank=False)

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')

    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField(max_length=5000, blank=True)
    publication_year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1450), MaxValueValidator(2100)]
    )
    dimensions = models.CharField(max_length=100, blank=True)   # например "20x13x3 см"
    materials = models.CharField(max_length=100, blank=True)

    image1 = models.ImageField(upload_to='books/%Y/%m/', blank=True, null=True)
    image2 = models.ImageField(upload_to='books/%Y/%m/', blank=True, null=True)
    image3 = models.ImageField(upload_to='books/%Y/%m/', blank=True, null=True)
    image4 = models.ImageField(upload_to='books/%Y/%m/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('title',)

    def __str__(self):
        return self.title


class Review(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        PROCESSED = 'processed', 'Обработан'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    comment = models.TextField(max_length=2000)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)


# ---- Заказ и позиции заказа ----

PHONE_VALIDATOR = RegexValidator(
    regex=r'^\+?[0-9\s\-()]{7,20}$',
    message='Введите номер телефона в формате +123456789'
)

class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses"
    )

    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100)

    country  = CountryField()
    city     = models.CharField(max_length=100)
    address1 = models.CharField(max_length=255)
    address2 = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=20)

    phone = models.CharField(max_length=32, validators=[PHONE_VALIDATOR])

    is_default_shipping = models.BooleanField(default=False)
    is_default_billing  = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f'{self.address1}, {self.city}'
    
class ShippingMethod(models.Model):
    name = models.CharField(max_length=120)

    delivery_time = models.CharField(max_length=100)  

    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "price", "name"]

    def __str__(self):
        return f"{self.name} — {self.delivery_time} — €{self.price}"
    
    
class Coupon(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"
        EXPIRED = "expired", "Expired"

    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percent"
        AMOUNT = "amount", "Fixed amount"

    code = models.CharField(max_length=40, unique=True)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True, db_index=True)

    max_uses = models.PositiveIntegerField(null=True, blank=True)  
    used_count = models.PositiveIntegerField(default=0)

    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        default=DiscountType.PERCENT,
    )

    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    ) 

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid_now(self) -> bool:
        if not self.is_active or self.status != self.Status.ACTIVE:
            return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.is_single_use and self.used_count >= 1:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True

    def clean(self):
        if self.discount_type == self.DiscountType.PERCENT:
            if self.discount_value > 100:
                raise ValidationError(
                    {"discount_value": "Percent discount cannot be greater than 100."}
                )
        super().clean()

    def __str__(self):
        return self.code



class Order(models.Model):
    class Status(models.TextChoices):
        CART        = 'cart',        'Cart'
        IN_PROGRESS = 'in_progress', 'In Progress'
        WAITING     = 'waiting',     'Waiting for processing'
        IN_DELIVERY = 'in_delivery', 'In Delivery'
        DELIVERED   = 'delivered',   'Delivered'
        CANCELED    = 'canceled',    'Canceled'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CART)
    shipping_method = models.ForeignKey(
        ShippingMethod, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    shipping_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
        null=True, blank=True
    )
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL,related_name="orders")
    discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        default=0,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ordered_at = models.DateTimeField(null=True, blank=True)

    # Итоговая сумма заказа (фиксируем на момент покупки)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True,)


    def __str__(self):
        return f'Order #{self.pk} — {self.get_status_display()}'
    
class OrderAddress(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="address")

    billing_first_name = models.CharField(max_length=100)
    billing_last_name  = models.CharField(max_length=100)
    billing_country    = CountryField()
    billing_city       = models.CharField(max_length=100)
    billing_address1   = models.CharField(max_length=255)
    billing_address2   = models.CharField(max_length=255, blank=True)
    billing_postcode   = models.CharField(max_length=20)
    billing_phone      = models.CharField(max_length=32, validators=[PHONE_VALIDATOR])

    shipping_first_name = models.CharField(max_length=100)
    shipping_last_name  = models.CharField(max_length=100)
    shipping_country    = CountryField()
    shipping_city       = models.CharField(max_length=100)
    shipping_address1   = models.CharField(max_length=255)
    shipping_address2   = models.CharField(max_length=255, blank=True)
    shipping_postcode   = models.CharField(max_length=20)
    shipping_phone      = models.CharField(max_length=32, validators=[PHONE_VALIDATOR])

    class Meta:
        verbose_name = "Order address"
        verbose_name_plural = "Order addresses"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    book  = models.ForeignKey(Book, on_delete=models.PROTECT, related_name='order_items')
    quantity   = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)
    subtotal   = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        constraints = [
            models.UniqueConstraint(fields=["order", "book"], name="uniq_order_book")
        ]

    @property
    def dynamic_subtotal(self) -> Decimal:
        """
        Текущая сумма позиции по актуальной цене книги (для корзины).
        """
        return self.book.price * self.quantity

    def __str__(self):
        return f'{self.book} x {self.quantity}'
    
class Payment(models.Model):
    order = models.OneToOneField(
        "Order",
        on_delete=models.CASCADE,
        related_name="payment"
    )
    card_last4 = models.CharField(max_length=4, blank=True)
    name_on_card = models.CharField(max_length=120)

    expiry = models.CharField(max_length=5,null=True, blank=True)

    is_paid = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    


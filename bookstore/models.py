# # app/models.py
# from django.conf import settings
# from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
# from django.db import models


# class Author(models.Model):
#     first_name = models.CharField(max_length=100)
#     last_name  = models.CharField(max_length=100)
#     description = models.TextField(max_length=2000, blank=True)

#     class Meta:
#         unique_together = ('first_name', 'last_name')
#         ordering = ('last_name', 'first_name')

#     def __str__(self):
#         return f'{self.first_name} {self.last_name}'


# class Category(models.Model):
#     name = models.CharField(max_length=120, unique=True)

#     class Meta:
#         ordering = ('name',)

#     def __str__(self):
#         return self.name


# class Book(models.Model):
#     title = models.CharField(max_length=200, unique=True)

#     authors = models.ManyToManyField(Author, related_name='books', blank=False)

#     category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')

#     price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
#     description = models.TextField(max_length=5000, blank=True)
#     publication_year = models.PositiveSmallIntegerField(
#         validators=[MinValueValidator(1450), MaxValueValidator(2100)]
#     )
#     dimensions = models.CharField(max_length=100, blank=True)   # например "20x13x3 см"
#     materials = models.CharField(max_length=100, blank=True)

#     image1 = models.ImageField(upload_to='books/%Y/%m/', blank=True, null=True)
#     image2 = models.ImageField(upload_to='books/%Y/%m/', blank=True, null=True)
#     image3 = models.ImageField(upload_to='books/%Y/%m/', blank=True, null=True)
#     image4 = models.ImageField(upload_to='books/%Y/%m/', blank=True, null=True)
    
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ('title',)

#     def __str__(self):
#         return self.title


# class Review(models.Model):
#     class Status(models.TextChoices):
#         NEW = 'new', 'Новый'
#         PROCESSED = 'processed', 'Обработан'

#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
#     book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
#     rating = models.PositiveSmallIntegerField(
#         validators=[MinValueValidator(1), MaxValueValidator(5)],
#         default=5
#     )
#     comment = models.TextField(max_length=2000)
#     status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ('-created_at',)


# # ---- Заказ и позиции заказа ----

# PHONE_VALIDATOR = RegexValidator(
#     regex=r'^\+?[0-9\s\-()]{7,20}$',
#     message='Введите номер телефона в формате +123456789'
# )

# class Order(models.Model):
#     class Status(models.TextChoices):
#         IN_PROGRESS = 'in_progress', 'В процессе'
#         DELIVERED   = 'delivered',   'Доставлен'
#         CANCELED    = 'canceled',    'Отменён'

#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
#     status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     # Итоговая сумма заказа (фиксируем на момент покупки)
#     total_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

#     # Доставка (shipping)
#     shipping_first_name = models.CharField(max_length=100)
#     shipping_last_name  = models.CharField(max_length=100)
#     shipping_country    = models.CharField(max_length=100)
#     shipping_city       = models.CharField(max_length=100)
#     shipping_address1   = models.CharField("Адрес (строка 1)", max_length=255)
#     shipping_address2   = models.CharField("Адрес (строка 2)", max_length=255, blank=True)
#     shipping_postcode   = models.CharField(max_length=20, blank=True)
#     shipping_phone      = models.CharField(max_length=32, validators=[PHONE_VALIDATOR], blank=True)

#     # Платёжный адрес (billing) — может отличаться от адреса доставки
#     billing_first_name = models.CharField(max_length=100)
#     billing_last_name  = models.CharField(max_length=100)
#     billing_country    = models.CharField(max_length=100)
#     billing_city       = models.CharField(max_length=100)
#     billing_address1   = models.CharField("Адрес (строка 1)", max_length=255)
#     billing_address2   = models.CharField("Адрес (строка 2)", max_length=255, blank=True)
#     billing_postcode   = models.CharField(max_length=20, blank=True)
#     billing_phone      = models.CharField(max_length=32, validators=[PHONE_VALIDATOR], blank=True)
#     billing_email      = models.EmailField(blank=True)

#     # Платёжные данные (безопасно)
#     payment_provider   = models.CharField(max_length=50, blank=True)   # 'stripe', 'yookassa', ...
#     payment_token      = models.CharField(max_length=255, blank=True)  # токен/идентификатор транзакции у провайдера
#     card_brand         = models.CharField(max_length=20, blank=True)   # 'visa', 'mastercard'
#     card_last4         = models.CharField(max_length=4, blank=True)

#     class Meta:
#         ordering = ('-created_at',)

#     def __str__(self):
#         return f'Order #{self.pk} — {self.get_status_display()}'


# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
#     book  = models.ForeignKey(Book, on_delete=models.PROTECT, related_name='order_items')
#     quantity   = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
#     unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])  # цена на момент заказа
#     subtotal   = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

#     class Meta:
#         verbose_name = 'Позиция заказа'
#         verbose_name_plural = 'Позиции заказа'

#     def __str__(self):
#         return f'{self.book} x {self.quantity}'

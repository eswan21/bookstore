from django import forms
from django.utils import timezone
from .models import Review, OrderAddress, ShippingMethod, Address
import re

class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        required=True,
        error_messages={
            "required": "Please select a rating."
        }
    )
    fname = forms.CharField(
        required=True,
        error_messages={
            "required": "Please write your First Name."
        }
    )
    lname = forms.CharField(
        required=True,
        error_messages={
            "required": "Please write your Last Name."
        }
    )
    comment = forms.CharField(
        required=True,
        error_messages={
            "required": "Please write your review."
        }
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]

class AddressBillingForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "first_name",
            "last_name",
            "country",
            "city",
            "address1",
            "postcode",
            "phone",
        ]

        error_messages = {
            "first_name": {
                "required": "Please enter your first name",
            },
            "last_name": {
                "required": "Please enter your last name",
            },
            "address1": {
                "required": "Please enter your address",
            },
            "city": {
                "required": "Please enter your city",
            },
            "postcode": {
                "required": "Please enter zip",
            },
            "phone": {
                "required": "Please enter phone number in format +355 66 123 4567"
            }
        }
        widgets = {
            "country": forms.Select(attrs={"class": "form-control"}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "address1": "Address",
            "city": "City",
            "postcode": "Zip",
            "phone": "Example +355 66 123 4567",
        }
        for name, field in self.fields.items():
            base = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (base + " form-control").strip()

            if name in placeholders and field.widget.input_type != "select":
                field.widget.attrs["placeholder"] = placeholders[name]

class AddressShippingForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "first_name",
            "last_name",
            "country",
            "city",
            "address1",
            "postcode",
            "phone",
        ]

        error_messages = {
            "first_name": {
                "required": "Please enter your first name",
            },
            "last_name": {
                "required": "Please enter your last name",
            },
            "address1": {
                "required": "Please enter your address",
            },
            "city": {
                "required": "Please enter your city",
            },
            "postcode": {
                "required": "Please enter zip",
            },
            "phone": {
                "required": "Please enter a valid phone",
            },
        }

        widgets = {
            "country": forms.Select(attrs={"class": "form-control"}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "address1": "Address",
            "city": "City",
            "postcode": "Zip",
            "phone": "Example +355 66 123 4567",
        }

        for name, field in self.fields.items():
            base = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (base + " form-control").strip()

            if name in placeholders and field.widget.input_type != "select":
                field.widget.attrs["placeholder"] = placeholders[name]

class CheckoutAddressForm(forms.ModelForm):
    class Meta:
        model = OrderAddress
        fields = [
            "billing_first_name",
            "billing_last_name",
            "billing_country",
            "billing_city",
            "billing_address1",
            "billing_postcode",
            "billing_phone",

            "shipping_first_name",
            "shipping_last_name",
            "shipping_country",
            "shipping_city",
            "shipping_address1",
            "shipping_postcode",
            "shipping_phone",
        ]

        error_messages = {
            "billing_first_name": {
                "required": "Please enter your first name",
            },
            "billing_last_name": {
                "required": "Please enter your last name",
            },
            "billing_address1": {
                "required": "Please enter your address",
            },
            "billing_city": {
                "required": "Please enter your city",
            },
            "billing_postcode": {
                "required": "Please enter zip",
            },
            "billing_phone": {
                "required": "Please enter phone number in format +355 66 123 4567"
            },
            "shipping_first_name": {
                "required": "Please enter your first name",
            },
            "shipping_last_name": {
                "required": "Please enter your last name",
            },
            "shipping_address1": {
                "required": "Please enter your address",
            },
            "shipping_city": {
                "required": "Please enter your city",
            },
            "shipping_postcode": {
                "required": "Please enter zip",
            },
            "shipping_phone": {
                "required": "Please enter a valid phone",
            },
        }

        widgets = {
            "billing_country": forms.Select(attrs={"class": "form-control"}),
            "shipping_country": forms.Select(attrs={"class": "form-control"}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            "billing_first_name": "First Name",
            "billing_last_name": "Last Name",
            "billing_address1": "Address",
            "billing_city": "City",
            "billing_postcode": "Zip",
            "billing_phone": "Example +355 66 123 4567",

            "shipping_first_name": "First Name",
            "shipping_last_name": "Last Name",
            "shipping_address1": "Address",
            "shipping_city": "City",
            "shipping_postcode": "Zip",
            "shipping_phone": "Phone",
        }

        for name, field in self.fields.items():
            base = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (base + " form-control").strip()

            if name in placeholders and field.widget.input_type != "select":
                field.widget.attrs["placeholder"] = placeholders[name]
            

class CheckoutDeliveryForm(forms.Form):
    shipping_method = forms.ModelChoiceField(
        queryset=ShippingMethod.objects.filter(is_active=True),
        empty_label=None,
        widget=forms.RadioSelect
    )
    
def luhn_ok(number: str) -> bool:
    digits = [int(d) for d in re.sub(r"\D", "", number)]
    if len(digits) < 12:   
        return False

    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

class CheckoutPaymentForm(forms.Form):
    card_number = forms.CharField(
        max_length=19,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Card Number"})
    )
    name_on_card = forms.CharField(
        max_length=120,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Name on Card"})
    )
    expiry = forms.CharField(
        max_length=5,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "MM/YY"})
    )
    cvv = forms.CharField(
        max_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "CVV"})
    )

    def clean_card_number(self):
        num = self.cleaned_data["card_number"]
        digits = re.sub(r"\D", "", num)
        if not digits.isdigit() or len(digits) not in (13, 14, 15, 16, 18, 19):
            raise forms.ValidationError("Please enter a valid credit card number.")
        if not luhn_ok(digits):
            raise forms.ValidationError("Please enter a valid credit card number.")
        return digits 

    def clean_cvv(self):
        cvv = re.sub(r"\D", "", self.cleaned_data["cvv"])
        if len(cvv) not in (3, 4):
            raise forms.ValidationError("Please enter a valid CVV.")
        return cvv
    
    
    def clean_expiry(self):
        expiry = self.cleaned_data["expiry"]

        if not re.match(r"^\d{2}/\d{2}$", expiry):
            raise forms.ValidationError("Use format MM/YY")

        month, year = expiry.split("/")
        month = int(month)
        year = int("20" + year)  # 25 → 2025

        if month < 1 or month > 12:
            raise forms.ValidationError("Invalid month")

        now = timezone.now()

        if year < now.year or (year == now.year and month < now.month):
            raise forms.ValidationError("Card has expired")

        return expiry
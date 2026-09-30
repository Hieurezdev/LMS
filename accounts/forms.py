from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from .models import User, GENDERS
from lms_manager.models import PaymentRequest


class CashierRegistrationForm(UserCreationForm):
    """Public registrations create cashier accounts only."""

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tên đăng nhập"}),
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Họ"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tên"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "email@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Số điện thoại"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("password1", "password2"):
            self.fields[field_name].widget.attrs.update({"class": "form-control"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.ROLE_CASHIER
        if commit:
            user.save()
        return user


class ApprovalAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        # Django superusers are created by the trusted createsuperuser command
        # and must not depend on the cashier approval workflow.
        if not user.is_superuser and not user.is_approved:
            raise ValidationError(
                "Tài khoản đang chờ quản trị viên duyệt.", code="pending_approval"
            )


class AdminCashierCreateForm(CashierRegistrationForm):
    """Used only by admins to issue an immediately active cashier account."""

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_approved = True
        user.is_active = True
        if commit:
            user.save()
        return user


class ProfileUpdateForm(UserChangeForm):
    email = forms.EmailField(
        widget=forms.TextInput(
            attrs={
                "type": "email",
                "class": "form-control",
            }
        ),
        label="Email Address",
    )

    first_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "type": "text",
                "class": "form-control",
            }
        ),
        label="First Name",
    )

    last_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "type": "text",
                "class": "form-control",
            }
        ),
        label="Last Name",
    )

    gender = forms.CharField(
        widget=forms.Select(
            choices=GENDERS,
            attrs={
                "class": "browser-default custom-select form-control",
            },
        ),
    )

    phone = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "type": "text",
                "class": "form-control",
            }
        ),
        label="Phone No.",
    )

    address = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "type": "text",
                "class": "form-control",
            }
        ),
        label="Address / city",
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "gender",
            "email",
            "phone",
            "address",
            "picture",
        ]


class PublicPaymentRequestForm(forms.ModelForm):
    class Meta:
        model = PaymentRequest
        fields = (
            "student_name",
            "classroom_name",
            "subject_name",
            "teacher_name",
            "payment_period_name",
            "amount",
            "payment_method",
            "payer_phone",
            "transaction_reference",
            "note",
        )
        labels = {
            "student_name": "Tên học sinh",
            "classroom_name": "Lớp học",
            "subject_name": "Môn học",
            "teacher_name": "Giảng viên",
            "payment_period_name": "Đợt thu",
            "amount": "Số tiền",
            "payment_method": "Hình thức thanh toán",
            "payer_phone": "Số điện thoại liên hệ",
            "transaction_reference": "Mã giao dịch (nếu có)",
            "note": "Ghi chú",
        }
        widgets = {
            "payment_period_name": forms.Select(
                choices=[(f"Đợt {number}", f"Đợt {number}") for number in range(1, 9)]
            ),
            "amount": forms.NumberInput(attrs={"min": 1, "step": 1}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["payment_method"].widget.attrs["class"] = "form-select"

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Số tiền phải lớn hơn 0.")
        return amount

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from .models import User, GENDERS
from lms_manager.models import Enrollment, Payment, PaymentRequest


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
    student_id = forms.IntegerField(widget=forms.HiddenInput)
    payment_period_name = forms.MultipleChoiceField(
        choices=[(f"Đợt {number}", f"Đợt {number}") for number in range(1, 9)],
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = PaymentRequest
        fields = (
            "enrollment",
            "student_name",
            "classroom_name",
            "subject_name",
            "teacher_name",
            "payment_period_name",
            "amount",
            "payment_method",
        )
        labels = {
            "student_name": "Tên học sinh",
            "classroom_name": "Lớp học",
            "subject_name": "Môn học",
            "teacher_name": "Giảng viên",
            "payment_period_name": "Đợt thu",
            "amount": "Số tiền",
            "payment_method": "Hình thức thanh toán",
        }
        widgets = {
            "enrollment": forms.HiddenInput(),
            "teacher_name": forms.HiddenInput(),
            "amount": forms.NumberInput(attrs={"min": 1, "step": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["payment_method"].widget.attrs["class"] = "form-select"
        self.fields["payment_period_name"].widget.attrs.pop("class", None)
        self.fields["enrollment"].widget.attrs.pop("class", None)
        self.fields["student_id"].widget.attrs.pop("class", None)
        self.fields["teacher_name"].widget.attrs.pop("class", None)
        for field_name in ("classroom_name", "subject_name", "teacher_name"):
            self.fields[field_name].required = False
            self.fields[field_name].widget.attrs["readonly"] = True
        self.fields["enrollment"].required = True
        self.fields["student_name"].widget.attrs.update({
            "autocomplete": "off",
            "placeholder": "Nhập tên học sinh để tìm kiếm...",
        })
        self.fields["classroom_name"].widget.attrs["placeholder"] = "Tự điền sau khi chọn học sinh"
        self.fields["subject_name"].widget.attrs["placeholder"] = "Tự điền sau khi chọn giảng viên"

    def clean(self):
        cleaned_data = super().clean()
        enrollment = cleaned_data.get("enrollment")
        student_id = cleaned_data.get("student_id")
        student_name = cleaned_data.get("student_name", "").strip()
        period_names = cleaned_data.get("payment_period_name", [])
        if not enrollment or not student_id:
            return cleaned_data

        enrollment = Enrollment.objects.select_related(
            "student__classroom", "teacher", "subject"
        ).filter(pk=enrollment.pk).first()
        if enrollment is None:
            raise forms.ValidationError("Đăng ký học không còn hợp lệ. Vui lòng chọn lại học sinh.")
        student = enrollment.student
        if student.pk != student_id or student.name.strip().casefold() != student_name.casefold():
            raise forms.ValidationError("Vui lòng chọn lại học sinh từ danh sách gợi ý.")
        if not student.classroom:
            raise forms.ValidationError("Học sinh này chưa được xếp lớp.")
        for period_name in period_names:
            if Payment.objects.filter(
                student=student,
                teacher=enrollment.teacher,
                payment_period__name=period_name,
            ).exists():
                raise forms.ValidationError(
                    f"Học sinh đã đóng {period_name} với giảng viên được chọn."
                )
            if PaymentRequest.objects.filter(
                enrollment=enrollment,
                payment_period_name=period_name,
                status=PaymentRequest.STATUS_PENDING,
            ).exists():
                raise forms.ValidationError(
                    f"{period_name} đã có yêu cầu đang chờ xác nhận."
                )

        cleaned_data.update(
            student_name=student.name,
            classroom_name=student.classroom.name,
            subject_name=enrollment.subject.name,
            teacher_name=enrollment.teacher.name,
        )
        return cleaned_data

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Số tiền phải lớn hơn 0.")
        return amount

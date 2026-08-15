from django.http.response import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import PasswordChangeForm
from .decorators import admin_required
from .forms import AdminCashierCreateForm, ApprovalAuthenticationForm, ProfileUpdateForm
from .models import User


class RoleLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = ApprovalAuthenticationForm

    def get_success_url(self):
        if self.request.user.is_cashier:
            return redirect("cashier_due_list").url
        return super().get_success_url()


def register(request):
    messages.info(request, "Tài khoản Thu ngân do Quản trị viên cấp.")
    return redirect("login")


def validate_username(request):
    username = request.GET.get("username", None)
    data = {"is_taken": User.objects.filter(username__iexact=username).exists()}
    return JsonResponse(data)


@login_required
def profile(request):
    return render(
        request,
        "accounts/profile.html",
        {
            "title": request.user.get_full_name,
            "user": request.user,
        },
    )


@login_required
@admin_required
def profile_single(request, id):
    if request.user.id == id:
        return redirect("profile")

    user = get_object_or_404(User, pk=id)
    return render(
        request,
        "accounts/profile_single.html",
        {
            "title": user.get_full_name,
            "user": user,
        },
    )


@login_required
@admin_required
def admin_panel(request):
    return render(
        request,
        "setting/admin_panel.html",
        {
            "title": request.user.get_full_name,
            "pending_accounts": User.objects.filter(
                role=User.ROLE_CASHIER,
                is_approved=False,
                is_active=True,
                is_superuser=False,
            ).order_by("date_joined"),
            "cashier_count": User.objects.filter(
                role=User.ROLE_CASHIER,
                is_approved=True,
                is_active=True,
            ).count(),
            "admin_count": User.objects.filter(is_superuser=True, is_active=True).count(),
            "cashier_form": AdminCashierCreateForm(),
        },
    )


@login_required
@admin_required
def create_cashier_account(request):
    if request.method != "POST":
        return redirect("admin_panel")
    form = AdminCashierCreateForm(request.POST)
    if form.is_valid():
        user = form.save()
        messages.success(request, f"Đã cấp tài khoản Thu ngân: {user.username}.")
    else:
        messages.error(request, "Không thể tạo tài khoản. Hãy kiểm tra lại tên đăng nhập và mật khẩu.")
    return redirect("admin_panel")


@login_required
def profile_update(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect("profile")
        else:
            messages.error(request, "Please correct the error(s) below.")
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(
        request,
        "setting/profile_info_change.html",
        {
            "title": "Setting",
            "form": form,
        },
    )


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated!")
            return redirect("profile")
        else:
            messages.error(request, "Please correct the error(s) below. ")
    else:
        form = PasswordChangeForm(request.user)
    return render(
        request,
        "setting/password_change.html",
        {
            "form": form,
        },
    )

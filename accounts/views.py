import json
import tarfile
import tempfile
from datetime import datetime, timezone as datetime_timezone
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.http import FileResponse, Http404
from django.http.response import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
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
    backup_root = Path(settings.BACKUP_ROOT)
    backup_paths = sorted(
        backup_root.glob("lms-backup-*.tar.gz"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if backup_root.exists() else []
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
            "backups": [_backup_info(path) for path in backup_paths],
        },
    )


@login_required
@admin_required
def backup_center(request):
    backup_root = Path(settings.BACKUP_ROOT)
    backup_paths = sorted(
        backup_root.glob("lms-backup-*.tar.gz"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if backup_root.exists() else []
    backups = [_backup_info(path) for path in backup_paths]
    return render(request, "setting/backup_center.html", {"backups": backups})


def _backup_info(backup_path):
    """Return display metadata, preferring the timestamp stored in the archive."""
    created_at = timezone.localtime(
        datetime.fromtimestamp(backup_path.stat().st_mtime, tz=datetime_timezone.utc)
    )
    try:
        with tarfile.open(backup_path, "r:gz") as archive:
            manifest = json.load(archive.extractfile("manifest.json"))
        parsed_created_at = parse_datetime(manifest.get("created_at", ""))
        if parsed_created_at and timezone.is_aware(parsed_created_at):
            created_at = timezone.localtime(parsed_created_at)
    except (OSError, KeyError, tarfile.TarError, json.JSONDecodeError):
        pass
    return {"name": backup_path.name, "created_at": created_at, "size": backup_path.stat().st_size}


@login_required
@admin_required
def backup_download(request):
    backup_root = Path(settings.BACKUP_ROOT).resolve()
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(datetime_timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_root / f"lms-backup-{timestamp}.tar.gz"
    try:
        call_command("backup_data", output=str(backup_path), verbosity=0)
    except (CommandError, DatabaseError, OSError) as exc:
        messages.error(request, f"Không thể tạo bản sao lưu: {exc}")
        return redirect("backup_center")
    return FileResponse(
        backup_path.open("rb"),
        as_attachment=True,
        filename=backup_path.name,
    )


@login_required
@admin_required
def backup_file_download(request, filename):
    backup_root = Path(settings.BACKUP_ROOT).resolve()
    backup_path = (backup_root / filename).resolve()
    if backup_path.parent != backup_root or not backup_path.is_file() or backup_path.suffixes != [".tar", ".gz"]:
        raise Http404
    return FileResponse(backup_path.open("rb"), as_attachment=True, filename=backup_path.name)


@login_required
@admin_required
def backup_restore(request):
    if request.method != "POST":
        return redirect("backup_center")
    upload = request.FILES.get("backup_file")
    if not upload or not upload.name.endswith(".tar.gz"):
        messages.error(request, "Vui lòng chọn đúng file backup .tar.gz.")
        return redirect("backup_center")

    with tempfile.NamedTemporaryFile(prefix="uploaded-backup-", suffix=".tar.gz") as temporary_file:
        for chunk in upload.chunks():
            temporary_file.write(chunk)
        temporary_file.flush()
        try:
            arguments = [
                "restore_data",
                temporary_file.name,
                "--yes-i-really-want-to-restore",
            ]
            if request.POST.get("replace") == "on":
                arguments.extend(["--replace", "--replace-media"])
            call_command(*arguments, verbosity=0)
        except (CommandError, DatabaseError, OSError) as exc:
            messages.error(request, f"Không thể khôi phục backup: {exc}")
            return redirect("backup_center")

    messages.success(request, "Đã khôi phục dữ liệu từ file backup.")
    return redirect("backup_center")


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

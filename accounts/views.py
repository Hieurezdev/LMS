import json
import tarfile
import tempfile
import unicodedata
from datetime import datetime, timezone as datetime_timezone
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.db.models import Prefetch
from django.db import transaction
from django.http import FileResponse, Http404
from django.http.response import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.http import require_POST
from .decorators import admin_required
from .forms import (
    AdminCashierCreateForm,
    ApprovalAuthenticationForm,
    ProfileUpdateForm,
    PublicPaymentRequestForm,
)
from .models import User
from lms_manager.models import Enrollment, Payment, PaymentPeriod, PaymentRequest, Student


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


def public_payment_request(request):
    """Accept a payment request without exposing the authenticated LMS area."""
    if request.method == "POST":
        form = PublicPaymentRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, "accounts/payment_request_success.html")
    else:
        form = PublicPaymentRequestForm(initial={"payment_method": "cash"})
    return render(request, "accounts/payment_request.html", {"form": form})


def _normalized_search_text(value):
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char)).replace("đ", "d")


@require_POST
def public_payment_student_search(request):
    query = " ".join(request.POST.get("query", "").split())[:80]
    if len(query) < 3:
        return JsonResponse({"students": []})

    now = timezone.now().timestamp()
    window_start, request_count = request.session.get("payment_search_window", (now, 0))
    if now - window_start >= 60:
        window_start, request_count = now, 0
    if request_count >= 60:
        return JsonResponse({"error": "Bạn tìm kiếm quá nhanh. Vui lòng thử lại sau một phút."}, status=429)
    request.session["payment_search_window"] = (window_start, request_count + 1)

    candidates = list(
        Student.objects.filter(classroom__isnull=False, name__icontains=query)
        .select_related("classroom")
        .order_by("name", "pk")[:8]
    )
    if len(candidates) < 8:
        seen_ids = {student.pk for student in candidates}
        normalized_query = _normalized_search_text(query)
        for student in Student.objects.filter(classroom__isnull=False).select_related("classroom").order_by("name", "pk").iterator():
            if student.pk not in seen_ids and normalized_query in _normalized_search_text(student.name):
                candidates.append(student)
                seen_ids.add(student.pk)
                if len(candidates) == 8:
                    break

    student_ids = [student.pk for student in candidates]
    students_by_id = {
        student.pk: student
        for student in Student.objects.filter(pk__in=student_ids).select_related("classroom").prefetch_related(
            Prefetch("enrollments", queryset=Enrollment.objects.select_related("teacher", "subject")),
            Prefetch("payments", queryset=Payment.objects.select_related("payment_period")),
        )
    }
    results = []
    for student_id in student_ids:
        student = students_by_id[student_id]
        paid = {(payment.teacher_id, payment.payment_period.name) for payment in student.payments.all()}
        enrollments = [
            {
                "id": enrollment.pk,
                "teacher": enrollment.teacher.name,
                "subject": enrollment.subject.name,
                "unpaid_periods": [
                    number for number in range(1, 9)
                    if (enrollment.teacher_id, f"Đợt {number}") not in paid
                ],
            }
            for enrollment in student.enrollments.all()
        ]
        if enrollments:
            results.append({
                "id": student.pk,
                "name": student.name,
                "classroom": student.classroom.name,
                "enrollments": enrollments,
            })
    return JsonResponse({"students": results})


@login_required
@admin_required
def payment_request_queue(request):
    requests = PaymentRequest.objects.select_related("reviewed_by", "payment").all()
    return render(request, "setting/payment_request_queue.html", {
        "payment_requests": requests,
        "breadcrumb_items": [
            {"label": "Giao dịch đóng tiền", "url": reverse("payment_list")},
            {"label": "Hàng chờ giao dịch"},
        ],
    })


@login_required
@admin_required
@require_POST
@transaction.atomic
def approve_payment_request(request, pk):
    payment_request = get_object_or_404(
        PaymentRequest.objects.select_for_update(),
        pk=pk,
        status=PaymentRequest.STATUS_PENDING,
    )
    if payment_request.enrollment_id:
        enrollment = Enrollment.objects.select_related("student__classroom", "subject", "teacher").filter(
            pk=payment_request.enrollment_id
        ).first()
        if enrollment is None or enrollment.student.classroom is None:
            messages.error(request, "Không thể xác nhận: đăng ký học không còn hợp lệ.")
            return redirect("payment_request_queue")
        student = enrollment.student
    else:
        students = Student.objects.filter(
            name__iexact=payment_request.student_name.strip(),
            classroom__name__iexact=payment_request.classroom_name.strip(),
        )
        if students.count() != 1:
            messages.error(request, "Không thể xác nhận: tên học sinh và lớp không xác định duy nhất.")
            return redirect("payment_request_queue")
        student = students.first()
        enrollments = Enrollment.objects.filter(
            student=student,
            subject__name__iexact=payment_request.subject_name.strip(),
            teacher__name__iexact=payment_request.teacher_name.strip(),
        ).select_related("subject", "teacher")
        if enrollments.count() != 1:
            messages.error(request, "Không thể xác nhận: thông tin môn học hoặc giảng viên không khớp.")
            return redirect("payment_request_queue")
        enrollment = enrollments.first()
    period, _ = PaymentPeriod.objects.get_or_create(
        name=payment_request.payment_period_name.strip(),
        teacher=enrollment.teacher,
        subject=enrollment.subject,
    )
    if Payment.objects.filter(
        student=student, teacher=enrollment.teacher, payment_period=period
    ).exists():
        messages.error(request, "Học sinh này đã có giao dịch cho đợt thu đã chọn.")
        return redirect("payment_request_queue")

    payment = Payment.objects.create(
        student=student,
        classroom=student.classroom,
        subject=enrollment.subject,
        teacher=enrollment.teacher,
        payment_period=period,
        amount=payment_request.amount,
        payment_method=payment_request.payment_method,
    )
    payment_request.payment = payment
    payment_request.status = PaymentRequest.STATUS_APPROVED
    payment_request.reviewed_by = request.user
    payment_request.reviewed_at = timezone.now()
    payment_request.save(update_fields=["payment", "status", "reviewed_by", "reviewed_at"])

    messages.success(request, "Đã xác nhận yêu cầu và tạo giao dịch học phí.")
    return redirect("payment_request_queue")


@login_required
@admin_required
@require_POST
def reject_payment_request(request, pk):
    payment_request = get_object_or_404(
        PaymentRequest, pk=pk, status=PaymentRequest.STATUS_PENDING
    )
    payment_request.status = PaymentRequest.STATUS_REJECTED
    payment_request.reviewed_by = request.user
    payment_request.reviewed_at = timezone.now()
    payment_request.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    messages.success(request, "Đã từ chối yêu cầu thu học phí.")
    return redirect("payment_request_queue")


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
    backup_paths = _list_backup_paths()
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
            "pending_payment_requests": PaymentRequest.objects.filter(
                status=PaymentRequest.STATUS_PENDING
            ).count(),
            "cashier_form": AdminCashierCreateForm(),
            "backups": [_backup_info(path) for path in backup_paths],
        },
    )


@login_required
@admin_required
def backup_center(request):
    backup_paths = _list_backup_paths()
    backups = [_backup_info(path) for path in backup_paths]
    return render(request, "setting/backup_center.html", {"backups": backups})


def _list_backup_paths():
    backup_root = Path(settings.BACKUP_ROOT)
    if not backup_root.exists():
        return []
    return sorted(
        [
            *backup_root.glob("lms-backup-*.tar.gz"),
            *backup_root.glob("lms-deleted-*.tar.gz"),
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


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
@require_POST
def backup_restore_previous(request, filename):
    """Restore the most recent pre-delete snapshot as a one-click undo."""
    backup_root = Path(settings.BACKUP_ROOT).resolve()
    backup_path = (backup_root / filename).resolve()
    if (
        backup_path.parent != backup_root
        or not backup_path.is_file()
        or not filename.startswith("lms-deleted-")
        or backup_path.suffixes != [".tar", ".gz"]
    ):
        raise Http404

    try:
        call_command(
            "restore_data",
            str(backup_path),
            "--yes-i-really-want-to-restore",
            "--replace",
            "--replace-media",
            verbosity=0,
        )
    except (CommandError, DatabaseError, OSError) as exc:
        messages.error(request, f"Không thể khôi phục thao tác vừa xóa: {exc}")
        return redirect("admin_panel")

    request.session.pop("last_delete_backup", None)
    messages.success(request, "Đã khôi phục dữ liệu về trước thao tác xóa gần nhất.")
    return redirect("admin_panel")


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

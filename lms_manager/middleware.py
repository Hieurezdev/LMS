from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.urls import Resolver404, resolve


class LMSAccessMiddleware:
    """Require authentication and limit cashier accounts to collection work."""

    CASHIER_ALLOWED_VIEWS = {
        "cashier_due_list",
        "payment_add", "payment_receipt", "payment_batch_receipt",
        "api_student_subjects", "api_student_teachers", "api_student_unpaid_periods",
        "api_student_payment_periods", "api_get_receipt_url", "api_payment_periods_filter",
        "api_payment_period_details", "api_subject_teachers", "api_teacher_classrooms",
        "api_teacher_subjects",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return self.get_response(request)

        if not match.func.__module__.startswith("lms_manager."):
            return self.get_response(request)
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if getattr(request.user, "is_admin", False):
            return self.get_response(request)
        if getattr(request.user, "is_cashier", False) and match.url_name in self.CASHIER_ALLOWED_VIEWS:
            return self.get_response(request)

        return HttpResponseForbidden("Bạn không có quyền truy cập chức năng này.")

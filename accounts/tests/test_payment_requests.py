from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import translation

from lms_manager.models import Payment, PaymentRequest


class PaymentRequestRemovalTests(TestCase):
    def test_removed_request_routes_leave_existing_data_untouched(self):
        payment_request = PaymentRequest.objects.create(
            student_name="Nguyễn Văn A",
            classroom_name="10A1",
            subject_name="Toán",
            teacher_name="Cô Lan",
            payment_period_name="Đợt 1",
            amount=125000,
            payer_phone="0900000000",
        )
        admin = get_user_model().objects.create_superuser(
            username="payment-admin", password="test-password"
        )
        self.client.force_login(admin)

        with translation.override("en"):
            for url in (
                "/en/accounts/payment-request/",
                "/en/accounts/payment-request/students/search/",
                "/en/accounts/admin_panel/payment-requests/",
                f"/en/accounts/admin_panel/payment-requests/{payment_request.pk}/approve/",
                f"/en/accounts/admin_panel/payment-requests/{payment_request.pk}/reject/",
            ):
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 404)
                    self.assertEqual(self.client.post(url).status_code, 404)

        payment_request.refresh_from_db()
        self.assertEqual(payment_request.status, PaymentRequest.STATUS_PENDING)
        self.assertEqual(Payment.objects.count(), 0)

    def test_admin_panel_does_not_link_to_removed_queue(self):
        admin = get_user_model().objects.create_superuser(
            username="payment-admin", password="test-password"
        )
        self.client.force_login(admin)

        with translation.override("en"):
            response = self.client.get("/en/accounts/admin_panel/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "/en/accounts/admin_panel/payment-requests/")

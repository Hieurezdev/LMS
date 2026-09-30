from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from lms_manager.models import (
    ClassRoom,
    Enrollment,
    Payment,
    PaymentRequest,
    Student,
    Subject,
    Teacher,
)


class PaymentRequestFlowTests(TestCase):
    def setUp(self):
        self.media_root = TemporaryDirectory()
        self.addCleanup(self.media_root.cleanup)
        self.media_settings = override_settings(MEDIA_ROOT=self.media_root.name)
        self.media_settings.enable()
        self.addCleanup(self.media_settings.disable)

        self.admin = get_user_model().objects.create_superuser(
            username="payment-admin", password="test-password"
        )
        classroom = ClassRoom.objects.create(name="10A1")
        subject = Subject.objects.create(name="Toán")
        teacher = Teacher.objects.create(name="Cô Lan")
        teacher.subjects.add(subject)
        teacher.classes.add(classroom)
        student = Student.objects.create(name="Nguyễn Văn A", classroom=classroom)
        Enrollment.objects.create(student=student, teacher=teacher, subject=subject)
        self.student = student

    def test_public_submission_waits_for_admin_approval(self):
        with translation.override("en"):
            public_url = reverse("public_payment_request")
            queue_url = reverse("payment_request_queue")

            self.assertEqual(self.client.get(public_url).status_code, 200)
            response = self.client.post(public_url, {
                "student_name": "Nguyễn Văn A",
                "classroom_name": "10A1",
                "subject_name": "Toán",
                "teacher_name": "Cô Lan",
                "payment_period_name": "Đợt 1",
                "amount": "125000",
                "payment_method": "bank_transfer",
                "payer_phone": "0900000000",
                "transaction_reference": "TEST-123",
            })
            self.assertEqual(response.status_code, 200)
            payment_request = PaymentRequest.objects.get()
            self.assertEqual(payment_request.status, PaymentRequest.STATUS_PENDING)
            self.assertEqual(Payment.objects.count(), 0)

            self.assertEqual(self.client.get(queue_url).status_code, 302)
            self.client.force_login(self.admin)
            queue_response = self.client.get(queue_url)
            self.assertEqual(queue_response.status_code, 200)
            self.assertContains(queue_response, "Hàng chờ giao dịch")
            self.assertContains(queue_response, "Nguyễn Văn A")

            approve_url = reverse("approve_payment_request", args=[payment_request.pk])
            self.assertEqual(self.client.post(approve_url).status_code, 302)
            payment_request.refresh_from_db()
            self.assertEqual(payment_request.status, PaymentRequest.STATUS_APPROVED)
            self.assertEqual(Payment.objects.count(), 1)
            self.assertEqual(payment_request.payment.student, self.student)
            self.assertTrue(payment_request.payment.receipt_pdf)

    def test_rejected_request_creates_no_payment(self):
        payment_request = PaymentRequest.objects.create(
            student_name="Nguyễn Văn A",
            classroom_name="10A1",
            subject_name="Toán",
            teacher_name="Cô Lan",
            payment_period_name="Đợt 1",
            amount=125000,
            payer_phone="0900000000",
        )
        self.client.force_login(self.admin)
        with translation.override("en"):
            response = self.client.post(
                reverse("reject_payment_request", args=[payment_request.pk])
            )
        self.assertEqual(response.status_code, 302)
        payment_request.refresh_from_db()
        self.assertEqual(payment_request.status, PaymentRequest.STATUS_REJECTED)
        self.assertEqual(Payment.objects.count(), 0)

import uuid
from io import BytesIO
from tempfile import TemporaryDirectory

from pypdf import PdfReader
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone, translation

from lms_manager.models import (
    ClassRoom,
    Enrollment,
    Payment,
    PaymentBatch,
    PaymentPeriod,
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
        self.enrollment = Enrollment.objects.create(student=student, teacher=teacher, subject=subject)
        self.student = student

    def test_public_submission_and_student_search_are_unavailable(self):
        with translation.override("en"):
            for url in (
                "/en/accounts/payment-request/",
                "/en/accounts/payment-request/students/search/",
            ):
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {"query": "Nguyen"}).status_code, 404)
        self.assertEqual(PaymentRequest.objects.count(), 0)

    def test_existing_request_can_still_be_approved(self):
        payment_request = PaymentRequest.objects.create(
            enrollment=self.enrollment,
            student_name=self.student.name,
            classroom_name=self.student.classroom.name,
            subject_name=self.enrollment.subject.name,
            teacher_name=self.enrollment.teacher.name,
            payment_period_name="Đợt 1",
            amount=125000,
            payment_method="bank_transfer",
            payer_phone="0900000000",
            transaction_reference="TEST-123",
        )
        with translation.override("en"):
            queue_url = reverse("payment_request_queue")
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
            batch = PaymentBatch.objects.get()
            self.assertEqual(batch.payments.count(), 1)
            self.assertEqual(payment_request.payment.student, self.student)
            self.assertTrue(payment_request.payment.receipt_pdf)
            self.assertEqual(payment_request.payment.collected_at, payment_request.reviewed_at)
            self.assertEqual(batch.created_at, payment_request.payment.collected_at)
            self.assertEqual(payment_request.payment.payment_date, timezone.localdate(batch.created_at))
            queue_response = self.client.get(queue_url)
            collected_time = timezone.localtime(batch.created_at).strftime('%d/%m/%Y %H:%M')
            self.assertContains(queue_response, f'Thu: {collected_time}')
            for receipt_url in (
                reverse("payment_receipt", args=[payment_request.payment_id]),
                reverse("payment_batch_receipt", args=[batch.pk]),
            ):
                receipt_response = self.client.get(receipt_url)
                self.assertEqual(receipt_response.status_code, 200)
                receipt_text = PdfReader(BytesIO(receipt_response.content)).pages[0].extract_text()
                self.assertIn(collected_time[-5:], receipt_text)

    def test_queue_search_filters_requests(self):
        PaymentRequest.objects.create(
            student_name="Nguyễn Văn A", classroom_name="10A1",
            subject_name="Toán", teacher_name="Cô Lan",
            payment_period_name="Đợt 1", amount=125000,
            payer_phone="0900000000",
        )
        PaymentRequest.objects.create(
            student_name="Trần Thị B", classroom_name="11B2",
            subject_name="Lý", teacher_name="Thầy Minh",
            payment_period_name="Đợt 2", amount=150000,
            payer_phone="0911111111",
        )
        self.client.force_login(self.admin)
        with translation.override("en"):
            url = reverse("payment_request_queue")
            response = self.client.get(url, {"q": "10A1"})
            phone_response = self.client.get(url, {"q": "0911111111"})
            empty_response = self.client.get(url, {"q": "không có"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nguyễn Văn A")
        self.assertNotContains(response, "Trần Thị B")
        self.assertEqual(response.context["payment_request_query"], "10A1")
        self.assertContains(phone_response, "Trần Thị B")
        self.assertNotContains(phone_response, "Nguyễn Văn A")
        self.assertContains(empty_response, "Không tìm thấy yêu cầu phù hợp")

    def test_existing_grouped_requests_can_still_be_approved_together(self):
        second_subject = Subject.objects.create(name="Lý")
        second_teacher = Teacher.objects.create(name="Thầy Minh")
        second_teacher.subjects.add(second_subject)
        second_teacher.classes.add(self.student.classroom)
        second_enrollment = Enrollment.objects.create(
            student=self.student,
            teacher=second_teacher,
            subject=second_subject,
        )
        request_group = uuid.uuid4()
        for enrollment, amount in (
            (self.enrollment, 125000),
            (second_enrollment, 150000),
        ):
            PaymentRequest.objects.create(
                request_group=request_group,
                enrollment=enrollment,
                student_name=self.student.name,
                classroom_name=self.student.classroom.name,
                subject_name=enrollment.subject.name,
                teacher_name=enrollment.teacher.name,
                payment_period_name="Đợt 1",
                amount=amount,
                payment_method="cash",
            )
        self.assertEqual(PaymentRequest.objects.count(), 2)
        self.assertEqual(
            set(PaymentRequest.objects.values_list("teacher_name", flat=True)),
            {"Cô Lan", "Thầy Minh"},
        )
        self.assertEqual(Payment.objects.count(), 0)
        self.client.force_login(self.admin)
        first_request = PaymentRequest.objects.order_by("pk").first()
        with translation.override("en"):
            approve_response = self.client.post(
                reverse("approve_payment_request", args=[first_request.pk])
            )
        self.assertEqual(approve_response.status_code, 302)
        self.assertEqual(Payment.objects.count(), 2)
        self.assertEqual(PaymentBatch.objects.count(), 1)
        batch = PaymentBatch.objects.get()
        with translation.override("en"):
            self.assertEqual(
                approve_response.url,
                reverse("payment_batch_receipt", args=[batch.pk]),
            )
        self.assertEqual(
            PaymentRequest.objects.filter(status=PaymentRequest.STATUS_APPROVED).count(),
            2,
        )
        self.assertEqual(set(Payment.objects.values_list("collected_at", flat=True)), {batch.created_at})

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

import json
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

    def test_search_finds_student_and_only_unpaid_periods(self):
        with translation.override("en"):
            search_url = reverse("public_payment_student_search")
            self.assertEqual(self.client.post(search_url, {"query": ""}).json()["students"], [])
            response = self.client.post(search_url, {"query": "Nguyen"})
        self.assertEqual(response.status_code, 200)
        student = response.json()["students"][0]
        self.assertEqual(student["name"], "Nguyễn Văn A")
        self.assertEqual(student["classroom"], "10A1")
        self.assertEqual(student["enrollments"][0]["id"], self.enrollment.pk)
        self.assertIn(1, student["enrollments"][0]["unpaid_periods"])

        period = PaymentPeriod.objects.create(
            name="Đợt 1", teacher=self.enrollment.teacher, subject=self.enrollment.subject
        )
        Payment.objects.bulk_create([Payment(
            student=self.student,
            classroom=self.student.classroom,
            subject=self.enrollment.subject,
            teacher=self.enrollment.teacher,
            payment_period=period,
            amount=125000,
        )])
        with translation.override("en"):
            response = self.client.post(search_url, {"query": "Nguyen"})
        self.assertNotIn(1, response.json()["students"][0]["enrollments"][0]["unpaid_periods"])

    def test_public_submission_waits_for_admin_approval(self):
        with translation.override("en"):
            public_url = reverse("public_payment_request")
            queue_url = reverse("payment_request_queue")

            page = self.client.get(public_url)
            self.assertEqual(page.status_code, 200)
            payment_method = page.context["form"]["payment_method"]
            self.assertEqual(payment_method.value(), "cash")
            self.assertEqual(next(iter(payment_method.field.choices))[0], "cash")
            response = self.client.post(public_url, {
                "student_id": self.student.pk,
                "enrollment": self.enrollment.pk,
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
            self.assertEqual(payment_request.enrollment_id, self.enrollment.pk)
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

    def test_submission_rejects_an_unselected_student(self):
        with translation.override("en"):
            response = self.client.post(reverse("public_payment_request"), {
                "student_name": "Nguyễn Văn A",
                "classroom_name": "10A1",
                "subject_name": "Toán",
                "teacher_name": "Cô Lan",
                "payment_period_name": "Đợt 1",
                "amount": "125000",
                "payment_method": "cash",
                "payer_phone": "0900000000",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PaymentRequest.objects.count(), 0)

    def test_submission_creates_one_pending_request_per_selected_period(self):
        with translation.override("en"):
            response = self.client.post(reverse("public_payment_request"), {
                "student_id": self.student.pk,
                "enrollment": self.enrollment.pk,
                "student_name": "Nguyễn Văn A",
                "classroom_name": "10A1",
                "subject_name": "Toán",
                "teacher_name": "Cô Lan",
                "payment_period_name": ["Đợt 1", "Đợt 2"],
                "amount": "125000",
                "payment_method": "cash",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(PaymentRequest.objects.values_list("payment_period_name", flat=True)),
            {"Đợt 1", "Đợt 2"},
        )
        self.assertEqual(Payment.objects.count(), 0)

    def test_submission_accepts_multiple_students_and_teachers_in_one_batch(self):
        second_subject = Subject.objects.create(name="Lý")
        second_teacher = Teacher.objects.create(name="Thầy Minh")
        second_teacher.subjects.add(second_subject)
        second_teacher.classes.add(self.student.classroom)
        second_enrollment = Enrollment.objects.create(
            student=self.student,
            teacher=second_teacher,
            subject=second_subject,
        )
        items = [
            {
                "student_id": self.student.pk,
                "enrollment": self.enrollment.pk,
                "student_name": "Nguyễn Văn A",
                "classroom_name": "10A1",
                "subject_name": "Toán",
                "teacher_name": "Cô Lan",
                "payment_period_name": ["Đợt 1"],
                "amount": "125000",
                "payment_method": "cash",
            },
            {
                "student_id": self.student.pk,
                "enrollment": second_enrollment.pk,
                "student_name": "Nguyễn Văn A",
                "classroom_name": "10A1",
                "subject_name": "Lý",
                "teacher_name": "Thầy Minh",
                "payment_period_name": ["Đợt 1"],
                "amount": "150000",
                "payment_method": "cash",
            },
        ]

        with translation.override("en"):
            response = self.client.post(
                reverse("public_payment_request"),
                {"batch_items": json.dumps(items)},
            )

        self.assertEqual(response.status_code, 200)
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

    def test_invalid_batch_shows_error_without_creating_request(self):
        with translation.override("en"):
            url = reverse("public_payment_request")
            invalid_json = self.client.post(url, {"batch_items": "not json"})
            invalid_row = self.client.post(url, {"batch_items": json.dumps([{
                "student_name": self.student.name,
                "payment_period_name": ["Đợt 1"],
                "amount": "125000",
                "payment_method": "cash",
            }])})

        self.assertContains(invalid_json, "Danh sách khoản thu không hợp lệ.")
        self.assertContains(invalid_row, "Khoản thu dòng 1:")
        self.assertEqual(PaymentRequest.objects.count(), 0)

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

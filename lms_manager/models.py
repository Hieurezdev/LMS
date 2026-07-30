from django.db import models
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.conf import settings
from io import BytesIO
from xhtml2pdf import pisa
import os

def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those
    resources from local disk.
    """
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATICFILES_DIRS[0], uri.replace(settings.STATIC_URL, ""))
    elif uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    else:
        return uri

    if not os.path.isfile(path):
        return uri
    return path


class ClassRoom(models.Model):
    name = models.CharField(max_length=150, verbose_name="Tên lớp")

    class Meta:
        verbose_name = "Lớp học"
        verbose_name_plural = "Lớp học"

    def __str__(self):
        teachers = self.teachers.all()
        if teachers.exists():
            teacher_names = ", ".join(t.name for t in teachers)
            return f"{self.name} (GV: {teacher_names})"
        return self.name

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_name = None
        if not is_new:
            try:
                old_self = self.__class__.objects.get(pk=self.pk)
                old_name = old_self.name
            except self.__class__.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if not is_new and old_name != self.name:
            for payment in self.payments.all():
                payment.generate_receipt_pdf()


class Subject(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name="Tên môn học")

    class Meta:
        verbose_name = "Môn học"
        verbose_name_plural = "Môn học"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_name = None
        if not is_new:
            try:
                old_self = self.__class__.objects.get(pk=self.pk)
                old_name = old_self.name
            except self.__class__.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if not is_new and old_name != self.name:
            for payment in self.payments.all():
                payment.generate_receipt_pdf()


class Teacher(models.Model):
    name = models.CharField(max_length=150, verbose_name="Tên giảng viên")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Số điện thoại")
    subjects = models.ManyToManyField(Subject, related_name="teachers", verbose_name="Môn giảng dạy")
    classes = models.ManyToManyField(ClassRoom, related_name="teachers", blank=True, verbose_name="Lớp giảng dạy")

    class Meta:
        verbose_name = "Giảng viên"
        verbose_name_plural = "Giảng viên"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_name = None
        if not is_new:
            try:
                old_self = self.__class__.objects.get(pk=self.pk)
                old_name = old_self.name
            except self.__class__.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if not is_new and old_name != self.name:
            for payment in self.payments.all():
                payment.generate_receipt_pdf()


class Student(models.Model):
    STATUS_CHOICES = [
        ('Chưa đóng', 'Chưa đóng'),
        ('Đã đóng', 'Đã đóng'),
    ]
    name = models.CharField(max_length=150, verbose_name="Tên học sinh")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Số điện thoại")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="students", null=True, blank=True, verbose_name="Lớp")
    start_date = models.DateField(blank=True, null=True, verbose_name="Ngày bắt đầu học")
    
    dot_1 = models.CharField(max_length=20, default='Chưa đóng', choices=STATUS_CHOICES, verbose_name="Đợt 1")
    dot_2 = models.CharField(max_length=20, default='Chưa đóng', choices=STATUS_CHOICES, verbose_name="Đợt 2")
    dot_3 = models.CharField(max_length=20, default='Chưa đóng', choices=STATUS_CHOICES, verbose_name="Đợt 3")
    dot_4 = models.CharField(max_length=20, default='Chưa đóng', choices=STATUS_CHOICES, verbose_name="Đợt 4")
    dot_5 = models.CharField(max_length=20, default='Chưa đóng', choices=STATUS_CHOICES, verbose_name="Đợt 5")
    dot_6 = models.CharField(max_length=20, default='Chưa đóng', choices=STATUS_CHOICES, verbose_name="Đợt 6")
    dot_7 = models.CharField(max_length=20, default='Chưa đóng', choices=STATUS_CHOICES, verbose_name="Đợt 7")
    dot_8 = models.CharField(max_length=20, default='Chưa đóng', choices=STATUS_CHOICES, verbose_name="Đợt 8")


    class Meta:
        verbose_name = "Học sinh"
        verbose_name_plural = "Học sinh"

    def __str__(self):
        return f"{self.name} ({self.classroom.name})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_name = None
        if not is_new:
            try:
                old_self = self.__class__.objects.get(pk=self.pk)
                old_name = old_self.name
            except self.__class__.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if not is_new and old_name != self.name:
            for payment in self.payments.all():
                payment.generate_receipt_pdf()


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments", verbose_name="Học sinh")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="enrollments", verbose_name="Môn đăng ký")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="enrollments", verbose_name="Giáo viên hướng dẫn")

    class Meta:
        verbose_name = "Đăng ký học"
        verbose_name_plural = "Đăng ký học"
        unique_together = ('student', 'subject')

    def __str__(self):
        return f"{self.student.name} - {self.subject.name} (GV: {self.teacher.name})"


class PaymentPeriod(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên đợt đóng tiền")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="payment_periods", verbose_name="Giảng viên")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="payment_periods", verbose_name="Môn học")

    class Meta:
        verbose_name = "Đợt đóng tiền"
        verbose_name_plural = "Đợt đóng tiền"
        unique_together = ('name', 'teacher', 'subject')
        ordering = ['subject__name', 'name']

    def __str__(self):
        return f"{self.name} - {self.subject.name} (GV: {self.teacher.name})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_name = None
        if not is_new:
            try:
                old_self = self.__class__.objects.get(pk=self.pk)
                old_name = old_self.name
            except self.__class__.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if not is_new and old_name != self.name:
            for payment in self.payments.all():
                payment.generate_receipt_pdf()


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Tiền mặt'),
        ('bank_transfer', 'Chuyển khoản'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="payments", verbose_name="Học sinh")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="payments", verbose_name="Lớp")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="payments", verbose_name="Môn học")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="payments", verbose_name="Giảng viên")
    payment_period = models.ForeignKey(PaymentPeriod, on_delete=models.CASCADE, related_name="payments", verbose_name="Đợt đóng tiền")
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Số tiền đóng")
    payment_date = models.DateField(default=timezone.now, verbose_name="Ngày đóng")
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',
        verbose_name="Hình thức thanh toán",
    )
    receipt_pdf = models.FileField(upload_to="receipts/", blank=True, null=True, verbose_name="Biên lai PDF")

    class Meta:
        verbose_name = "Thanh toán học phí"
        verbose_name_plural = "Thanh toán học phí"

    def __str__(self):
        return f"{self.student.name} - {self.payment_period.name}: {self.amount:,} VNĐ"

    def generate_receipt_pdf(self):
        context = {
            'payment': self,
            'MEDIA_ROOT': settings.MEDIA_ROOT,
        }
        html_string = render_to_string('lms_manager/receipt_pdf.html', context)
        pdf_io = BytesIO()
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_io, link_callback=link_callback)
        if not pisa_status.err:
            pdf_io.seek(0)
            if self.receipt_pdf:
                self.receipt_pdf.storage.delete(self.receipt_pdf.name)
            filename = f"receipt_{self.id}_a5_v2.pdf"
            self.receipt_pdf.save(filename, ContentFile(pdf_io.read()), save=False)
            Payment.objects.filter(pk=self.pk).update(receipt_pdf=self.receipt_pdf)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.generate_receipt_pdf()


class PaymentBatch(models.Model):
    """A single collection session that may contain several payment records."""
    payments = models.ManyToManyField(Payment, related_name='batches')
    payment_date = models.DateField(default=timezone.now, verbose_name="Ngày thu")
    created_at = models.DateTimeField(auto_now_add=True)
    receipt_pdf = models.FileField(upload_to="receipts/batches/", blank=True, null=True,
                                   verbose_name="Biên lai tổng hợp PDF")

    class Meta:
        verbose_name = "Phiếu thu tổng hợp"
        verbose_name_plural = "Phiếu thu tổng hợp"
        ordering = ['-created_at']

    def __str__(self):
        return f"Phiếu thu tổng hợp #{self.pk}"

    def generate_receipt_pdf(self):
        payments = list(self.payments.select_related(
            'student', 'classroom', 'subject', 'teacher', 'payment_period'
        ).order_by('student__name', 'id'))
        context = {
            'batch': self,
            'payments': payments,
            'total_amount': sum(payment.amount for payment in payments),
            'payment_method_display': payments[0].get_payment_method_display() if payments else 'Tiền mặt',
        }
        html_string = render_to_string('lms_manager/batch_receipt_pdf.html', context)
        pdf_io = BytesIO()
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_io, link_callback=link_callback)
        if not pisa_status.err:
            pdf_io.seek(0)
            if self.receipt_pdf:
                self.receipt_pdf.storage.delete(self.receipt_pdf.name)
            filename = f"batch_receipt_{self.id}_a5_v2.pdf"
            self.receipt_pdf.save(filename, ContentFile(pdf_io.read()), save=False)
            PaymentBatch.objects.filter(pk=self.pk).update(receipt_pdf=self.receipt_pdf)


class TeacherSettlement(models.Model):
    """A confirmed payout for one teacher in one classroom."""
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name='settlements',
        verbose_name="Giảng viên",
    )
    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.PROTECT,
        related_name='teacher_settlements',
        verbose_name="Lớp",
    )
    payments = models.ManyToManyField(
        Payment,
        related_name='teacher_settlements',
        verbose_name="Các khoản học phí",
    )
    revenue = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Doanh thu")
    teacher_share_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default='0.8000',
        verbose_name="Tỷ lệ giảng viên nhận",
    )
    teacher_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="Số tiền quyết toán cho giảng viên",
    )
    settled_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời điểm quyết toán")

    class Meta:
        verbose_name = "Quyết toán giảng viên"
        verbose_name_plural = "Quyết toán giảng viên"
        ordering = ['-settled_at']

    def __str__(self):
        return f"Quyết toán #{self.pk} - {self.teacher.name} - {self.classroom.name}"

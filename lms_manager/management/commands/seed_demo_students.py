import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from lms_manager.models import (
    ClassRoom,
    Enrollment,
    Payment,
    PaymentPeriod,
    Student,
    Subject,
    Teacher,
)


class Command(BaseCommand):
    help = 'Thêm học sinh dữ liệu mẫu mà không xóa dữ liệu hiện có.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--students', type=int, default=100,
            help='Số học sinh mẫu cần thêm (mặc định: 100).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        student_total = options['students']
        if student_total < 1:
            self.stderr.write(self.style.ERROR('Số học sinh phải lớn hơn 0.'))
            return

        randomizer = random.Random(20260731)
        class_names = ['[Mẫu] 10A1', '[Mẫu] 10A2', '[Mẫu] 11B1', '[Mẫu] 12A1']
        teacher_names = ['[Mẫu] Nguyễn Văn An', '[Mẫu] Trần Thị Bình', '[Mẫu] Lê Hoàng Cường', '[Mẫu] Phạm Thu Dung']
        phones = ['0912000001', '0912000002', '0912000003', '0912000004']
        classes = [ClassRoom.objects.get_or_create(name=name)[0] for name in class_names]
        subject, _ = Subject.objects.get_or_create(name='[Mẫu] Toán học')
        teachers = []
        for name, phone, classroom in zip(teacher_names, phones, classes):
            teacher, _ = Teacher.objects.get_or_create(name=name, defaults={'phone': phone})
            teacher.subjects.add(subject)
            teacher.classes.add(classroom)
            teachers.append(teacher)

        periods_by_teacher = {}
        for teacher in teachers:
            periods_by_teacher[teacher.id] = [
                PaymentPeriod.objects.get_or_create(
                    name=f'Đợt {number}', teacher=teacher, subject=subject
                )[0]
                for number in range(1, 9)
            ]

        surnames = ['Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Huỳnh', 'Phan', 'Vũ', 'Đặng', 'Bùi']
        middle_names = ['Minh', 'Thảo', 'Quang', 'Ngọc', 'Gia', 'Khánh', 'Bảo', 'Thu', 'Anh', 'Hồng']
        given_names = ['An', 'Bình', 'Châu', 'Dũng', 'Giang', 'Hà', 'Huy', 'Khang', 'Linh', 'Minh']
        today = timezone.localdate()
        payments = []
        created_students = 0

        for number in range(1, student_total + 1):
            classroom_index = (number - 1) % len(classes)
            classroom = classes[classroom_index]
            teacher = teachers[classroom_index]
            name = (
                f'{surnames[(number - 1) % len(surnames)]} '
                f'{middle_names[((number - 1) // len(surnames)) % len(middle_names)]} '
                f'{given_names[((number - 1) // (len(surnames) * len(middle_names))) % len(given_names)]} '
                f'Mẫu {number:03d}'
            )
            student = Student.objects.create(
                name=name,
                classroom=classroom,
                start_date=today - timedelta(days=randomizer.randint(30, 250)),
            )
            Enrollment.objects.create(student=student, subject=subject, teacher=teacher)
            created_students += 1

            # Đợt đầu có tỉ lệ đóng cao hơn, các đợt sau tạo cả học sinh còn nợ.
            for period_number, period in enumerate(periods_by_teacher[teacher.id], start=1):
                payment_rate = max(0.18, 0.88 - period_number * 0.09)
                if randomizer.random() <= payment_rate:
                    payments.append(Payment(
                        student=student,
                        classroom=classroom,
                        subject=subject,
                        teacher=teacher,
                        payment_period=period,
                        amount=Decimal(randomizer.choice([75000, 125000, 250000, 300000])),
                        payment_date=today - timedelta(days=(8 - period_number) * 28 + randomizer.randint(0, 20)),
                        payment_method=randomizer.choice(['cash', 'bank_transfer']),
                    ))

        Payment.objects.bulk_create(payments)
        self.stdout.write(self.style.SUCCESS(
            f'Đã thêm {created_students} học sinh mẫu, {len(payments)} khoản thu; dữ liệu hiện có được giữ nguyên.'
        ))

from django.core.management.base import BaseCommand
from django.utils import timezone
from lms_manager.models import ClassRoom, Subject, Teacher, Student, Enrollment, Payment, PaymentPeriod
import random

class Command(BaseCommand):
    help = 'Populates the database with comprehensive sample data for lms_manager'

    def handle(self, *args, **kwargs):
        # 1. Clear old data
        self.stdout.write("Cleaning old lms_manager data...")
        Payment.objects.all().delete()
        Enrollment.objects.all().delete()
        Student.objects.all().delete()
        Teacher.objects.all().delete()
        Subject.objects.all().delete()
        ClassRoom.objects.all().delete()
        PaymentPeriod.objects.all().delete()

        self.stdout.write("Generating new comprehensive sample data...")

        # 2. Classes
        c1 = ClassRoom.objects.create(name="10A1")
        c2 = ClassRoom.objects.create(name="10A2")
        c3 = ClassRoom.objects.create(name="11B1")
        c4 = ClassRoom.objects.create(name="11B2")
        c5 = ClassRoom.objects.create(name="12C1")
        c6 = ClassRoom.objects.create(name="12C2")
        c7 = ClassRoom.objects.create(name="12C3")

        # 3. Subjects
        s1 = Subject.objects.create(name="Toán học")
        s2 = Subject.objects.create(name="Ngữ văn")
        s3 = Subject.objects.create(name="Tiếng Anh")
        s4 = Subject.objects.create(name="Vật lí")
        s5 = Subject.objects.create(name="Hóa học")
        s6 = Subject.objects.create(name="Sinh học")
        s7 = Subject.objects.create(name="Lịch sử")
        s8 = Subject.objects.create(name="Địa lí")

        # 4. Teachers
        t1 = Teacher.objects.create(name="Thầy Nguyễn Văn A")
        t1.subjects.add(s1, s4)
        t1.classes.add(c1, c2, c3, c4)

        t2 = Teacher.objects.create(name="Cô Trần Thị B")
        t2.subjects.add(s2, s3)
        t2.classes.add(c1, c4, c5, c7)

        t3 = Teacher.objects.create(name="Thầy Lê Hoàng C")
        t3.subjects.add(s5, s6)
        t3.classes.add(c3, c4, c6, c7)

        t4 = Teacher.objects.create(name="Cô Phạm Thu D")
        t4.subjects.add(s7, s8)
        t4.classes.add(c2, c3, c5)

        t5 = Teacher.objects.create(name="Thầy Ngô Minh E")
        t5.subjects.add(s1)
        t5.classes.add(c5, c6, c7)

        t6 = Teacher.objects.create(name="Cô Đỗ Hoàng F")
        t6.subjects.add(s3)
        t6.classes.add(c2, c3, c6)

        # 5. Students grouped by classroom
        students_data = {
            c1: [
                "Nguyễn Đức Anh", "Trần Thu Thủy", "Lê Minh Triết", "Phạm Bích Phượng", "Hoàng Gia Bảo"
            ],
            c2: [
                "Nguyễn Hoàng Nam", "Vũ Minh Thư", "Đỗ Tuấn Kiệt", "Phan Thanh Hằng", "Bùi Quốc Anh"
            ],
            c3: [
                "Phạm Minh Tuấn", "Trần Đức Lợi", "Nguyễn Thu Hà", "Lê Hồng Nhung", "Đặng Quang Huy"
            ],
            c4: [
                "Trần Ngọc Hải", "Nguyễn Thùy Dương", "Phan Gia Khánh", "Đỗ Quỳnh Chi", "Vũ Hoàng Long"
            ],
            c5: [
                "Lê Thùy Chi", "Nguyễn Tuấn Tú", "Phạm Hải Đăng", "Trần Mai Anh", "Nguyễn Quốc Bảo"
            ],
            c6: [
                "Hoàng Khánh Linh", "Đỗ Minh Quân", "Lê Bảo Châu", "Phạm Tiến Dũng", "Nguyễn Phương Thảo"
            ],
            c7: [
                "Trần Thanh Tùng", "Nguyễn Hiền Mai", "Vũ Huy Hoàng", "Lê Cát Tường", "Phạm Trọng Nhân"
            ]
        }

        # Create students and store them
        students_by_class = {}
        for cls, names in students_data.items():
            students_by_class[cls] = []
            for name in names:
                student = Student.objects.create(name=name, classroom=cls)
                students_by_class[cls].append(student)

        # Class - Subject - Teacher configuration mappings
        class_subjects = [
            (c1, s1, t1), # 10A1 - Toán học - Thầy A
            (c1, s3, t2), # 10A1 - Tiếng Anh - Cô B
            (c1, s2, t2), # 10A1 - Ngữ văn - Cô B

            (c2, s1, t1), # 10A2 - Toán học - Thầy A
            (c2, s3, t6), # 10A2 - Tiếng Anh - Cô F
            (c2, s7, t4), # 10A2 - Lịch sử - Cô D

            (c3, s1, t1), # 11B1 - Toán học - Thầy A
            (c3, s3, t6), # 11B1 - Tiếng Anh - Cô F
            (c3, s5, t3), # 11B1 - Hóa học - Thầy C
            (c3, s8, t4), # 11B1 - Địa lí - Cô D

            (c4, s4, t1), # 11B2 - Vật lí - Thầy A
            (c4, s2, t2), # 11B2 - Ngữ văn - Cô B
            (c4, s5, t3), # 11B2 - Hóa học - Thầy C

            (c5, s1, t5), # 12C1 - Toán học - Thầy E
            (c5, s3, t2), # 12C1 - Tiếng Anh - Cô B
            (c5, s7, t4), # 12C1 - Lịch sử - Cô D

            (c6, s1, t5), # 12C2 - Toán học - Thầy E
            (c6, s3, t6), # 12C2 - Tiếng Anh - Cô F
            (c6, s6, t3), # 12C2 - Sinh học - Thầy C

            (c7, s1, t5), # 12C3 - Toán học - Thầy E
            (c7, s2, t2), # 12C3 - Ngữ văn - Cô B
            (c7, s6, t3), # 12C3 - Sinh học - Thầy C
        ]

        # 6. Create Enrollments
        self.stdout.write("Registering student enrollments...")
        for cls, sub, teacher in class_subjects:
            for student in students_by_class[cls]:
                Enrollment.objects.create(student=student, subject=sub, teacher=teacher)

        # 7. Create Payment Periods
        self.stdout.write("Creating payment periods...")
        periods = []
        for cls, sub, teacher in class_subjects:
            p1 = PaymentPeriod.objects.create(name="Tháng 9/2026", classroom=cls, teacher=teacher, subject=sub)
            periods.append(p1)
            
            # For heavier subjects, define a second billing period
            if sub in [s1, s2, s3, s4, s5]:
                p2 = PaymentPeriod.objects.create(name="Tháng 10/2026", classroom=cls, teacher=teacher, subject=sub)
                periods.append(p2)

        # 8. Populate Payments with randomized completion rates
        self.stdout.write("Generating payment receipts...")
        random.seed(42)
        
        amounts_by_subject = {
            s1: 500000, # Toán học
            s2: 450000, # Ngữ văn
            s3: 600000, # Tiếng Anh
            s4: 550000, # Vật lí
            s5: 550000, # Hóa học
            s6: 500000, # Sinh học
            s7: 400000, # Lịch sử
            s8: 400000, # Địa lí
        }

        payment_count = 0
        for period in periods:
            enrollments = Enrollment.objects.filter(
                student__classroom=period.classroom,
                subject=period.subject,
                teacher=period.teacher
            )
            
            # September has higher rate of payment completion compared to October
            payment_rate = 0.85 if period.name == "Tháng 9/2026" else 0.45
            
            for enrollment in enrollments:
                if random.random() < payment_rate:
                    amount = amounts_by_subject[period.subject]
                    
                    # Random day within the month
                    day = random.randint(5, 25)
                    month = 9 if period.name == "Tháng 9/2026" else 10
                    p_date = timezone.datetime(2026, month, day).date()
                    
                    Payment.objects.create(
                        student=enrollment.student,
                        classroom=period.classroom,
                        subject=period.subject,
                        teacher=period.teacher,
                        payment_period=period,
                        amount=amount,
                        payment_date=p_date
                    )
                    payment_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully populated sample data!\n"
            f"- Classrooms: {ClassRoom.objects.count()}\n"
            f"- Subjects: {Subject.objects.count()}\n"
            f"- Teachers: {Teacher.objects.count()}\n"
            f"- Students: {Student.objects.count()}\n"
            f"- Enrollments: {Enrollment.objects.count()}\n"
            f"- Payment Periods: {PaymentPeriod.objects.count()}\n"
            f"- Payment Records: {payment_count}"
        ))

import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from lms_manager.models import ClassRoom, Subject, Teacher, Student, Enrollment, PaymentPeriod, Payment

class Command(BaseCommand):
    help = 'Create mock data for the LMS project'

    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting existing data...")
        Payment.objects.all().delete()
        PaymentPeriod.objects.all().delete()
        Enrollment.objects.all().delete()
        Student.objects.all().delete()
        Teacher.objects.all().delete()
        Subject.objects.all().delete()
        ClassRoom.objects.all().delete()

        self.stdout.write("Creating ClassRooms...")
        c1 = ClassRoom.objects.create(name="11B1")
        c2 = ClassRoom.objects.create(name="11B1")
        c3 = ClassRoom.objects.create(name="12A2")

        self.stdout.write("Creating Subjects...")
        s_math = Subject.objects.create(name="Toán Học")
        s_phys = Subject.objects.create(name="Vật Lí")
        s_chem = Subject.objects.create(name="Hóa Học")
        s_eng = Subject.objects.create(name="Tiếng Anh")

        self.stdout.write("Creating Teachers...")
        t_an = Teacher.objects.create(name="Nguyễn Văn An", phone="0912345678")
        t_an.subjects.add(s_math, s_phys)
        t_an.classes.add(c1, c2)

        t_binh = Teacher.objects.create(name="Trần Thị Bình", phone="0987654321")
        t_binh.subjects.add(s_chem, s_eng)
        t_binh.classes.add(c2, c3)

        t_cuong = Teacher.objects.create(name="Lê Hoàng Cường", phone="0909090909")
        t_cuong.subjects.add(s_math)
        t_cuong.classes.add(c1, c3)

        self.stdout.write("Creating Students...")
        today = timezone.localdate()
        
        # Student 1: Started 3 months ago, has paid 2 periods (Period 1, 2), has unpaid Period 3 (past due), not in debt >= 2 periods
        stu1 = Student.objects.create(
            name="Phạm Minh Đức",
            classroom=c1,
            start_date=today - datetime.timedelta(days=95),
            dot_1="Đã đóng",
            dot_2="Đã đóng",
            dot_3="Chưa đóng"
        )
        
        # Student 1 Duplicate: Same student, but studying with Teacher Binh in her 11B1 class
        stu1_dup = Student.objects.create(
            name="Phạm Minh Đức",
            classroom=c2,
            start_date=today - datetime.timedelta(days=95),
            dot_1="Chưa đóng",
            dot_2="Đã đóng",
            dot_3="Chưa đóng"
        )
        
        # Student 2: Started 3 months ago, unpaid Period 1, 2, 3 -> In debt for 3 periods! (Should show on dashboard)
        stu2 = Student.objects.create(
            name="Đỗ Thu Hà",
            classroom=c2,
            start_date=today - datetime.timedelta(days=95),
            dot_1="Chưa đóng",
            dot_2="Chưa đóng",
            dot_3="Chưa đóng"
        )

        # Student 3: Started 2 months ago, unpaid Period 1, 2 -> In debt for 2 periods! (Should show on dashboard)
        stu3 = Student.objects.create(
            name="Trịnh Quốc Bảo",
            classroom=c2,
            start_date=today - datetime.timedelta(days=65),
            dot_1="Chưa đóng",
            dot_2="Chưa đóng"
        )

        # Student 4: Started 15 days ago, unpaid Period 1 -> Not overdue yet (deadline is 1 month from start date)
        stu4 = Student.objects.create(
            name="Lê Minh Khôi",
            classroom=c3,
            start_date=today - datetime.timedelta(days=15),
            dot_1="Chưa đóng"
        )

        # Student 5: Started today, all periods unpaid -> Not overdue yet
        stu5 = Student.objects.create(
            name="Nguyễn Thảo Nguyên",
            classroom=c1,
            start_date=today,
            dot_1="Chưa đóng"
        )

        self.stdout.write("Creating Enrollments...")
        # Enroll stu1 (An - Math)
        Enrollment.objects.create(student=stu1, subject=s_math, teacher=t_an)
        
        # Enroll stu1_dup (Binh - Eng)
        Enrollment.objects.create(student=stu1_dup, subject=s_eng, teacher=t_binh)

        # Enroll stu2 (Binh - Chem, Cuong - Math)
        Enrollment.objects.create(student=stu2, subject=s_chem, teacher=t_binh)
        Enrollment.objects.create(student=stu2, subject=s_math, teacher=t_cuong)

        # Enroll stu3 (An - Phys, Binh - Eng)
        Enrollment.objects.create(student=stu3, subject=s_phys, teacher=t_an)
        Enrollment.objects.create(student=stu3, subject=s_eng, teacher=t_binh)

        # Enroll stu4 (Cuong - Math)
        Enrollment.objects.create(student=stu4, subject=s_math, teacher=t_cuong)

        # Enroll stu5 (An - Math)
        Enrollment.objects.create(student=stu5, subject=s_math, teacher=t_an)

        self.stdout.write("Creating Payment Periods & Payments...")
        # Define period objects
        # Period 1, 2 for An - Math
        p_an_math_1, _ = PaymentPeriod.objects.get_or_create(name="Đợt 1", teacher=t_an, subject=s_math)
        p_an_math_2, _ = PaymentPeriod.objects.get_or_create(name="Đợt 2", teacher=t_an, subject=s_math)
        
        # Period 1, 2 for Binh - Eng
        p_binh_eng_1, _ = PaymentPeriod.objects.get_or_create(name="Đợt 1", teacher=t_binh, subject=s_eng)
        p_binh_eng_2, _ = PaymentPeriod.objects.get_or_create(name="Đợt 2", teacher=t_binh, subject=s_eng)

        # Add payments for stu1 (Math Đợt 1, 2)
        Payment.objects.create(
            student=stu1,
            classroom=c1,
            subject=s_math,
            teacher=t_an,
            payment_period=p_an_math_1,
            amount=500000,
            payment_date=today - datetime.timedelta(days=90)
        )
        Payment.objects.create(
            student=stu1,
            classroom=c1,
            subject=s_math,
            teacher=t_an,
            payment_period=p_an_math_2,
            amount=500000,
            payment_date=today - datetime.timedelta(days=60)
        )
        
        # Add payments for stu1_dup (Eng Đợt 1, 2)
        Payment.objects.create(
            student=stu1_dup,
            classroom=c2,
            subject=s_eng,
            teacher=t_binh,
            payment_period=p_binh_eng_1,
            amount=500000,
            payment_date=today - datetime.timedelta(days=90)
        )
        Payment.objects.create(
            student=stu1_dup,
            classroom=c2,
            subject=s_eng,
            teacher=t_binh,
            payment_period=p_binh_eng_2,
            amount=500000,
            payment_date=today - datetime.timedelta(days=60)
        )

        self.stdout.write(self.style.SUCCESS("Mock data successfully created!"))

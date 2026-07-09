from django.test import TestCase
from lms_manager.models import ClassRoom, Subject, Teacher, Student, Enrollment, PaymentPeriod, Payment

class LMSManagerQueryTest(TestCase):
    def setUp(self):
        self.classroom = ClassRoom.objects.create(name="10A1")
        self.subject = Subject.objects.create(name="Math")
        self.teacher = Teacher.objects.create(name="Mr. Smith")
        self.teacher.subjects.add(self.subject)
        self.teacher.classes.add(self.classroom)
        
        self.student1 = Student.objects.create(name="John Doe", classroom=self.classroom)
        self.student2 = Student.objects.create(name="Jane Doe", classroom=self.classroom)
        
        self.enrollment1 = Enrollment.objects.create(
            student=self.student1,
            subject=self.subject,
            teacher=self.teacher
        )
        self.enrollment2 = Enrollment.objects.create(
            student=self.student2,
            subject=self.subject,
            teacher=self.teacher
        )
        
        self.payment_period = PaymentPeriod.objects.create(
            name="Period 1",
            classroom=self.classroom,
            teacher=self.teacher,
            subject=self.subject
        )
        
        # student1 paid, student2 didn't
        self.payment = Payment.objects.create(
            student=self.student1,
            classroom=self.classroom,
            subject=self.subject,
            teacher=self.teacher,
            payment_period=self.payment_period,
            amount=100000
        )
        
    def test_unpaid_enrollments_query(self):
        period = self.payment_period
        unpaid = Enrollment.objects.filter(
            student__classroom=period.classroom,
            subject=period.subject,
            teacher=period.teacher,
        ).exclude(
            student__payments__payment_period=period
        )
        
        self.assertEqual(unpaid.count(), 1)
        self.assertEqual(unpaid.first().student, self.student2)

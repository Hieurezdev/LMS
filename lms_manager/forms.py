from django import forms
from .models import ClassRoom, Subject, Teacher, Student, Enrollment, Payment, PaymentPeriod

class ClassRoomForm(forms.ModelForm):
    class Meta:
        model = ClassRoom
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: 12A, Lớp Toán nâng cao'}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: Toán, Vật lí'}),
        }


class TeacherForm(forms.ModelForm):
    subject_name = forms.CharField(
        label="Môn giảng dạy (Nhập tên)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập tên môn học (ví dụ: Toán học, Vật lí)...',
            'id': 'id_subject_name',
            'list': 'subject-list',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = Teacher
        fields = ['name', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên giảng viên'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số điện thoại (tùy chọn)'}),
        }



class StudentForm(forms.ModelForm):
    classroom = forms.ModelChoiceField(
        queryset=ClassRoom.objects.all(),
        required=False,
        label="Lớp học",
        widget=forms.Select(attrs={'class': 'form-control form-select', 'id': 'id_classroom'})
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        label="Môn học đăng ký (Tùy chọn)",
        widget=forms.Select(attrs={'class': 'form-control form-select', 'id': 'id_subject'})
    )
    teacher = forms.ModelChoiceField(
        queryset=Teacher.objects.all(),
        required=False,
        label="Giảng viên dạy (Tùy chọn)",
        widget=forms.Select(attrs={'class': 'form-control form-select', 'id': 'id_teacher'})
    )

    class Meta:
        model = Student
        fields = ['name', 'classroom', 'start_date']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên học sinh'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    field_order = ['name', 'start_date', 'teacher', 'subject', 'classroom']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            # Creation mode
            self.fields['teacher'].required = True
            self.fields['subject'].required = True
            self.fields['classroom'].required = True
            self.fields['teacher'].label = "Giảng viên đăng ký học"
            self.fields['subject'].label = "Môn học đăng ký"
            self.fields['classroom'].label = "Lớp học"
        else:
            # Edit mode: remove teacher and subject fields as they are only for enrollment
            if 'teacher' in self.fields:
                del self.fields['teacher']
            if 'subject' in self.fields:
                del self.fields['subject']


class EnrollmentForm(forms.ModelForm):
    classroom = forms.ModelChoiceField(
        queryset=ClassRoom.objects.all(),
        required=True,
        label="Lớp học",
        widget=forms.Select(attrs={'class': 'form-control form-select', 'id': 'id_classroom'})
    )

    class Meta:
        model = Enrollment
        fields = ['student', 'subject', 'teacher']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control form-select'}),
            'subject': forms.Select(attrs={'class': 'form-control form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-control form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically restrict teacher choices based on the selected subject if any
        # (This will be complemented by JS on the frontend if needed, but we keep the options populated)
        self.fields['teacher'].queryset = Teacher.objects.all()


class PaymentPeriodForm(forms.ModelForm):
    class Meta:
        model = PaymentPeriod
        fields = ['name', 'subject', 'teacher']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: Đợt 1, Đợt 2'}),
            'subject': forms.Select(attrs={'class': 'form-control form-select'}),
            'teacher': forms.Select(attrs={'class': 'form-control form-select'}),
        }


class PaymentForm(forms.ModelForm):
    student_name = forms.CharField(
        label="Học sinh (Nhập tên)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập tên học sinh...',
            'id': 'id_student_name',
            'list': 'student-list',
            'autocomplete': 'off'
        })
    )
    payment_period = forms.CharField(
        label="Đợt đóng tiền",
        widget=forms.Select(attrs={'class': 'form-control form-select', 'id': 'id_payment_period'})
    )

    class Meta:
        model = Payment
        fields = ['teacher', 'amount', 'payment_date']
        widgets = {
            'teacher': forms.Select(attrs={'class': 'form-control form-select', 'id': 'id_teacher'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Nhập số tiền đóng (VNĐ)'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    field_order = ['student_name', 'teacher', 'payment_period', 'amount', 'payment_date']



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date to today in HTML format (YYYY-MM-DD)
        from django.utils import timezone
        self.fields['payment_date'].initial = timezone.localdate()

import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count
from django.contrib import messages
from django.utils import timezone
from .models import ClassRoom, Subject, Teacher, Student, Enrollment, Payment, PaymentPeriod
from .forms import ClassRoomForm, SubjectForm, TeacherForm, StudentForm, EnrollmentForm, PaymentForm, PaymentPeriodForm

# -------------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------------
def dashboard_view(request):
    # Overall Counts
    student_count = Student.objects.count()
    teacher_count = Teacher.objects.count()
    subject_count = Subject.objects.count()
    class_count = ClassRoom.objects.count()
    period_count = PaymentPeriod.objects.count()
    payment_count = Payment.objects.count()

    # Total Revenue
    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0

    # Revenue by payment period
    revenue_by_period = list(Payment.objects.values('payment_period__name')
                            .annotate(total=Sum('amount'))
                            .order_by('-total'))

    # Revenue by classroom
    revenue_by_class = list(Payment.objects.values('classroom__id', 'classroom__name')
                           .annotate(total=Sum('amount'))
                           .order_by('-total'))

    # Revenue by subject
    revenue_by_subject = list(Payment.objects.values('subject__name')
                             .annotate(total=Sum('amount'))
                             .order_by('-total'))

    # Revenue by teacher
    revenue_by_teacher = list(Payment.objects.values('teacher__id', 'teacher__name')
                             .annotate(total=Sum('amount'))
                             .order_by('-total'))

    # ---- Onboarding wizard state ----
    setup_steps = [
        {
            'key': 'classroom',
            'icon': 'fa-school',
            'color': 'primary',
            'label': 'Tạo Lớp học',
            'desc': 'Khởi tạo các lớp (VD: 10A1, 11B2, Lớp Toán nâng cao).',
            'count': class_count,
            'done': class_count > 0,
            'url_name': 'classroom_list',
        },
        {
            'key': 'subject',
            'icon': 'fa-book-open',
            'color': 'info',
            'label': 'Tạo Môn học',
            'desc': 'Thêm các môn (Toán, Vật lí, Hóa học...) để gán cho giảng viên.',
            'count': subject_count,
            'done': subject_count > 0,
            'url_name': 'subject_list',
        },
        {
            'key': 'teacher',
            'icon': 'fa-chalkboard-teacher',
            'color': 'warning',
            'label': 'Thêm Giảng viên',
            'desc': 'Tạo giảng viên và gán môn + lớp phụ trách.',
            'count': teacher_count,
            'done': teacher_count > 0,
            'url_name': 'teacher_list',
        },
        {
            'key': 'period',
            'icon': 'fa-calendar-alt',
            'color': 'secondary',
            'label': 'Tạo Đợt đóng tiền',
            'desc': 'Định nghĩa đợt thu học phí (Đợt 1, Tháng 7...) cho từng lớp + môn + GV.',
            'count': period_count,
            'done': period_count > 0,
            'url_name': 'payment_period_list',
        },
    ]
    all_done = all(step['done'] for step in setup_steps)
    done_count = sum(1 for s in setup_steps if s['done'])

    # ---- Công nợ (nổi bật) ----
    # Tổng số bản ghi "chưa đóng" trong bảng kê
    debt_total_amount = 0
    debt_total_count = 0
    debt_rows = []
    for period in PaymentPeriod.objects.all().select_related('subject', 'teacher'):
        unpaid = Enrollment.objects.filter(
            subject=period.subject,
            teacher=period.teacher,
        ).exclude(
            student__payments__payment_period=period
        ).select_related('student', 'student__classroom').order_by('student__name')

        for e in unpaid:
            debt_rows.append({
                'student': e.student,
                'classroom': e.student.classroom,
                'subject': period.subject,
                'teacher': period.teacher,
                'period': period,
            })
            debt_total_count += 1

    # Sắp xếp theo lớp rồi tên học sinh
    debt_rows.sort(key=lambda r: (r['classroom'].name, r['student'].name))
    # Lấy 8 dòng đầu để hiển thị nhanh
    debt_preview = debt_rows[:8]

    context = {
        'student_count': student_count,
        'teacher_count': teacher_count,
        'subject_count': subject_count,
        'class_count': class_count,
        'period_count': period_count,
        'payment_count': payment_count,
        'total_revenue': total_revenue,
        'revenue_by_period': revenue_by_period,
        'revenue_by_class': revenue_by_class,
        'revenue_by_subject': revenue_by_subject,
        'revenue_by_teacher': revenue_by_teacher,
        'setup_steps': setup_steps,
        'setup_done_count': done_count,
        'setup_total': len(setup_steps),
        'setup_all_done': all_done,
        'debt_total_count': debt_total_count,
        'debt_rows': debt_preview,
    }
    return render(request, 'lms_manager/dashboard.html', context)


# -------------------------------------------------------------
# DEBT DASHBOARD (Công nợ)
# -------------------------------------------------------------
def debt_dashboard(request):
    """
    Tổng hợp tất cả các khoản học phí chưa đóng theo từng đợt/lớp/giảng viên.
    Có bộ lọc theo lớp, giảng viên, môn học.
    """
    classrooms = ClassRoom.objects.all().order_by('name')
    teachers = Teacher.objects.all().order_by('name')
    subjects = Subject.objects.all().order_by('name')

    classroom_id = request.GET.get('classroom_id', '').strip()
    teacher_id = request.GET.get('teacher_id', '').strip()
    subject_id = request.GET.get('subject_id', '').strip()

    periods = PaymentPeriod.objects.all().select_related('subject', 'teacher')

    if teacher_id:
        periods = periods.filter(teacher_id=teacher_id)
    if subject_id:
        periods = periods.filter(subject_id=subject_id)

    periods = periods.order_by('name', 'subject__name')

    period_reports = []
    total_debt_count = 0

    for period in periods:
        enrollment_filter = {
            'subject': period.subject,
            'teacher': period.teacher,
        }
        if classroom_id:
            enrollment_filter['student__classroom_id'] = classroom_id

        enrollments = Enrollment.objects.filter(
            **enrollment_filter
        ).exclude(
            student__payments__payment_period=period
        ).select_related('student', 'student__classroom').order_by('student__classroom__name', 'student__name')

        unpaid_records = []
        for e in enrollments:
            unpaid_records.append({
                'student': e.student,
                'classroom': e.student.classroom,
            })

        if not unpaid_records:
            continue

        total_debt_count += len(unpaid_records)

        period_reports.append({
            'period': period,
            'period_label': f"{period.name} - Môn: {period.subject.name} (GV: {period.teacher.name})",
            'records': unpaid_records,
        })

    context = {
        'classrooms': classrooms,
        'teachers': teachers,
        'subjects': subjects,
        'selected_classroom_id': classroom_id,
        'selected_teacher_id': teacher_id,
        'selected_subject_id': subject_id,
        'period_reports': period_reports,
        'total_debt_count': total_debt_count,
    }
    return render(request, 'lms_manager/debt_dashboard.html', context)


# -------------------------------------------------------------
# CLASSROOM CRUD
# -------------------------------------------------------------
def classroom_list(request):
    classes = ClassRoom.objects.all().order_by('name')
    
    class_reports = []
    for c in classes:
        student_count = c.students.count()
        subject_count = Enrollment.objects.filter(student__classroom=c).values('subject').distinct().count()
        revenue = Payment.objects.filter(classroom=c).aggregate(total=Sum('amount'))['total'] or 0
        
        class_reports.append({
            'classroom': c,
            'student_count': student_count,
            'subject_count': subject_count,
            'revenue': revenue,
        })
        
    return render(request, 'lms_manager/classroom_list.html', {'class_reports': class_reports})

def classroom_create(request):
    if request.method == 'POST':
        form = ClassRoomForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm lớp học thành công!")
            return redirect('classroom_list')
    else:
        form = ClassRoomForm()
    return render(request, 'lms_manager/form.html', {'form': form, 'title': 'Thêm lớp học'})

def classroom_update(request, pk):
    classroom = get_object_or_404(ClassRoom, pk=pk)
    if request.method == 'POST':
        form = ClassRoomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật lớp học thành công!")
            return redirect('classroom_detail', pk=classroom.id)
    else:
        form = ClassRoomForm(instance=classroom)
    return render(request, 'lms_manager/form.html', {'form': form, 'title': 'Sửa lớp học'})

def classroom_delete(request, pk):
    classroom = get_object_or_404(ClassRoom, pk=pk)
    classroom.delete()
    messages.success(request, "Đã xóa lớp học!")
    return redirect('classroom_list')


# -------------------------------------------------------------
# SUBJECT CRUD
# -------------------------------------------------------------
def subject_list(request):
    subjects = Subject.objects.all().order_by('name')
    return render(request, 'lms_manager/subject_list.html', {'subjects': subjects})

def subject_create(request):
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm môn học thành công!")
            return redirect('subject_list')
    else:
        form = SubjectForm()
    return render(request, 'lms_manager/form.html', {'form': form, 'title': 'Thêm môn học'})

def subject_update(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật môn học thành công!")
            return redirect('subject_list')
    else:
        form = SubjectForm(instance=subject)
    return render(request, 'lms_manager/form.html', {'form': form, 'title': 'Sửa môn học'})

def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    subject.delete()
    messages.success(request, "Đã xóa môn học!")
    return redirect('subject_list')


# -------------------------------------------------------------
# TEACHER CRUD
# -------------------------------------------------------------
def teacher_list(request):
    teachers = Teacher.objects.all().order_by('name')
    return render(request, 'lms_manager/teacher_list.html', {'teachers': teachers})

def teacher_create(request):
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            teacher = form.save(commit=False)
            
            # Capitalize teacher name (Title Case)
            teacher.name = " ".join(word.capitalize() for word in form.cleaned_data['name'].split())
            teacher.save()
            
            # Process typed subject names (supports comma-separated values)
            raw_subjects = form.cleaned_data.get('subject_name', '')
            subject_names = [s.strip() for s in raw_subjects.split(',') if s.strip()]
            
            subject_objs = []
            for name in subject_names:
                capitalized_sub = " ".join(word.capitalize() for word in name.split())
                sub, _ = Subject.objects.get_or_create(name=capitalized_sub)
                subject_objs.append(sub)
                
            teacher.subjects.set(subject_objs)
            
            # Process typed classroom names (supports comma-separated values)
            raw_classes = form.cleaned_data.get('class_names', '')
            class_names = [c.strip() for c in raw_classes.split(',') if c.strip()]
            
            class_objs = []
            for name in class_names:
                # Smart format for classrooms: e.g. "10a1" -> "10A1", "lớp toán" -> "Lớp Toán"
                capitalized_class = " ".join(
                    word.upper() if (len(word) <= 4 and any(char.isdigit() for char in word))
                    else word.capitalize()
                    for word in name.split()
                )
                cls, _ = ClassRoom.objects.get_or_create(name=capitalized_class)
                class_objs.append(cls)
                
            teacher.classes.set(class_objs)
            
            messages.success(request, f"Đã thêm giảng viên '{teacher.name}' thành công!")
            return redirect('teacher_list')
    else:
        form = TeacherForm()
        
    existing_subjects = Subject.objects.all().order_by('name')
    existing_classrooms = ClassRoom.objects.all().order_by('name')
    return render(request, 'lms_manager/teacher_create_form.html', {
        'form': form,
        'title': 'Thêm giảng viên',
        'existing_subjects': existing_subjects,
        'existing_classrooms': existing_classrooms
    })

def teacher_update(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            teacher = form.save(commit=False)
            
            # Capitalize teacher name (Title Case)
            teacher.name = " ".join(word.capitalize() for word in form.cleaned_data['name'].split())
            teacher.save()
            
            # Process typed subject names (supports comma-separated values)
            raw_subjects = form.cleaned_data.get('subject_name', '')
            subject_names = [s.strip() for s in raw_subjects.split(',') if s.strip()]
            
            subject_objs = []
            for name in subject_names:
                capitalized_sub = " ".join(word.capitalize() for word in name.split())
                sub, _ = Subject.objects.get_or_create(name=capitalized_sub)
                subject_objs.append(sub)
                
            teacher.subjects.set(subject_objs)
            
            # Process typed classroom names (supports comma-separated values)
            raw_classes = form.cleaned_data.get('class_names', '')
            class_names = [c.strip() for c in raw_classes.split(',') if c.strip()]
            
            class_objs = []
            for name in class_names:
                capitalized_class = " ".join(
                    word.upper() if (len(word) <= 4 and any(char.isdigit() for char in word))
                    else word.capitalize()
                    for word in name.split()
                )
                cls, _ = ClassRoom.objects.get_or_create(name=capitalized_class)
                class_objs.append(cls)
                
            teacher.classes.set(class_objs)
            
            messages.success(request, f"Đã cập nhật giảng viên '{teacher.name}' thành công!")
            return redirect('teacher_detail', pk=teacher.id)
    else:
        initial_data = {
            'subject_name': ", ".join(s.name for s in teacher.subjects.all()),
            'class_names': ", ".join(c.name for c in teacher.classes.all())
        }
        form = TeacherForm(instance=teacher, initial=initial_data)
        
    existing_subjects = Subject.objects.all().order_by('name')
    existing_classrooms = ClassRoom.objects.all().order_by('name')
    return render(request, 'lms_manager/teacher_create_form.html', {
        'form': form,
        'title': 'Sửa giảng viên',
        'existing_subjects': existing_subjects,
        'existing_classrooms': existing_classrooms
    })

def teacher_delete(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    teacher.delete()
    messages.success(request, "Đã xóa giảng viên!")
    return redirect('teacher_list')


def teacher_import_template(request):
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Template_Nhap_Lop_Giang_Vien.csv"'
    
    # Prepend UTF-8 BOM so Excel opens it with correct Vietnamese accents
    response.write(b'\xef\xbb\xbf')
    
    writer = csv.writer(response)
    writer.writerow(['Tên Lớp học', 'Môn giảng dạy'])
    writer.writerow(['10A1', 'Toán học'])
    writer.writerow(['11B2', 'Vật lí'])
    writer.writerow(['Lớp Toán nâng cao', 'Hình học'])
    return response


def teacher_import_excel(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    
    if request.method == 'POST':
        csv_file = request.FILES.get('excel_file')
        if not csv_file:
            messages.error(request, "Vui lòng chọn một tệp CSV để tải lên!")
            return redirect('teacher_import_excel', pk=teacher.id)
            
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Hệ thống chỉ hỗ trợ tệp định dạng .csv (mã hóa UTF-8)!")
            return redirect('teacher_import_excel', pk=teacher.id)
            
        try:
            # Read file content and decode from UTF-8 (utf-8-sig strips BOM)
            file_data = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(file_data)
            
            # Read CSV
            reader = csv.reader(io_string, delimiter=',')
            header = next(reader, None) # skip header row
            
            imported_classes = 0
            imported_subjects = 0
            
            for row in reader:
                if not row or len(row) < 2:
                    continue
                
                raw_class = row[0].strip()
                raw_subject = row[1].strip()
                
                if not raw_class or not raw_subject:
                    continue
                
                # Format classroom name using our smart formatting
                capitalized_class = " ".join(
                    word.upper() if (len(word) <= 4 and any(char.isdigit() for char in word))
                    else word.capitalize()
                    for word in raw_class.split()
                )
                
                # Format subject name
                capitalized_sub = " ".join(word.capitalize() for word in raw_subject.split())
                
                # Get or create
                classroom, class_created = ClassRoom.objects.get_or_create(name=capitalized_class)
                subject, sub_created = Subject.objects.get_or_create(name=capitalized_sub)
                
                if class_created:
                    imported_classes += 1
                if sub_created:
                    imported_subjects += 1
                    
                # Associate with teacher
                teacher.classes.add(classroom)
                teacher.subjects.add(subject)
                
            messages.success(
                request, 
                f"Nhập dữ liệu thành công! Đã liên kết giảng viên với các lớp & môn học tương ứng. "
                f"(Tạo mới {imported_classes} lớp học và {imported_subjects} môn học mới)."
            )
            return redirect('teacher_detail', pk=teacher.id)
            
        except Exception as e:
            messages.error(request, f"Đã xảy ra lỗi khi đọc tệp: {str(e)}")
            return redirect('teacher_import_excel', pk=teacher.id)
            
    return render(request, 'lms_manager/teacher_import_excel.html', {'teacher': teacher})


# -------------------------------------------------------------
# STUDENT & ENROLLMENT CRUD
# -------------------------------------------------------------
def student_list(request):
    classrooms = ClassRoom.objects.all().order_by('name')
    students = Student.objects.all().select_related('classroom').prefetch_related('enrollments__subject', 'enrollments__teacher')
    
    search_name = request.GET.get('name', '').strip()
    classroom_id = request.GET.get('classroom_id', '').strip()
    
    if search_name:
        students = students.filter(name__icontains=search_name)
    if classroom_id:
        students = students.filter(classroom_id=classroom_id)
        
    students = students.order_by('classroom__name', 'name')
    
    return render(request, 'lms_manager/student_list.html', {
        'students': students,
        'classrooms': classrooms,
        'search_name': search_name,
        'selected_classroom_id': classroom_id,
    })

def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            subject = form.cleaned_data.get('subject')
            teacher = form.cleaned_data.get('teacher')
            
            if subject and teacher:
                Enrollment.objects.get_or_create(
                    student=student,
                    subject=subject,
                    defaults={'teacher': teacher}
                )
                messages.success(request, f"Đã thêm học sinh '{student.name}' và đăng ký học môn {subject.name} với GV {teacher.name}!")
            else:
                messages.success(request, f"Đã thêm học sinh '{student.name}' thành công!")
                
            return redirect('student_list')
    else:
        form = StudentForm()
    return render(request, 'lms_manager/student_create_form.html', {'form': form})

def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật học sinh thành công!")
            return redirect('student_detail', pk=student.id)
    else:
        form = StudentForm(instance=student)
    return render(request, 'lms_manager/form.html', {'form': form, 'title': 'Sửa học sinh'})

def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    student.delete()
    messages.success(request, "Đã xóa học sinh!")
    return redirect('student_list')

def student_register(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    enrollments = Enrollment.objects.filter(student=student)
    
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            # Check unique_together manually to provide friendly warning if already registered
            subject = form.cleaned_data['subject']
            if Enrollment.objects.filter(student=student, subject=subject).exists():
                messages.warning(request, f"Học sinh đã đăng ký môn {subject.name} trước đó rồi!")
            else:
                enrollment = form.save(commit=False)
                enrollment.student = student
                enrollment.save()
                messages.success(request, f"Đăng ký thành công môn {subject.name} cho {student.name}!")
            return redirect('student_register', student_id=student.id)
    else:
        form = EnrollmentForm(initial={'student': student})
        # Hide the student selection field or lock it since we are on the student-specific page
        form.fields['student'].widget = forms.HiddenInput()
        
    return render(request, 'lms_manager/student_register.html', {
        'student': student,
        'enrollments': enrollments,
        'form': form
    })

def enrollment_delete(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    student_id = enrollment.student.id
    enrollment.delete()
    messages.success(request, "Đã hủy đăng ký môn học!")
    return redirect('student_register', student_id=student_id)


# -------------------------------------------------------------
# PAYMENT & BILLING CRUD
# -------------------------------------------------------------
def payment_list(request):
    payments = Payment.objects.all().order_by('-payment_date', '-id')
    return render(request, 'lms_manager/payment_list.html', {'payments': payments})

def payment_create(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            
            # Get typed student name and capitalize it (Title Case)
            raw_name = form.cleaned_data.get('student_name', '').strip()
            capitalized_name = " ".join(word.capitalize() for word in raw_name.split())
            
            # Find student first to resolve their classroom
            student = Student.objects.filter(name=capitalized_name).first()
            if student:
                classroom = student.classroom
                created = False
            else:
                classroom = ClassRoom.objects.first()
                student = Student.objects.create(name=capitalized_name, classroom=classroom)
                created = True
            
            payment.student = student
            payment.classroom = classroom
            payment.subject = payment.payment_period.subject
            # Override teacher to match the selected payment period's teacher
            payment.teacher = payment.payment_period.teacher
            
            # Auto-enroll student in the subject if not enrolled yet
            Enrollment.objects.get_or_create(
                student=student,
                subject=payment.subject,
                defaults={'teacher': payment.teacher}
            )
            
            payment.save()
            
            if created:
                messages.success(request, f"Đã thêm học sinh mới '{student.name}' vào lớp {classroom.name}!")
            messages.success(request, f"Đã ghi nhận đóng tiền thành công đợt '{payment.payment_period.name}' cho học sinh '{student.name}'!")
            return redirect('payment_list')
        else:
            messages.error(request, "Thông tin nhập không hợp lệ!")
    else:
        initial_data = {}
        student_id = request.GET.get('student')
        if student_id:
            student = Student.objects.filter(id=student_id).first()
            if student:
                initial_data['student_name'] = student.name
        if 'period' in request.GET:
            period_id = request.GET.get('period')
            initial_data['payment_period'] = period_id
            period_obj = PaymentPeriod.objects.filter(id=period_id).first()
            if period_obj:
                initial_data['teacher'] = period_obj.teacher.id
                # Pre-populate typical amount for this subject
                last_payment = Payment.objects.filter(subject=period_obj.subject).order_by('-id').first()
                if last_payment:
                    initial_data['amount'] = int(last_payment.amount)
                else:
                    sub_name = period_obj.subject.name.lower()
                    if "toán" in sub_name:
                        initial_data['amount'] = 500000
                    elif "văn" in sub_name:
                        initial_data['amount'] = 450000
                    elif "anh" in sub_name:
                        initial_data['amount'] = 600000
                    elif "lý" in sub_name or "lí" in sub_name or "hóa" in sub_name:
                        initial_data['amount'] = 550000
                    else:
                        initial_data['amount'] = 500000
        form = PaymentForm(initial=initial_data)
        
    existing_students = Student.objects.all().order_by('name')
    return render(request, 'lms_manager/payment_create.html', {
        'form': form,
        'existing_students': existing_students
    })

def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    payment.delete()
    messages.success(request, "Đã xóa đợt đóng tiền!")
    return redirect('payment_list')

def payment_receipt(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    import os
    if not payment.receipt_pdf or not os.path.exists(payment.receipt_pdf.path):
        payment.generate_receipt_pdf()
        payment.refresh_from_db()
        
    response = HttpResponse(payment.receipt_pdf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="receipt_{payment.id}.pdf"'
    return response


# -------------------------------------------------------------
# AJAX API FOR DYNAMIC DROPDOWNS
# -------------------------------------------------------------
def get_student_subjects(request, student_id):
    enrollments = Enrollment.objects.filter(student_id=student_id).select_related('subject')
    data = []
    for e in enrollments:
        data.append({
            'id': e.subject.id,
            'name': e.subject.name
        })
    return JsonResponse({'subjects': data})


def get_student_payment_periods(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    
    # Get subjects student is enrolled in
    enrollments = student.enrollments.all()
    
    # Construct filters for student's registered subject-teacher pairs
    from django.db.models import Q
    q_filter = Q()
    for enrollment in enrollments:
        q_filter |= Q(subject_id=enrollment.subject_id, teacher_id=enrollment.teacher_id)
        
    periods = []
    if enrollments:
        periods = list(
            PaymentPeriod.objects.filter(q_filter)
            .select_related('subject', 'teacher')
            .order_by('name', 'subject__name')
        )
    
    data = []
    for p in periods:
        data.append({
            'id': p.id,
            'name': f"{p.name} - Môn: {p.subject.name} (GV: {p.teacher.name})"
        })
        
    return JsonResponse({'periods': data})


def filter_payment_periods(request):
    student_id = request.GET.get('student_id')
    teacher_id = request.GET.get('teacher_id')
    
    periods = PaymentPeriod.objects.all().select_related('subject', 'teacher')
    
    if student_id:
        student = Student.objects.filter(id=student_id).first()
        if student:
            enrollments = student.enrollments.all()
            from django.db.models import Q
            q_filter = Q()
            for enrollment in enrollments:
                q_filter |= Q(subject_id=enrollment.subject_id, teacher_id=enrollment.teacher_id)
            if enrollments:
                periods = periods.filter(q_filter)
            else:
                periods = periods.none()
            
    if teacher_id:
        periods = periods.filter(teacher_id=teacher_id)
        
    periods = periods.order_by('name', 'subject__name')
    
    data = []
    for p in periods:
        data.append({
            'id': p.id,
            'name': f"{p.name} - Môn: {p.subject.name} (GV: {p.teacher.name})"
        })
        
    return JsonResponse({'periods': data})


def get_subject_teachers(request, subject_id):
    teachers = Teacher.objects.filter(subjects__id=subject_id).distinct().order_by('name')
    data = [{'id': t.id, 'name': t.name} for t in teachers]
    return JsonResponse({'teachers': data})


def get_period_details(request, period_id):
    period = get_object_or_404(PaymentPeriod, pk=period_id)
    last_payment = Payment.objects.filter(subject=period.subject).order_by('-id').first()
    
    if last_payment:
        amount = int(last_payment.amount)
    else:
        sub_name = period.subject.name.lower()
        if "toán" in sub_name:
            amount = 500000
        elif "văn" in sub_name:
            amount = 450000
        elif "anh" in sub_name:
            amount = 600000
        elif "lý" in sub_name or "lí" in sub_name or "hóa" in sub_name:
            amount = 550000
        else:
            amount = 500000
            
    return JsonResponse({
        'amount': amount,
        'teacher_id': period.teacher.id,
    })


def teacher_detail(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    subjects = teacher.subjects.all()
    
    # Get all payment periods specifically defined for this teacher
    payment_periods = list(
        PaymentPeriod.objects.filter(teacher=teacher)
        .select_related('subject')
        .order_by('name')
    )
    
    period_reports = []
    for period in payment_periods:
        records = []
        total_paid_in_period = 0
        
        # Get enrollments for this subject and teacher
        enrollments = Enrollment.objects.filter(
            subject=period.subject,
            teacher=teacher
        ).select_related('student', 'student__classroom').order_by('student__classroom__name', 'student__name')
        
        for enrollment in enrollments:
            payment = Payment.objects.filter(
                student=enrollment.student,
                classroom=enrollment.student.classroom,
                subject=period.subject,
                payment_period=period
            ).first()
            
            if payment:
                status = "Đã đóng"
                amount = payment.amount
                date = payment.payment_date
                payment_id = payment.id
                total_paid_in_period += amount
            else:
                status = "Chưa đóng"
                amount = 0
                date = None
                payment_id = None
                
            records.append({
                'student': enrollment.student,
                'status': status,
                'amount': amount,
                'net_amount': float(amount) * 0.8,
                'date': date,
                'payment_id': payment_id,
                'payment': payment,
            })
            
        period_reports.append({
            'period_id': period.id,
            'period_name': f"{period.name} (Môn: {period.subject.name})",
            'simple_name': period.name,
            'subject_name': period.subject.name,
            'records': records,
            'total_paid': total_paid_in_period,
            'total_net': float(total_paid_in_period) * 0.8,
        })
        
    total_earned = Payment.objects.filter(teacher=teacher).aggregate(total=Sum('amount'))['total'] or 0
    total_net_earned = float(total_earned) * 0.8
    
    return render(request, 'lms_manager/teacher_detail.html', {
        'teacher': teacher,
        'subjects': subjects,
        'period_reports': period_reports,
        'total_earned': total_earned,
        'total_net_earned': total_net_earned,
    })


def classroom_detail(request, pk):
    classroom = get_object_or_404(ClassRoom, pk=pk)
    
    # Get all students in this classroom
    students = Student.objects.filter(classroom=classroom).order_by('name')
    
    # Build list of student reports (student + their subject enrollments)
    student_reports = []
    for student in students:
        enrollments = Enrollment.objects.filter(student=student).select_related('subject', 'teacher')
        student_reports.append({
            'student': student,
            'enrollments': enrollments,
        })
    
    # Get all (teacher, subject) combinations active in this classroom
    active_lessons = Enrollment.objects.filter(
        student__classroom=classroom
    ).values('teacher', 'subject').distinct()
    
    # Query all payment periods matching these active lessons
    payment_periods = []
    if active_lessons:
        from django.db.models import Q
        q_filter = Q()
        for lesson in active_lessons:
            q_filter |= Q(teacher_id=lesson['teacher'], subject_id=lesson['subject'])
        payment_periods = list(
            PaymentPeriod.objects.filter(q_filter)
            .select_related('teacher', 'subject')
            .order_by('name', 'subject__name')
        )
    
    period_reports = []
    for period in payment_periods:
        records = []
        total_paid_in_period = 0
        
        # Get enrollments for this class, subject, and teacher
        enrollments = Enrollment.objects.filter(
            student__classroom=classroom,
            subject=period.subject,
            teacher=period.teacher
        ).select_related('student')
        
        for enrollment in enrollments:
            payment = Payment.objects.filter(
                student=enrollment.student,
                classroom=classroom,
                subject=period.subject,
                payment_period=period
            ).first()
            
            if payment:
                status = "Đã đóng"
                amount = payment.amount
                date = payment.payment_date
                payment_id = payment.id
                total_paid_in_period += amount
            else:
                status = "Chưa đóng"
                amount = 0
                date = None
                payment_id = None
                
            records.append({
                'student': enrollment.student,
                'subject': enrollment.subject,
                'teacher': enrollment.teacher,
                'status': status,
                'amount': amount,
                'date': date,
                'payment_id': payment_id,
                'payment': payment,
            })
            
        period_reports.append({
            'period_id': period.id,
            'period_name': f"{period.name} - Môn: {period.subject.name} (GV: {period.teacher.name})",
            'simple_name': period.name,
            'subject_name': period.subject.name,
            'teacher_name': period.teacher.name,
            'records': records,
            'total_paid': total_paid_in_period,
        })
        
    total_paid_all = Payment.objects.filter(classroom=classroom).aggregate(total=Sum('amount'))['total'] or 0
    
    return render(request, 'lms_manager/classroom_detail.html', {
        'classroom': classroom,
        'period_reports': period_reports,
        'total_paid_all': total_paid_all,
        'students': students,
        'student_reports': student_reports,
    })


def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    classroom = student.classroom
    
    # Get all enrollments for this student
    enrollments = Enrollment.objects.filter(student=student).select_related('subject', 'teacher')
    
    # Get all payment periods that match the student's registered subjects and teachers
    from django.db.models import Q
    q_filter = Q()
    for enrollment in enrollments:
        q_filter |= Q(subject_id=enrollment.subject_id, teacher_id=enrollment.teacher_id)
        
    payment_periods = []
    if enrollments:
        payment_periods = list(
            PaymentPeriod.objects.filter(q_filter)
            .select_related('teacher', 'subject')
            .order_by('name', 'subject__name')
        )
    
    # Build report for this student
    records = []
    total_paid = 0
    
    for period in payment_periods:
        # Find payment
        payment = Payment.objects.filter(
            student=student,
            classroom=classroom,
            subject=period.subject,
            payment_period=period
        ).first()
        
        if payment:
            status = "Đã đóng"
            amount = payment.amount
            date = payment.payment_date
            payment_id = payment.id
            total_paid += amount
        else:
            status = "Chưa đóng"
            amount = 0
            date = None
            payment_id = None
            
        records.append({
            'period': period,
            'status': status,
            'amount': amount,
            'date': date,
            'payment_id': payment_id,
            'payment': payment,
        })
        
    return render(request, 'lms_manager/student_detail.html', {
        'student': student,
        'classroom': classroom,
        'enrollments': enrollments,
        'records': records,
        'total_paid': total_paid,
    })


# -------------------------------------------------------------
# PAYMENT PERIOD CRUD
# -------------------------------------------------------------
def payment_period_list(request):
    periods = PaymentPeriod.objects.all().order_by('name')
    return render(request, 'lms_manager/payment_period_list.html', {'periods': periods})

def payment_period_create(request):
    if request.method == 'POST':
        form = PaymentPeriodForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm đợt đóng tiền thành công!")
            return redirect('payment_period_list')
    else:
        initial_data = {}
        if 'teacher' in request.GET:
            initial_data['teacher'] = request.GET.get('teacher')
        if 'subject' in request.GET:
            initial_data['subject'] = request.GET.get('subject')
        form = PaymentPeriodForm(initial=initial_data)
    return render(request, 'lms_manager/form.html', {'form': form, 'title': 'Thêm đợt đóng tiền'})

def payment_period_update(request, pk):
    period = get_object_or_404(PaymentPeriod, pk=pk)
    if request.method == 'POST':
        form = PaymentPeriodForm(request.POST, instance=period)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật đợt đóng tiền thành công!")
            return redirect('payment_period_list')
    else:
        form = PaymentPeriodForm(instance=period)
    return render(request, 'lms_manager/form.html', {'form': form, 'title': 'Sửa đợt đóng tiền'})

def payment_period_delete(request, pk):
    period = get_object_or_404(PaymentPeriod, pk=pk)
    period.delete()
    messages.success(request, "Đã xóa đợt đóng tiền!")
    return redirect('payment_period_list')

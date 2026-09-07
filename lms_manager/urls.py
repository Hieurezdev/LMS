from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='home'),

    # Công nợ
    path('cong-no/', views.debt_dashboard, name='debt_dashboard'),
    path('bao-cao/doanh-thu-ngay/', views.daily_revenue_report, name='daily_revenue_report'),
    path('thu-ngan/cong-no/', views.cashier_due_list, name='cashier_due_list'),
    path('tai-khoan-cho-duyet/<int:user_id>/approve/', views.approve_cashier_account, name='approve_cashier_account'),
    path('tai-khoan-cho-duyet/<int:user_id>/reject/', views.reject_cashier_account, name='reject_cashier_account'),

    # ClassRoom
    path('classes/', views.classroom_list, name='classroom_list'),
    path('classes/export/', views.classroom_list_export, name='classroom_list_export'),
    path('classes/add/', views.classroom_create, name='classroom_add'),
    path('classes/delete-all/', views.classroom_delete_all, name='classroom_delete_all'),
    path('classes/<int:pk>/', views.classroom_detail, name='classroom_detail'),
    path('classes/<int:pk>/export/', views.classroom_export, name='classroom_export'),
    path('classes/<int:pk>/edit/', views.classroom_update, name='classroom_edit'),
    path('classes/<int:pk>/delete/', views.classroom_delete, name='classroom_delete'),
    
    # Subject
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/add/', views.subject_create, name='subject_add'),
    path('subjects/delete-all/', views.subject_delete_all, name='subject_delete_all'),
    path('subjects/<int:pk>/edit/', views.subject_update, name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.subject_delete, name='subject_delete'),
    
    # Teacher
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/<int:pk>/', views.teacher_detail, name='teacher_detail'),
    path('teachers/add/', views.teacher_create, name='teacher_add'),
    path('teachers/delete-all/', views.teacher_delete_all, name='teacher_delete_all'),
    path('teachers/<int:pk>/edit/', views.teacher_update, name='teacher_edit'),
    path('teachers/<int:pk>/delete/', views.teacher_delete, name='teacher_delete'),
    path('teachers/<int:pk>/add-classroom/', views.teacher_add_classroom, name='teacher_add_classroom'),
    path('teachers/<int:teacher_id>/classes/<int:classroom_id>/students/<int:student_id>/remove/', views.teacher_classroom_student_remove, name='teacher_classroom_student_remove'),
    path('teachers/<int:pk>/import-excel/', views.teacher_import_excel, name='teacher_import_excel'),
    path('teachers/import-template/', views.teacher_import_template, name='teacher_import_template'),
    path('teachers/<int:teacher_id>/classes/<int:classroom_id>/settlement/', views.teacher_class_settlement, name='teacher_class_settlement'),
    path('teacher-settlements/<int:pk>/export/', views.teacher_settlement_export, name='teacher_settlement_export'),
    
    # Student
    path('students/', views.student_list, name='student_list'),
    path('students/export/', views.student_list_export, name='student_list_export'),
    path('students/add/', views.student_create, name='student_add'),
    path('students/delete-all/', views.student_delete_all, name='student_delete_all'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    path('students/<int:pk>/export/', views.student_export, name='student_export'),
    path('students/<int:pk>/edit/', views.student_update, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('students/<int:student_id>/register/', views.student_register, name='student_register'),
    path('enrollments/<int:pk>/delete/', views.enrollment_delete, name='enrollment_delete'),
    
    # Payment
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/add/', views.payment_create, name='payment_add'),
    path('payments/delete-all/', views.payment_delete_all, name='payment_delete_all'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('payments/<int:pk>/edit/', views.payment_edit, name='payment_edit'),
    path('payments/<int:pk>/receipt/', views.payment_receipt, name='payment_receipt'),
    path('payments/batches/<int:pk>/receipt/', views.payment_batch_receipt, name='payment_batch_receipt'),
    
    # PaymentPeriod
    path('periods/', views.payment_period_list, name='payment_period_list'),
    path('periods/add/', views.payment_period_create, name='payment_period_add'),
    path('periods/delete-all/', views.payment_period_delete_all, name='payment_period_delete_all'),
    path('periods/<int:pk>/edit/', views.payment_period_update, name='payment_period_edit'),
    path('periods/<int:pk>/delete/', views.payment_period_delete, name='payment_period_delete'),
    
    # Class import excel
    path('classes/import-template/', views.classroom_import_template, name='classroom_import_template'),
    path('classes/<int:pk>/import-excel/', views.classroom_import_excel, name='classroom_import_excel'),
    
    # API for dynamic status toggle
    path('api/students/<int:pk>/toggle-period/<int:period_num>/', views.student_toggle_period, name='student_toggle_period'),
    
    # API for dynamic dropdowns
    path('api/students/<int:student_id>/subjects/', views.get_student_subjects, name='api_student_subjects'),
    path('api/students/<int:student_id>/teachers/', views.get_student_teachers, name='api_student_teachers'),
    path('api/students/<int:student_id>/unpaid-periods/', views.get_student_unpaid_periods, name='api_student_unpaid_periods'),
    path('api/students/<int:student_id>/payment-periods/', views.get_student_payment_periods, name='api_student_payment_periods'),
    path('api/students/<int:student_id>/period/<int:period_num>/receipt-url/', views.get_receipt_url, name='api_get_receipt_url'),
    path('api/payment-periods/filter/', views.filter_payment_periods, name='api_payment_periods_filter'),
    path('api/payment-periods/<int:period_id>/details/', views.get_period_details, name='api_payment_period_details'),
    path('api/subjects/<int:subject_id>/teachers/', views.get_subject_teachers, name='api_subject_teachers'),
    path('api/teachers/<int:teacher_id>/classes/', views.get_teacher_classrooms, name='api_teacher_classrooms'),
    path('api/teachers/<int:teacher_id>/subjects/', views.get_teacher_subjects, name='api_teacher_subjects'),
]

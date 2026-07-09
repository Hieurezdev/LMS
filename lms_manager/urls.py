from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='home'),

    # Công nợ
    path('cong-no/', views.debt_dashboard, name='debt_dashboard'),

    # ClassRoom
    path('classes/', views.classroom_list, name='classroom_list'),
    path('classes/add/', views.classroom_create, name='classroom_add'),
    path('classes/<int:pk>/', views.classroom_detail, name='classroom_detail'),
    path('classes/<int:pk>/edit/', views.classroom_update, name='classroom_edit'),
    path('classes/<int:pk>/delete/', views.classroom_delete, name='classroom_delete'),
    
    # Subject
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/add/', views.subject_create, name='subject_add'),
    path('subjects/<int:pk>/edit/', views.subject_update, name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.subject_delete, name='subject_delete'),
    
    # Teacher
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/<int:pk>/', views.teacher_detail, name='teacher_detail'),
    path('teachers/add/', views.teacher_create, name='teacher_add'),
    path('teachers/<int:pk>/edit/', views.teacher_update, name='teacher_edit'),
    path('teachers/<int:pk>/delete/', views.teacher_delete, name='teacher_delete'),
    path('teachers/<int:pk>/import-excel/', views.teacher_import_excel, name='teacher_import_excel'),
    path('teachers/import-template/', views.teacher_import_template, name='teacher_import_template'),
    
    # Student
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_create, name='student_add'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    path('students/<int:pk>/edit/', views.student_update, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('students/<int:student_id>/register/', views.student_register, name='student_register'),
    path('enrollments/<int:pk>/delete/', views.enrollment_delete, name='enrollment_delete'),
    
    # Payment
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/add/', views.payment_create, name='payment_add'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('payments/<int:pk>/receipt/', views.payment_receipt, name='payment_receipt'),
    
    # PaymentPeriod
    path('periods/', views.payment_period_list, name='payment_period_list'),
    path('periods/add/', views.payment_period_create, name='payment_period_add'),
    path('periods/<int:pk>/edit/', views.payment_period_update, name='payment_period_edit'),
    path('periods/<int:pk>/delete/', views.payment_period_delete, name='payment_period_delete'),
    
    # API for dynamic dropdowns
    path('api/students/<int:student_id>/subjects/', views.get_student_subjects, name='api_student_subjects'),
    path('api/students/<int:student_id>/payment-periods/', views.get_student_payment_periods, name='api_student_payment_periods'),
    path('api/payment-periods/filter/', views.filter_payment_periods, name='api_payment_periods_filter'),
    path('api/payment-periods/<int:period_id>/details/', views.get_period_details, name='api_payment_period_details'),
    path('api/subjects/<int:subject_id>/teachers/', views.get_subject_teachers, name='api_subject_teachers'),
]

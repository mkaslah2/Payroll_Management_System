from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    # ------------------ Public Pages ------------------
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # ------------------ Dashboards ------------------
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('admin/dashboard/', views.org_admin_dashboard, name='org_admin_dashboard'),
    path('hr/dashboard/', views.hr_dashboard, name='hr_dashboard'),
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),

    # ------------------ Department Pages ------------------
    path('department/add/', views.add_department_page, name='add_department_page'),
    path('department/view/<int:dept_id>/', views.view_department, name='view_department'),

    # ------------------ API Endpoints ------------------
    # Department CRUD
    path('api/department/add/', views.add_department, name='api_add_department'),
    path('api/department/<uuid:org_id>/', views.get_departments, name='api_get_departments'),

    # FIXED HERE ↓↓↓
    path('api/department/edit/<int:dept_id>/', views.edit_department, name='api_edit_department'),

    # Dashboard summary
    path('api/dashboard/summary/<uuid:org_id>/', views.get_dashboard_summary, name='api_dashboard_summary'),

    # Personnel CRUD
    path('api/personnel/add/<str:role>/', views.add_personnel, name='api_add_personnel'),
    path('api/personnel/<uuid:org_id>/<str:role>/', views.get_personnel, name='api_get_personnel'),
    path('api/personnel/view/<int:user_id>/', views.view_personnel, name='api_view_personnel'),
    path('api/personnel/edit/<int:user_id>/', views.edit_personnel_form, name='api_edit_personnel_form'),
    path('api/personnel/delete/<int:user_id>/', views.delete_personnel, name='api_delete_personnel'),

    # Notifications API
    path('api/notification/send/', views.send_notification, name='api_send_notification'),
    path('api/notification/list/', views.list_notifications, name='api_list_notifications'),

    # Attendance APIs
    path('api/attendance/mark/', views.mark_attendance, name='api_mark_attendance'),
    path('api/attendance/hr/<uuid:org_id>/', views.get_hr_attendance, name='api_get_hr_attendance'),
    path('api/attendance/verify/<int:att_id>/', views.verify_attendance, name='api_verify_attendance'),

    # HR & Employee Leave
    path('api/hr/leave/request/', views.hr_leave_request, name='hr_leave_request'),
    path('api/hr/leave/list/', views.hr_leave_list, name='hr_leave_list'),

    # Admin Leave
    path('api/leave/list/<uuid:org_id>/', views.admin_leave_list, name='admin_leave_list'),
    path('api/leave/action/<int:leave_id>/', views.admin_leave_action, name='admin_leave_action'),

    # Employee attendance
    path('api/attendance/employee/list/', views.employee_attendance_list, name='api_employee_attendance_list'),

    # HR managing employee attendance
    path('api/attendance/employee/hr/list/', views.hr_employee_attendance_list, name='api_hr_employee_attendance_list'),
    path('api/attendance/employee/hr/verify/<int:att_id>/', views.hr_verify_employee_attendance, name='api_hr_verify_employee_attendance'),

    # Employee leave
    path("api/employee/leave/request/", views.employee_leave_request),
    path("api/employee/leave/list/", views.employee_leave_list),

    # HR handles employee leave
    path("api/hr/employee/leave/list/", views.hr_employee_leave_list),
    path("api/hr/employee/leave/action/<int:leave_id>/", views.hr_employee_leave_action),
    path("api/hr/department/employees/", views.hr_department_employees),

    # Payslips
    path("api/payslip/generate/", views.generate_payslips, name="generate_payslips"),
    path("api/payslip/list/", views.list_payslips, name="list_payslips"),
    path("api/hr/payslips/", views.hr_payslips),
    path("api/hr/payslip/generate/", views.hr_generate_payslip),
    path("api/hr/payslip/list/", views.hr_employee_payslips),
    path("api/hr/employees/", views.hr_employee_list),
    path("api/employee/payslips/", views.employee_payslips, name="employee_payslips"),

    path('api/department/delete/<int:dept_id>/', views.delete_department, name='api_delete_department'),
    path("payslip/download/<int:payslip_id>/", views.download_payslip_pdf, name="download_payslip_pdf"),

    # FIXED HERE ↓↓↓
    path('department/edit/<int:dept_id>/', views.edit_department_page, name='edit_department_page'),
]

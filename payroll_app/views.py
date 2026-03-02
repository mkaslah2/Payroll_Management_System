import json
import decimal
from decimal import Decimal

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .forms import (
    OrganizationRegistrationForm,
    OrgAdminCreationForm,
    CustomLoginForm,
    NotificationForm,
)
from .models import (
    User,
    Organization,
    Department,
    HR,
    Employee,
    Notification,
    Attendance,
    LeaveRequest,
    Payslip
)


def safe_decimal_str(value):
    try:
        return str(decimal.Decimal(value))
    except (decimal.InvalidOperation, TypeError, ValueError):
        return "0.00"


# ------------------ Public Views ------------------


def index(request):
    """Landing page view."""
    return render(request, 'payroll_app/index.html')

def signup(request):
    """Handles Organization and OrgAdmin registration."""

    if request.method == 'POST':
        org_form = OrganizationRegistrationForm(request.POST)
        admin_form = OrgAdminCreationForm(request.POST)

        # Validate both forms
        if org_form.is_valid() and admin_form.is_valid():
            try:
                with transaction.atomic():

                    # Create Organization
                    org_data = org_form.cleaned_data
                    organization = Organization.objects.create(
                        name=org_data['name'],
                        email=org_data['email'],
                        address=org_data.get('address', ''),
                    )

                    # Create Admin User
                    admin_data = admin_form.cleaned_data
                    admin_user = User.objects.create_user(
                        email=admin_data['email'],
                        password=admin_data['password1'],  # Use password1
                        first_name=admin_data['first_name'],
                        last_name=admin_data['last_name'],
                        role='OrgAdmin',
                        organization=organization,
                    )

                    # Authenticate & Login
                    user = authenticate(
                        request,
                        email=admin_user.email,
                        password=admin_data['password1'],
                    )

                    if user:
                        login(request, user)
                        return redirect('org_admin_dashboard')

                    return redirect('login')

            except IntegrityError:
                org_form.add_error(None, "Registration failed due to a duplicate entry.")

        # If form invalid → re-render with errors
        context = {'org_form': org_form, 'admin_form': admin_form}
        return render(request, 'payroll_app/signup.html', context)

    else:
        # GET request → Empty forms
        org_form = OrganizationRegistrationForm()
        admin_form = OrgAdminCreationForm()
        context = {'org_form': org_form, 'admin_form': admin_form}
        return render(request, 'payroll_app/signup.html', context)

def login_view(request):
    """Handles role-based login with Organization ID."""
    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)

        org_id = request.POST.get('organization_id')
        user_id = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')

        try:
            organization = Organization.objects.get(id=org_id)
        except (Organization.DoesNotExist, ValueError):
            return render(
                request,
                'payroll_app/login.html',
                {'form': form, 'error': 'Invalid Organization ID.'},
            )

        if organization.status != 'Verified':
            return render(
                request,
                'payroll_app/login.html',
                {
                    'form': form,
                    'error': 'Organization pending verification by system admin.',
                },
            )

        user = authenticate(request, email=user_id, password=password)

        if user is not None:
            if user.organization != organization:
                return render(
                    request,
                    'payroll_app/login.html',
                    {
                        'form': form,
                        'error': 'User does not belong to this Organization.',
                    },
                )

            if user.role != role:
                return render(
                    request,
                    'payroll_app/login.html',
                    {
                        'form': form,
                        'error': f'Login successful, but role mismatch. Expected {role}.',
                    },
                )

            login(request, user)
            return redirect('dashboard_redirect')
        else:
            return render(
                request,
                'payroll_app/login.html',
                {'form': form, 'error': 'Invalid credentials or User ID.'},
            )
    else:
        form = CustomLoginForm()

    return render(request, 'payroll_app/login.html', {'form': form})


@login_required
def dashboard_redirect(request):
    """Redirects authenticated users to the correct dashboard based on role."""
    if request.user.is_org_admin:
        return redirect('org_admin_dashboard')
    elif request.user.is_hr:
        return redirect('hr_dashboard')
    elif request.user.is_employee:
        return redirect('employee_dashboard')
    else:
        return redirect('index')


# ------------------ Dashboards ------------------


@login_required
def org_admin_dashboard(request):
    """Organization Admin Dashboard."""
    if not request.user.is_org_admin:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            message = form.cleaned_data['message']
            recipient_type = form.cleaned_data['recipient_type']
            org = request.user.organization

            Notification.objects.create(
                organization=org,
                recipient_type=recipient_type,
                title=title,
                message=message,
                sent_by=request.user,
                sent_at=timezone.now(),
            )
            return redirect('org_admin_dashboard')
    else:
        form = NotificationForm()

    context = {
        'org_id': str(request.user.organization.id),
        'user': request.user,
        'notification_form': form,
    }
    return render(request, 'payroll_app/orgadmindashboard.html', context)


@login_required
def hr_dashboard(request):
    """HR Personnel Dashboard."""
    if not request.user.is_hr:
        return redirect('dashboard_redirect')

    org_id = str(request.user.organization.id)
    notifications = Notification.objects.filter(
        organization__id=org_id
    ).filter(
        Q(recipient_type='All') |
        Q(recipient_type='HR') |
        Q(target_user=request.user)
    ).order_by('-sent_at')

    context = {
        'org_id': org_id,
        'user': request.user,
        'notifications': notifications,
    }
    return render(request, 'payroll_app/hrmanagement.html', context)


@login_required
def employee_dashboard(request):
    """Regular Employee Dashboard."""
    if not request.user.is_employee:
        return redirect('dashboard_redirect')

    org_id = str(request.user.organization.id)
    notifications = Notification.objects.filter(
        organization__id=org_id
    ).filter(
        Q(recipient_type='All') |
        Q(recipient_type='Employee') |
        Q(target_user=request.user)
    ).order_by('-sent_at')

    context = {
        'org_id': org_id,
        'user': request.user,
        'notifications': notifications,
    }
    return render(request, 'payroll_app/employeedashboard.html', context)


# ------------------ Department Views & APIs ------------------


@login_required
def add_department_page(request):
    if not request.user.is_org_admin:
        return redirect('dashboard_redirect')
    return render(request, 'payroll_app/add_department.html')


@login_required
def add_department(request):
    """API to handle adding a new department via AJAX from the dashboard."""
    if not request.user.is_org_admin:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    try:
        data = json.loads(request.body)
        dept_name = data.get('name')
        dept_head = data.get('head')

        if not dept_name or not dept_head:
            return JsonResponse({'success': False, 'message': 'Missing fields.'}, status=400)

        department = Department.objects.create(
            organization=request.user.organization,
            name=dept_name,
            head=dept_head,
        )

        return JsonResponse(
            {
                'success': True,
                'id': department.id,
                'name': department.name,
            },
            status=201,
        )

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def get_departments(request, org_id):
    """API to get all departments for the current organization."""
    if request.user.organization.id != org_id:
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)

    departments = Department.objects.filter(organization__id=org_id)

    data = []
    for dept in departments:
        data.append({
            'id': str(dept.id),
            'name': dept.name,
            'head': dept.head,
            'employees': dept.employee_count,
        })

    return JsonResponse({'success': True, 'departments': data})


@login_required
def edit_department(request, dept_id):
    if not request.user.is_org_admin:
        return redirect('dashboard_redirect')

    department = get_object_or_404(
        Department,
        id=dept_id,
        organization=request.user.organization,
    )
    if request.method == 'POST':
        name = request.POST.get('name')
        head = request.POST.get('head')
        department.name = name
        department.head = head
        department.save()
        return redirect('org_admin_dashboard')
    else:
        return render(
            request,
            "payroll_app/edit_department.html",
            {"department": department},
        )


@login_required
def view_department(request, dept_id):
    if not request.user.is_org_admin:
        return redirect('dashboard_redirect')

    department = get_object_or_404(
        Department,
        id=dept_id,
        organization=request.user.organization,
    )

    employees = list(HR.objects.filter(department=department)) + list(
        Employee.objects.filter(department=department)
    )

    context = {
        "department": department,
        "employees": employees,
    }
    return render(request, "payroll_app/view_department.html", context)


# ------------------ Personnel Views & APIs ------------------


@login_required
def add_personnel(request, role):
    if not request.user.is_org_admin:
        return redirect('dashboard_redirect')

    if role == 'hr':
        role = 'HR'
    elif role == 'employee':
        role = 'Employee'
    else:
        return render(
            request,
            'payroll_app/add_personnel.html',
            {'role': role, 'error': 'Invalid role.'},
        )

    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            department_id = request.POST.get('department')
            position = request.POST.get('position')
            salary_str = request.POST.get('salary')
            password = request.POST.get('password')

            if not all([first_name, last_name, email, department_id, position, salary_str, password]):
                return render(
                    request,
                    'payroll_app/add_personnel.html',
                    {'role': role, 'error': 'All fields are required.'},
                )

            department = Department.objects.get(
                id=department_id,
                organization=request.user.organization,
            )

            user = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                role=role,
                organization=request.user.organization,
            )
            user.set_password(password)
            user.save()

            salary = Decimal(salary_str)

            if role == 'HR':
                HR.objects.create(
                    user=user,
                    organization=user.organization,
                    department=department,
                    position=position,
                    salary=salary,
                )
            elif role == 'Employee':
                Employee.objects.create(
                    user=user,
                    organization=user.organization,
                    department=department,
                    position=position,
                    salary=salary,
                )

            return redirect('org_admin_dashboard')
        except Exception as e:
            return render(
                request,
                'payroll_app/add_personnel.html',
                {'role': role, 'error': str(e)},
            )
    else:
        departments = Department.objects.filter(organization=request.user.organization)
        return render(
            request,
            'payroll_app/add_personnel.html',
            {
                'role': role,
                'departments': departments,
                'user': request.user,
            },
        )


@login_required
def get_personnel(request, org_id, role):
    if request.user.organization.id != org_id:
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)

    if role == 'hr':
        personnel = HR.objects.filter(
            organization__id=org_id
        ).select_related('user', 'department')
    elif role == 'employee':
        personnel = Employee.objects.filter(
            organization__id=org_id
        ).select_related('user', 'department')
    else:
        return JsonResponse({'success': False, 'message': 'Invalid role.'}, status=400)

    data = []
    for p in personnel:
        salary_value = safe_decimal_str(p.salary)
        data.append({
            'id': p.user.id,
            'first_name': p.user.first_name,
            'last_name': p.user.last_name,
            'email': p.user.email,
            'phone': p.user.phone or '',
            'department': p.department.name if p.department else '',
            'position': p.position,
            'salary': salary_value,
        })
    return JsonResponse({'success': True, 'personnel': data})


@login_required
def view_personnel(request, user_id):
    user_obj = get_object_or_404(
        User,
        id=user_id,
        organization=request.user.organization,
    )
    if user_obj.role == 'HR':
        personnel = get_object_or_404(HR, user=user_obj)
    elif user_obj.role == 'Employee':
        personnel = get_object_or_404(Employee, user=user_obj)
    else:
        return redirect('dashboard_redirect')

    context = {'personnel': personnel, 'user_obj': user_obj}
    return render(request, 'payroll_app/view_personnel.html', context)


@login_required
def edit_personnel_form(request, user_id):
    user_obj = get_object_or_404(
        User,
        id=user_id,
        organization=request.user.organization,
    )
    if user_obj.role == 'HR':
        personnel = get_object_or_404(HR, user=user_obj)
    elif user_obj.role == 'Employee':
        personnel = get_object_or_404(Employee, user=user_obj)
    else:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        department_id = request.POST.get('department')
        position = request.POST.get('position')
        salary_str = request.POST.get('salary')
        password = request.POST.get('password')

        department = get_object_or_404(
            Department,
            id=department_id,
            organization=request.user.organization,
        )

        user_obj.first_name = first_name
        user_obj.last_name = last_name
        user_obj.email = email
        user_obj.phone = phone
        if password:
            user_obj.set_password(password)
        user_obj.save()

        salary = Decimal(salary_str)

        personnel.department = department
        personnel.position = position
        personnel.salary = salary
        personnel.save()

        return redirect('org_admin_dashboard')
    else:
        departments = Department.objects.filter(organization=request.user.organization)
        context = {
            'personnel': personnel,
            'user_obj': user_obj,
            'departments': departments,
        }
        return render(request, 'payroll_app/edit_personnel.html', context)


@login_required
def delete_personnel(request, user_id):
    if not request.user.is_org_admin:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    user_obj = get_object_or_404(
        User,
        id=user_id,
        organization=request.user.organization,
    )
    user_obj.delete()
    return JsonResponse({'success': True})


# ------------------ Dashboard Summary API ------------------


@login_required
def get_dashboard_summary(request, org_id):
    if request.user.organization.id != org_id:
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)
    departments_count = Department.objects.filter(organization__id=org_id).count()
    employees_count = Employee.objects.filter(organization__id=org_id).count()
    hrs_count = HR.objects.filter(organization__id=org_id).count()
    departments = Department.objects.filter(organization__id=org_id)
    chart_data = {
        'departments': [
            {'name': dept.name, 'employee_count': dept.employee_count}
            for dept in departments
        ]
    }
    return JsonResponse({
        'success': True,
        'departments_count': departments_count,
        'employees_count': employees_count,
        'hrs_count': hrs_count,
        'chart_data': chart_data,
    })


# ------------------ Notifications ------------------


@login_required
@require_http_methods(["POST"])
def send_notification(request):
    try:
        data = json.loads(request.body)
        title = data.get('title')
        message = data.get('message')
        recipient_type = data.get('recipient_type')

        if not all([title, message, recipient_type]):
            return JsonResponse({'success': False, 'message': 'Missing fields.'}, status=400)

        org = request.user.organization

        notif = Notification.objects.create(
            organization=org,
            recipient_type=recipient_type if recipient_type != "Both" else "All",
            title=title,
            message=message,
            sent_by=request.user,
            sent_at=timezone.now(),
        )

        return JsonResponse({
            'success': True,
            'notification': {
                'id': notif.id,
                'recipient_type': notif.recipient_type,
                'title': notif.title,
                'message': notif.message,
                'sent_by': notif.sent_by.first_name,
                'sent_at': notif.sent_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def list_notifications(request):
    org = request.user.organization
    role = request.user.role

    if role == "OrgAdmin":
        qs = Notification.objects.filter(
        organization=org,
        sent_by=request.user
    )
    elif role == "HR":
        qs = Notification.objects.filter(
            organization=org
        ).filter(
            Q(recipient_type="All") |
            Q(recipient_type="HR") |
            Q(target_user=request.user)
        )
    elif role == "Employee":
        qs = Notification.objects.filter(
            organization=org
        ).filter(
            Q(recipient_type="All") |
            Q(recipient_type="Employee") |
            Q(target_user=request.user)
        )
    else:
        qs = Notification.objects.none()

    data = []
    for n in qs.order_by("-sent_at"):
        data.append({
            "id": n.id,
            "recipient_type": n.recipient_type,
            "title": n.title,
            "message": n.message,
            "sent_by": n.sent_by.first_name if n.sent_by else "Unknown",
            "sent_at": n.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return JsonResponse({"success": True, "notifications": data})


# ------------------ Attendance ------------------


@csrf_exempt
@login_required
def mark_attendance(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid method"})

    user = request.user
    data = json.loads(request.body.decode("utf-8"))
    status = data.get("status")

    if status not in ["Present", "Absent", "Leave"]:
        return JsonResponse({"success": False, "message": "Invalid status"})

    today = timezone.now().date()

    # Determine department based on role
    department = None
    if user.role == "HR" and hasattr(user, 'hr'):
        department = user.hr.department
    elif user.role == "Employee" and hasattr(user, 'employee'):
        department = user.employee.department

    att, created = Attendance.objects.get_or_create(
        user=user,
        date=today,
        defaults={
            "organization": user.organization,
            "department": department,
            "status": status,
            "verification": "Pending",
        },
    )

    if not created:
        att.status = status
        att.verification = "Pending"
        att.department = department
        att.save()

    return JsonResponse({"success": True, "message": "Attendance marked successfully"})


@login_required
def get_hr_attendance(request, org_id):
    """
    For OrgAdmin: see all HR attendance.
    For HR: see own attendance (used by HR calendar).
    """
    if request.user.organization.id != org_id:
        return JsonResponse({'success': False, 'message': 'Access denied.'}, status=403)

    if request.user.is_org_admin:
        qs = Attendance.objects.filter(
            organization__id=org_id,
            user__role='HR',
        ).select_related("user", "department").order_by("-date")
    elif request.user.is_hr:
        qs = Attendance.objects.filter(
            organization__id=org_id,
            user=request.user,
        ).select_related("user", "department").order_by("-date")
    else:
        return JsonResponse({'success': False, 'message': 'Only OrgAdmin/HR allowed.'}, status=403)

    data = [{
        "id": a.id,
        "hr_name": a.user.first_name,
        "department": a.department.name if a.department else "",
        "date": a.date.strftime("%Y-%m-%d"),
        "status": a.status,
        "verification": a.verification,
    } for a in qs]

    return JsonResponse({"success": True, "attendance": data})


@login_required
def verify_attendance(request, att_id):
    if not request.user.is_org_admin:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

    data = json.loads(request.body)
    action = data.get("action")

    attendance = get_object_or_404(Attendance, id=att_id)

    if action == "Approve":
        attendance.verification = "Verified"
    elif action == "Reject":
        attendance.verification = "Rejected"
    else:
        return JsonResponse({'success': False, 'message': 'Invalid action.'}, status=400)

    attendance.save()

    return JsonResponse({"success": True, "message": f"Attendance {attendance.verification}"})


@login_required
def employee_attendance_list(request):
    user = request.user

    records = Attendance.objects.filter(user=user).order_by("-date")

    data = []
    for r in records:
        data.append({
            "date": r.date.strftime("%Y-%m-%d"),
            "status": r.status,
            "verification": r.verification,
        })

    return JsonResponse({"success": True, "records": data})


@login_required
def hr_employee_attendance_list(request):
    """HR can see attendance of Employees only in their department."""
    if not request.user.is_hr:
        return JsonResponse({"success": False, "message": "Only HR allowed."}, status=403)

    try:
        hr = HR.objects.get(user=request.user)
    except HR.DoesNotExist:
        return JsonResponse({"success": False, "message": "HR profile not found."}, status=400)

    dept = hr.department

    records = Attendance.objects.filter(
        organization=request.user.organization,
        user__role="Employee",
        department=dept
    ).select_related("user", "department").order_by("-date")

    data = []
    for r in records:
        data.append({
            "id": r.id,
            "employee_name": f"{r.user.first_name} {r.user.last_name}",
            "department": r.department.name if r.department else "",
            "date": r.date.strftime("%Y-%m-%d"),
            "status": r.status,
            "verification": r.verification,
        })

    return JsonResponse({"success": True, "records": data})


@csrf_exempt
@login_required
def hr_verify_employee_attendance(request, att_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request"})

    if not request.user.is_hr:
        return JsonResponse({"success": False, "message": "Only HR allowed."}, status=403)

    try:
        hr = HR.objects.get(user=request.user)
    except HR.DoesNotExist:
        return JsonResponse({"success": False, "message": "HR profile not found."}, status=400)

    data = json.loads(request.body.decode("utf-8"))
    action = data.get("action")

    if action not in ["Approve", "Reject"]:
        return JsonResponse({"success": False, "message": "Invalid action"})

    try:
        attendance = Attendance.objects.select_related("user", "department").get(id=att_id)
    except Attendance.DoesNotExist:
        return JsonResponse({"success": False, "message": "Attendance not found"})

    # Ensure this is an Employee in HR's department
    if attendance.user.role != "Employee" or attendance.department != hr.department:
        return JsonResponse({"success": False, "message": "Not allowed"}, status=403)

    attendance.verification = "Verified" if action == "Approve" else "Rejected"
    attendance.save()

    return JsonResponse({"success": True, "message": f"Attendance {attendance.verification}"})


# ------------------ Leave System ------------------


@login_required
def hr_leave_request(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "POST required"}, status=405)

    data = json.loads(request.body)

    leave_type = data.get("leave_type")
    start = data.get("start_date")
    end = data.get("end_date")
    reason = data.get("reason")

    if not leave_type or not start or not reason:
        return JsonResponse({"success": False, "message": "All fields are required."})

    LeaveRequest.objects.create(
        user=request.user,
        leave_type=leave_type,
        start_date=start,
        end_date=end,
        reason=reason,
        status="Pending",
    )

    return JsonResponse({"success": True, "message": "Leave request submitted successfully."})


@login_required
def hr_leave_list(request):
    leaves = LeaveRequest.objects.filter(user=request.user).order_by("-id")

    data = []
    for l in leaves:
        data.append({
            "id": l.id,
            "leave_type": l.leave_type,
            "start": str(l.start_date),
            "end": str(l.end_date),
            "reason": l.reason,
            "status": l.status,
        })

    return JsonResponse({"success": True, "leaves": data})

@login_required
def admin_leave_list(request, org_id):
    if not request.user.is_org_admin or request.user.organization.id != org_id:
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)

    # ✅ Only HR leaves go to Org Admin dashboard
    leaves = LeaveRequest.objects.filter(
        user__organization=request.user.organization,
        user__role="HR"
    ).select_related("user").order_by("-submitted_at")

    data = []
    for l in leaves:
        if l.user.role == "HR" and hasattr(l.user, 'hr') and l.user.hr.department:
            dept_name = l.user.hr.department.name
        elif l.user.role == "Employee" and hasattr(l.user, 'employee') and l.user.employee.department:
            dept_name = l.user.employee.department.name
        else:
            dept_name = "—"

        data.append({
            "id": l.id,
            "name": f"{l.user.first_name} {l.user.last_name}",
            "role": l.user.role,
            "department": dept_name,
            "leave_type": l.leave_type,
            "start": str(l.start_date),
            "end": str(l.end_date),
            "status": l.status,
        })

    return JsonResponse({"success": True, "leaves": data})


@login_required
def admin_leave_action(request, leave_id):
    if not request.user.is_org_admin:
        return JsonResponse({"success": False, "message": "Forbidden"}, status=403)

    data = json.loads(request.body)
    action = data.get("action")

    leave = get_object_or_404(LeaveRequest, id=leave_id)

    if action == "Approve":
        leave.status = "Approved"
    elif action == "Reject":
        leave.status = "Rejected"
    else:
        return JsonResponse({"success": False, "message": "Invalid action."}, status=400)

    leave.save()

    return JsonResponse({"success": True, "message": f"Leave {leave.status}!"})


@login_required
def employee_leave_request(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "POST required"}, status=400)

    if not request.user.is_employee:
        return JsonResponse({"success": False, "message": "Only employees can submit leave."}, status=403)

    data = json.loads(request.body)
    leave_type = data.get("leave_type")
    start = data.get("start_date")
    end = data.get("end_date")
    reason = data.get("reason")

    if not leave_type or not start or not reason:
        return JsonResponse({"success": False, "message": "Missing required fields."}, status=400)

    LeaveRequest.objects.create(
        user=request.user,
        leave_type=leave_type,
        start_date=start,
        end_date=end,
        reason=reason,
        status="Pending"
    )

    return JsonResponse({"success": True, "message": "Leave request sent to your HR."})


@login_required
def hr_employee_leave_list(request):
    if not request.user.is_hr:
        return JsonResponse({"success": False, "message": "Only HR allowed."}, status=403)

    try:
        hr = HR.objects.get(user=request.user)
    except HR.DoesNotExist:
        return JsonResponse({"success": False, "message": "HR profile not found."}, status=400)

    dept = hr.department

    leaves = LeaveRequest.objects.filter(
        user__role="Employee",
        user__employee__department=dept
    ).select_related("user").order_by("-id")


    data = []
    for l in leaves:
        data.append({
            "id": l.id,
            "employee": f"{l.user.first_name} {l.user.last_name}",
            "leave_type": l.leave_type,
            "start": str(l.start_date),
            "end": str(l.end_date or ""),
            "reason": l.reason,
            "status": l.status,
        })

    return JsonResponse({"success": True, "leaves": data})


@login_required
def hr_employee_leave_action(request, leave_id):
    if not request.user.is_hr:
        return JsonResponse({"success": False, "message": "Only HR allowed."}, status=403)

    try:
        hr = HR.objects.get(user=request.user)
    except HR.DoesNotExist:
        return JsonResponse({"success": False, "message": "HR profile not found."}, status=400)

    hr_dept = hr.department

    try:
        leave = LeaveRequest.objects.select_related("user").get(id=leave_id)
    except LeaveRequest.DoesNotExist:
        return JsonResponse({"success": False, "message": "Leave not found"}, status=404)

    # Ensure employee belongs to HR’s department
    if leave.user.role != "Employee" or not hasattr(leave.user, 'employee') or leave.user.employee.department != hr_dept:
        return JsonResponse({"success": False, "message": "Not your department employee"}, status=403)

    data = json.loads(request.body)
    action = data.get("action")

    if action == "Approve":
        leave.status = "Approved"
    elif action == "Reject":
        leave.status = "Rejected"
    else:
        return JsonResponse({"success": False, "message": "Invalid action"}, status=400)

    # NOTE: LeaveRequest model has no reviewed_by field; do not set it.
    leave.save()

    return JsonResponse({"success": True, "message": f"Leave {leave.status}"})


@login_required
def employee_leave_list(request):
    records = LeaveRequest.objects.filter(
        user=request.user
    ).order_by("-id")


    data = [{
        "id": l.id,
        "leave_type": l.leave_type,
        "start": str(l.start_date),
        "end": str(l.end_date),
        "reason": l.reason,
        "status": l.status,
    } for l in records]

    return JsonResponse({"success": True, "leaves": data})


@login_required
def hr_department_employees(request):
    """Return employees only in HR’s own department."""
    if not request.user.is_hr:
        return JsonResponse({"success": False, "message": "Only HR allowed"}, status=403)

    try:
        hr = HR.objects.get(user=request.user)
    except HR.DoesNotExist:
        return JsonResponse({"success": False, "message": "HR profile not found"}, status=404)

    dept = hr.department

    employees = Employee.objects.filter(
        department=dept,
        organization=request.user.organization
    ).select_related("user")

    data = []
    for e in employees:
        data.append({
            "id": e.user.id,
            "name": f"{e.user.first_name} {e.user.last_name}",
            "position": e.position,
            "salary": str(e.salary),
        })

    return JsonResponse({"success": True, "employees": data})

@login_required
def generate_payslips(request):
    if not request.user.is_org_admin:
        return JsonResponse({'success': False, 'message': 'Only Org Admin allowed'}, status=403)

    org = request.user.organization

    # Determine which month to calculate
    today = timezone.now()
    month_start = today.replace(day=1)
    month_end = today

    hrs = HR.objects.filter(organization=org).select_related("user")
    generated = []

    for hr in hrs:
        user = hr.user

        # Fetch attendance in this month
        attendance = Attendance.objects.filter(
            user=user,
            date__gte=month_start,
            date__lte=month_end
        )

        present_days = attendance.filter(status="Present").count()
        leave_days = attendance.filter(status="Leave").count()
        absent_days = attendance.filter(status="Absent").count()

        # Payable days = Present + Leave
        payable_days = present_days + leave_days

        # Days in month (for computation)
        import calendar
        total_days = calendar.monthrange(today.year, today.month)[1]

        # Salary calculations
        daily_salary = hr.salary / Decimal(total_days)
        gross_salary = daily_salary * payable_days
        deductions = daily_salary * absent_days
        net_salary = gross_salary  # Or subtract deductions if needed

        # Prevent duplicate payslip for the same month
        payslip, created = Payslip.objects.get_or_create(
            user=user,
            month=month_start,
            defaults={
                'gross_salary': gross_salary,
                'deductions': deductions,
                'net_salary': net_salary,
                'generated_by': request.user,
            }
        )

        generated.append({
            "hr": f"{user.first_name} {user.last_name}",
            "present_days": present_days,
            "leave_days": leave_days,
            "absent_days": absent_days,
            "gross": str(gross_salary),
            "deductions": str(deductions),
            "net": str(net_salary),
            "created": created,
        })

    return JsonResponse({
        'success': True,
        'message': 'Payslips generated successfully',
        'generated': generated
    })




@login_required
def list_payslips(request):
    if not request.user.is_org_admin:
        return JsonResponse({'success': False, 'message': 'Only Org Admin allowed'}, status=403)

    slips = Payslip.objects.filter(
        generated_by=request.user,
        user__role="HR"
    ).select_related("user").order_by("-generated_at")

    data = []
    for p in slips:
        data.append({
            "id": p.id,
            "hr": f"{p.user.first_name} {p.user.last_name}",
            "month": p.month.strftime("%Y-%m"),
            "gross": str(p.gross_salary),
            "deductions": str(p.deductions),
            "net": str(p.net_salary),
            "generated_at": p.generated_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse({"success": True, "payslips": data})



@login_required
def hr_payslips(request):
    if not request.user.is_hr:
        return JsonResponse({'success': False, 'message': 'Only HR allowed'}, status=403)

    slips = Payslip.objects.filter(
        user=request.user
    ).order_by("-month")

    data = []
    for p in slips:
        data.append({
            "id": p.id,
            "month": p.month.strftime("%Y-%m"),
            "gross": str(p.gross_salary),
            "deductions": str(p.deductions),
            "net": str(p.net_salary),
            "generated_at": p.generated_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse({"success": True, "payslips": data})


@login_required
def hr_generate_payslip(request):
    if not request.user.is_hr:
        return JsonResponse({'success': False, 'message': 'Only HR allowed'}, status=403)

    data = json.loads(request.body)
    employee_id = data.get("employee_id")  # optional

    hr = HR.objects.get(user=request.user)
    dept = hr.department

    # Which employees HR can generate?
    if employee_id:
        employees = Employee.objects.filter(user__id=employee_id, department=dept)
    else:
        # Generate for all employees in department
        employees = Employee.objects.filter(department=dept)

    today = timezone.now()
    month_start = today.replace(day=1)

    import calendar
    total_days = calendar.monthrange(today.year, today.month)[1]

    generated = []

    for emp in employees:
        user = emp.user

        attendance = Attendance.objects.filter(
            user=user,
            date__gte=month_start,
            date__lte=today
        )

        present_days = attendance.filter(status="Present").count()
        leave_days = attendance.filter(status="Leave").count()
        absent_days = attendance.filter(status="Absent").count()

        payable_days = present_days + leave_days

        daily_salary = emp.salary / Decimal(total_days)
        gross = daily_salary * payable_days
        deductions = daily_salary * absent_days
        net = gross

        payslip, created = Payslip.objects.get_or_create(
            user=user,
            month=month_start,
            defaults={
                "gross_salary": gross,
                "deductions": deductions,
                "net_salary": net,
                "generated_by": request.user
            }
        )

        generated.append({
            "employee": f"{user.first_name} {user.last_name}",
            "gross": str(gross),
            "deductions": str(deductions),
            "net": str(net),
            "created": created
        })

    return JsonResponse({"success": True, "generated": generated})

@login_required
def hr_employee_payslips(request):
    if not request.user.is_hr:
        return JsonResponse({'success': False, 'message': 'Only HR allowed'}, status=403)

    hr = HR.objects.get(user=request.user)
    dept = hr.department

    slips = Payslip.objects.filter(
        user__employee__department=dept
    ).select_related("user").order_by("-generated_at")

    data = []
    for p in slips:
        data.append({
            "id": p.id,
            "employee": f"{p.user.first_name} {p.user.last_name}",
            "month": p.month.strftime("%Y-%m"),
            "gross": str(p.gross_salary),
            "deductions": str(p.deductions),
            "net": str(p.net_salary),
        })

    return JsonResponse({"success": True, "payslips": data})



@login_required
def employee_payslips(request):
    if not request.user.is_employee:
        return JsonResponse({'success': False, 'message': 'Only employees allowed'}, status=403)

    slips = Payslip.objects.filter(user=request.user).order_by("-month")

    data = []
    for p in slips:
        data.append({
            "id": p.id,
            "month": p.month.strftime("%Y-%m"),
            "gross": str(p.gross_salary),
            "deductions": str(p.deductions),
            "net": str(p.net_salary),
            "generated_at": p.generated_at.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse({"success": True, "payslips": data})


@login_required
def hr_employee_list(request):
    if not request.user.is_hr:
        return JsonResponse({"success": False, "message": "Only HR allowed"}, status=403)

    try:
        hr = HR.objects.get(user=request.user)
    except HR.DoesNotExist:
        return JsonResponse({"success": False, "message": "HR profile not found"}, status=400)

    dept = hr.department

    employees = Employee.objects.filter(department=dept).select_related("user")

    data = []
    for emp in employees:
        data.append({
            "id": emp.user.id,
            "first_name": emp.user.first_name,
            "last_name": emp.user.last_name,
            "department": dept.name,
            "salary": str(emp.salary)
        })

    return JsonResponse({"success": True, "employees": data})


@login_required
@require_POST
def delete_department(request, dept_id):
    if not request.user.is_org_admin:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

    try:
        department = Department.objects.get(id=dept_id, organization=request.user.organization)
        department.delete()
        return JsonResponse({'success': True, 'message': 'Department deleted successfully'})
    except Department.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Department not found'}, status=404)


from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import HttpResponse

@login_required
def download_payslip_pdf(request, payslip_id):
    # Fetch payslip
    payslip = get_object_or_404(Payslip, id=payslip_id)

    # SECURITY RULES
    # Org Admin → Can download any payslip
    # HR → Can download only own payslips
    # Employee → Can download only own payslips
    if request.user.role == "HR" and payslip.user != request.user:
        return HttpResponse("Not allowed", status=403)

    if request.user.role == "Employee" and payslip.user != request.user:
        return HttpResponse("Not allowed", status=403)

    # Create PDF response
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = (
        f'attachment; filename="Payslip_{payslip.user.first_name}_{payslip.month}.pdf"'
    )

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Title
    p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height - 50, "PAYMASTER - Monthly Payslip")

    # Employee Info
    y = height - 120
    p.setFont("Helvetica", 12)

    p.drawString(50, y,       f"Employee Name: {payslip.user.first_name} {payslip.user.last_name}")
    p.drawString(50, y - 20,  f"Email: {payslip.user.email}")
    p.drawString(50, y - 40,  f"Month: {payslip.month.strftime('%B %Y')}")
    p.drawString(50, y - 60,  f"Generated At: {payslip.generated_at.strftime('%Y-%m-%d %H:%M')}")

    # Salary Info
    y -= 120
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Salary Breakdown")
    p.setFont("Helvetica", 12)

    p.drawString(50, y - 30, f"Gross Salary: ₹{payslip.gross_salary}")
    p.drawString(50, y - 50, f"Deductions: ₹{payslip.deductions}")
    p.drawString(50, y - 70, f"Net Salary: ₹{payslip.net_salary}")

    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, 40, "Generated by PayMaster Payroll System")

    p.showPage()
    p.save()
    return response


@login_required
def edit_department_page(request, dept_id):
    if not request.user.is_org_admin:
        return redirect('dashboard_redirect')

    department = get_object_or_404(
        Department,
        id=dept_id,
        organization=request.user.organization
    )

    if request.method == "POST":
        name = request.POST.get("name")
        head = request.POST.get("head")

        department.name = name
        department.head = head
        department.save()

        return redirect("org_admin_dashboard")

    return render(request, "payroll_app/edit_department.html", {
        "department": department
    })

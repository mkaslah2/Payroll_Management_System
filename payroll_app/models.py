from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
import uuid


# --- Custom User Manager and Model ---
class UserManager(BaseUserManager):
    """Custom user manager to handle creating Org Admins and regular users."""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        # Default role for Django superuser
        extra_fields.setdefault('role', 'SystemAdmin')
        return self.create_user(email, password, **extra_fields)


class Organization(models.Model):
    """Represents a company using PayMaster."""
    STATUS_CHOICES = [
        ('Pending', 'Pending Review'),
        ('Verified', 'Verified'),
        ('Suspended', 'Suspended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    address = models.CharField(max_length=255, blank=True)
    registration_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Custom User model to store roles and link to an Organization."""
    ROLE_CHOICES = [
        ('OrgAdmin', 'Organization Admin'),
        ('HR', 'HR Personnel'),
        ('Employee', 'Regular Employee'),
        ('SystemAdmin', 'System Admin'),
    ]

    username = None  # Use email as username
    email = models.EmailField('email address', unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Employee')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)

    # Fields from HTML mocks
    phone = models.CharField(max_length=20, blank=True, null=True)
    date_joined = models.DateField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def is_org_admin(self):
        return self.role == 'OrgAdmin'

    @property
    def is_hr(self):
        return self.role == 'HR'

    @property
    def is_employee(self):
        return self.role == 'Employee'


class Department(models.Model):
    """Departments within an Organization."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    head = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

    @property
    def employee_count(self):
        return HR.objects.filter(department=self).count() + Employee.objects.filter(department=self).count()


class Personnel(models.Model):
    """Base class for HR and Employee, linked to the User model."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    position = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        abstract = True


class HR(Personnel):
    """HR Personnel data, linked via User model."""
    def __str__(self):
        return f"HR: {self.user.first_name} ({self.organization.name})"


class Employee(Personnel):
    """Regular Employee data, linked via User model."""
    def __str__(self):
        return f"Employee: {self.user.first_name} ({self.organization.name})"

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Employee or HR
    reviewed_by = models.ForeignKey(User, null=True, blank=True,
                                    related_name="reviewed_leaves",
                                    on_delete=models.SET_NULL)

    leave_type = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    submitted_at = models.DateTimeField(default=timezone.now)



class Payslip(models.Model):
    """Generated payslips."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    month = models.DateField()  # Store as first day of the month
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    deductions = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_payslips'
    )
    generated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'month')

    def __str__(self):
        return f"{self.user.email} - {self.month.strftime('%Y-%m')}"


class Notification(models.Model):
    """Notifications sent from Admin/HR to personnel."""
    RECIPIENT_CHOICES = [
        ('All', 'All Employees'),
        ('HR', 'HR Personnel'),
        ('Employee', 'Regular Employees'),
        ('Single', 'Single User'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_CHOICES)
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_notifications'
    )
    title = models.CharField(max_length=100)
    message = models.TextField()
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_notifications'
    )
    sent_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title


class Attendance(models.Model):
    ATTENDANCE_STATUS = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Leave', 'Leave'),
    ]

    VERIFICATION_STATUS = [
        ('Pending', 'Pending'),
        ('Verified', 'Verified'),
        ('Rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)

    date = models.DateField()
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS)
    verification = models.CharField(max_length=10, choices=VERIFICATION_STATUS, default="Pending")

    marked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.first_name} - {self.date} - {self.status}"

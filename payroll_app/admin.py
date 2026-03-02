from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Organization, Department, HR, Employee, LeaveRequest, Payslip, Notification, Attendance

# Custom Admin for the custom User model
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'organization', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active', 'organization')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'role', 'phone', 'organization')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

# Limit the System Admin view to only Organizations
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'status', 'registration_date')
    list_filter = ('status',)
    search_fields = ('name', 'email')
    actions = ['mark_verified', 'mark_pending']
    
    def mark_verified(self, request, queryset):
        queryset.update(status='Verified')
    mark_verified.short_description = "Mark selected organizations as Verified"
    
    def mark_pending(self, request, queryset):
        queryset.update(status='Pending')
    mark_pending.short_description = "Mark selected organizations as Pending Review"

admin.site.register(User, CustomUserAdmin)


# Note: In a production-ready app, you would define custom dashboard views 
# (not the default Django Admin) for OrgAdmin/HR roles, and restrict access 
# based on their organization. For this project, all Org/HR/Emp actions will
# happen via the frontend dashboards.
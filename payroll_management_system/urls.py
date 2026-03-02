"""
URL configuration for payroll_management_system project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # System Admin panel - only for viewing Organizations
    path('system-admin/', admin.site.urls), 
    
    # Include all application URLs
    path('', include('payroll_app.urls')), 
]
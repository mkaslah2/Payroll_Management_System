from payroll_app.models import HR, Employee
from decimal import Decimal, InvalidOperation

print("Checking HR salary fields...")
for h in HR.objects.all():
    try:
        Decimal(str(h.salary))
        print("OK: HR user_id:", h.user.id, "salary:", h.salary)
    except InvalidOperation:
        print("❌ BAD HR SALARY:", h.user.id, h.salary)

print("\\nChecking Employee salary fields...")
for e in Employee.objects.all():
    try:
        Decimal(str(e.salary))
        print("OK: Employee user_id:", e.user.id, "salary:", e.salary)
    except InvalidOperation:
        print("❌ BAD EMPLOYEE SALARY:", e.user.id, e.salary)

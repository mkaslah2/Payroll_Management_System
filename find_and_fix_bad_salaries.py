from django.db import connection
from decimal import Decimal, InvalidOperation
from payroll_app.models import HR, Employee

def check_and_fix_salaries(table_name, model_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT user_id, salary FROM {table_name}")
        rows = cursor.fetchall()

    bad_rows = []
    for user_id, salary in rows:
        try:
            Decimal(str(salary))
        except InvalidOperation:
            bad_rows.append((user_id, salary))

    if not bad_rows:
        print(f"All salaries in {table_name} are OK.")
        return

    print(f"Found bad salaries in {table_name}:")
    for user_id, salary in bad_rows:
        print(f"❌ BAD SALARY: User ID {user_id} - Salary Value: {salary}")

    for user_id, _ in bad_rows:
        # Fix salary via ORM for proper model instance handling
        try:
            obj = model_name.objects.get(user_id=user_id)
            obj.salary = Decimal("0.00")
            obj.save()
            print(f"Fixed salary for User ID {user_id}")
        except model_name.DoesNotExist:
            print(f"User ID {user_id} not found in ORM for {table_name}")

if __name__ == "__main__":
    print("Checking and fixing HR salaries...")
    check_and_fix_salaries("payroll_app_hr", HR)

    print("\nChecking and fixing Employee salaries...")
    check_and_fix_salaries("payroll_app_employee", Employee)

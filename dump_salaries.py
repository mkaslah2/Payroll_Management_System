import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'payroll_management_system.settings')
django.setup()

from django.db import connection

def dump_salaries(table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT user_id, salary FROM {table_name}")
        rows = cursor.fetchall()

    print(f"Salaries from {table_name}:")
    for user_id, salary in rows:
        print(f"user_id: {user_id}, salary: {salary}")

if __name__ == "__main__":
    dump_salaries("payroll_app_hr")
    print()
    dump_salaries("payroll_app_employee")

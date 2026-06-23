"""Reset owner access codes in the database."""
from app import create_app
from app.utils import get_owner_access_code, set_owner_access_code

ADMIN_CODE = "admin2026"
DOCTOR_CODE = "doctor2026"

app = create_app()
with app.app_context():
    set_owner_access_code("admin", ADMIN_CODE)
    set_owner_access_code("doctor", DOCTOR_CODE)
    print("Owner access codes reset:")
    print(f"  Admin:  {get_owner_access_code('admin')}")
    print(f"  Doctor: {get_owner_access_code('doctor')}")

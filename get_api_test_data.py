import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_system.settings')
django.setup()

from core.models import Service, ServiceUser, Declaration

print("="*60)
print("API Test Data - Use these IDs in Postman")
print("="*60)

print("\n[Services]")
for service in Service.objects.all():
    print(f"  ID: {service.id}, Name: {service.name}, Slug: {service.slug}")

print("\n[Service Users]")
for su in ServiceUser.objects.all()[:10]:
    user_name = "Default" if su.is_default else su.user.username
    print(f"  ID: {su.id}, Service: {su.service.name}, User: {user_name}")

print("\n[Declarations]")
for decl in Declaration.objects.all():
    print(f"  ID: {decl.id}, Code: {decl.code}, Name: {decl.name}, Service: {decl.service.name}")

print("\n" + "="*60)
print("Quick Test Example:")
print("="*60)
print("POST http://localhost:8000/api/process/")
print("  - image: [upload your invoice image]")
su = ServiceUser.objects.filter(is_default=True).first()
decl = Declaration.objects.first()
if su and decl:
    print(f"  - service_user_id: {su.id}")
    print(f"  - declaration_id: {decl.id}")
print("\nGET http://localhost:8000/api/logs/")
print("  - No parameters needed")

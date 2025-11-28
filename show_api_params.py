import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_system.settings')
django.setup()

from core.models import Service, Declaration, CustomUser

print("="*70)
print("API /api/process/ Parameters Reference")
print("="*70)

print("\n1. service_slug (Available Services):")
print("-" * 70)
for service in Service.objects.all():
    print(f"   - '{service.slug}'  ({service.name})")

print("\n2. customs_code (Available Customs Codes):")
print("-" * 70)
print(f"   - 'default'  (Use default settings)")
for user in CustomUser.objects.filter(user_type='customs'):
    print(f"   - '{user.customs_code}'  ({user.customs_name})")

print("\n3. declaration_code (Available Declaration Codes):")
print("-" * 70)
for decl in Declaration.objects.all():
    print(f"   - '{decl.code}'  ({decl.name}, Service: {decl.service.name})")

print("\n" + "="*70)
print("EXAMPLE REQUEST:")
print("="*70)
print("""
POST http://localhost:8000/api/process/

Body (form-data):
  - image: [Select your invoice image file]
  - service_slug: rk-customs
  - customs_code: default
  - declaration_code: IMPORT_DECL
""")

print("="*70)
print("Full Example with curl:")
print("="*70)
print("""
curl -X POST http://localhost:8000/api/process/ \\
  -H "Cookie: sessionid=YOUR_SESSION_ID" \\
  -F "image=@invoice.jpg" \\
  -F "service_slug=rk-customs" \\
  -F "customs_code=default" \\
  -F "declaration_code=IMPORT_DECL"
""")

import os
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_system.settings')
django.setup()

from core.models import CustomUser, Service, ServiceUser, Declaration, MappingInfo, PromptConfig

# 1. 관리자 계정 생성
print("Creating admin account...")
admin_user, created = CustomUser.objects.get_or_create(
    username='admin',
    defaults={
        'user_type': 'admin',
        'is_staff': True,
        'is_superuser': True,
        'is_first_login': False,
    }
)
if created:
    admin_user.set_password('P@ssw0rd')
    admin_user.save()
    print("[OK] Admin account created (admin / P@ssw0rd)")
else:
    print("[OK] Admin account already exists")

# 2. 샘플 관세사 계정 생성
print("\nCreating sample customs accounts...")
sample_customs = [
    {'code': '6N001', 'name': 'A customs broker'},
    {'code': '6N002', 'name': 'Woori customs broker'},
]

for customs in sample_customs:
    user, created = CustomUser.objects.get_or_create(
        username=customs['code'],
        defaults={
            'user_type': 'customs',
            'customs_code': customs['code'],
            'customs_name': customs['name'],
            'is_first_login': True,
        }
    )
    if created:
        user.set_password('init123')
        user.save()
        print(f"[OK] Customs account created: {customs['name']} ({customs['code']} / init123)")
    else:
        print(f"[OK] Customs account already exists: {customs['name']}")

# 3. 서비스 생성
print("\nCreating services...")
services_data = [
    {'name': 'RK Customs', 'slug': 'rk-customs', 'description': 'RK Customs service'},
    {'name': 'Association Customs', 'slug': 'association-customs', 'description': 'Association Customs service'},
    {'name': 'HelpManager', 'slug': 'help-manager', 'description': 'Help Manager service'},
]

services = []
for service_data in services_data:
    service, created = Service.objects.get_or_create(
        name=service_data['name'],
        defaults={
            'slug': service_data['slug'],
            'description': service_data['description'],
            'is_active': True
        }
    )
    services.append(service)
    if created:
        print(f"[OK] Service created: {service.name}")
    else:
        print(f"[OK] Service already exists: {service.name}")

# 4. 서비스-사용자 연결
print("\nCreating service-user connections...")
for service in services:
    # 기본 설정
    service_user_default, created = ServiceUser.objects.get_or_create(
        service=service,
        user=None,
        defaults={'is_default': True}
    )
    if created:
        print(f"[OK] {service.name} - default settings created")

    # 관세사 연결
    for customs in sample_customs:
        user = CustomUser.objects.get(customs_code=customs['code'])
        service_user, created = ServiceUser.objects.get_or_create(
            service=service,
            user=user,
            defaults={'is_default': False}
        )
        if created:
            print(f"[OK] {service.name} - {customs['name']} connected")

# 5. 신고서 생성
print("\nCreating declarations...")
declarations_data = [
    {'name': 'Import Declaration', 'code': 'IMPORT_DECL', 'type': 'import', 'service': 'RK Customs'},
    {'name': 'Export Declaration', 'code': 'EXPORT_DECL', 'type': 'export', 'service': 'RK Customs'},
    {'name': 'Export Correction', 'code': 'EXPORT_CORR', 'type': 'correction', 'service': 'RK Customs'},
]

declarations = []
for decl_data in declarations_data:
    service = Service.objects.get(name=decl_data['service'])
    declaration, created = Declaration.objects.get_or_create(
        code=decl_data['code'],
        defaults={
            'name': decl_data['name'],
            'service': service,
            'declaration_type': decl_data['type'],
            'is_active': True,
            'description': f'{decl_data["name"]} management'
        }
    )
    declarations.append(declaration)
    if created:
        print(f"[OK] Declaration created: {declaration.name} ({service.name})")
    else:
        print(f"[OK] Declaration already exists: {declaration.name}")

# 6. 샘플 매핑정보 생성
print("\nCreating sample mapping info...")
if declarations:
    declaration = declarations[0]  # Import Declaration
    service_user_default = ServiceUser.objects.filter(
        service=declaration.service,
        is_default=True
    ).first()

    sample_mappings = [
        {'unipass': 'Report Number', 'table': 'ImportDeclaration', 'field': 'Rpt_num'},
        {'unipass': 'Serial Number', 'table': 'ImportDeclaration', 'field': 'SN'},
        {'unipass': 'Goods Name', 'table': 'ImportGoods', 'field': 'goods_name'},
        {'unipass': 'HS Code', 'table': 'ImportGoods', 'field': 'hs_code'},
    ]

    for idx, mapping_data in enumerate(sample_mappings):
        mapping, created = MappingInfo.objects.get_or_create(
            declaration=declaration,
            unipass_field_name=mapping_data['unipass'],
            service_user=service_user_default,
            defaults={
                'db_table_name': mapping_data['table'],
                'db_field_name': mapping_data['field'],
                'priority': idx,
                'is_active': True
            }
        )
        if created:
            print(f"[OK] Mapping created: {mapping_data['unipass']} -> {mapping_data['table']}.{mapping_data['field']}")

            # 기본 프롬프트 생성
            PromptConfig.objects.create(
                mapping=mapping,
                prompt_type='basic',
                service_user=None,
                prompt_text=f"Extract {mapping_data['unipass']} field accurately. Return null if value not found.",
                is_active=True,
                created_by=admin_user
            )
            print(f"  -> Basic prompt created")

print("\n" + "="*50)
print("Initial data setup completed!")
print("="*50)
print("\nLogin information:")
print("  Admin: admin / P@ssw0rd")
print("  Customs: 6N001 / init123 (A customs broker)")
print("  Customs: 6N002 / init123 (Woori customs broker)")
print("\nAccess URL: http://localhost:8000")

"""
초기 데이터 설정 스크립트
Django 프로젝트 설정 후 실행하여 초기 데이터를 생성합니다.

실행 방법:
python manage.py shell < setup_initial_data.py
"""

from core.models import CustomUser, Service, ServiceUser, Declaration, MappingInfo, PromptConfig

# 1. 관리자 계정 생성
print("관리자 계정 생성 중...")
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
    print("✓ 관리자 계정 생성 완료 (admin / P@ssw0rd)")
else:
    print("✓ 관리자 계정 이미 존재")

# 2. 샘플 관세사 계정 생성
print("\n샘플 관세사 계정 생성 중...")
sample_customs = [
    {'code': '6N001', 'name': 'A관세사'},
    {'code': '6N002', 'name': '우리관세사'},
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
        print(f"✓ 관세사 계정 생성: {customs['name']} ({customs['code']} / init123)")
    else:
        print(f"✓ 관세사 계정 이미 존재: {customs['name']}")

# 3. 서비스 생성
print("\n서비스 생성 중...")
services_data = [
    {'name': 'RK통관', 'description': 'RK통관 서비스'},
    {'name': '협회통관', 'description': '협회통관 서비스'},
    {'name': 'HelpManager', 'description': 'Help Manager 서비스'},
]

services = []
for service_data in services_data:
    service, created = Service.objects.get_or_create(
        name=service_data['name'],
        defaults={'description': service_data['description'], 'is_active': True}
    )
    services.append(service)
    if created:
        print(f"✓ 서비스 생성: {service.name}")
    else:
        print(f"✓ 서비스 이미 존재: {service.name}")

# 4. 서비스-사용자 연결
print("\n서비스-사용자 연결 생성 중...")
for service in services:
    # 기본 설정
    service_user_default, created = ServiceUser.objects.get_or_create(
        service=service,
        user=None,
        defaults={'is_default': True}
    )
    if created:
        print(f"✓ {service.name} - 기본 설정 생성")

    # 관세사 연결
    for customs in sample_customs:
        user = CustomUser.objects.get(customs_code=customs['code'])
        service_user, created = ServiceUser.objects.get_or_create(
            service=service,
            user=user,
            defaults={'is_default': False}
        )
        if created:
            print(f"✓ {service.name} - {customs['name']} 연결")

# 5. 신고서 생성
print("\n신고서 생성 중...")
declarations_data = [
    {'name': '수입신고서', 'type': 'import', 'service': 'RK통관'},
    {'name': '수출신고서', 'type': 'export', 'service': 'RK통관'},
    {'name': '수출정정', 'type': 'correction', 'service': 'RK통관'},
]

declarations = []
for decl_data in declarations_data:
    service = Service.objects.get(name=decl_data['service'])
    declaration, created = Declaration.objects.get_or_create(
        name=decl_data['name'],
        service=service,
        defaults={
            'declaration_type': decl_data['type'],
            'is_active': True,
            'description': f'{decl_data["name"]} 관리'
        }
    )
    declarations.append(declaration)
    if created:
        print(f"✓ 신고서 생성: {declaration.name} ({service.name})")
    else:
        print(f"✓ 신고서 이미 존재: {declaration.name}")

# 6. 샘플 매핑정보 생성
print("\n샘플 매핑정보 생성 중...")
if declarations:
    declaration = declarations[0]  # 수입신고서
    service_user_default = ServiceUser.objects.filter(
        service=declaration.service,
        is_default=True
    ).first()

    sample_mappings = [
        {'unipass': '신고번호', 'table': 'ImportDeclaration', 'field': 'Rpt_num'},
        {'unipass': '시리얼번호', 'table': 'ImportDeclaration', 'field': 'SN'},
        {'unipass': '품명', 'table': 'ImportGoods', 'field': 'goods_name'},
        {'unipass': 'HS부호', 'table': 'ImportGoods', 'field': 'hs_code'},
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
            print(f"✓ 매핑정보 생성: {mapping_data['unipass']} → {mapping_data['table']}.{mapping_data['field']}")

            # 기본 프롬프트 생성
            PromptConfig.objects.create(
                mapping=mapping,
                prompt_type='basic',
                service_user=None,
                prompt_text=f"{mapping_data['unipass']} 항목을 정확하게 추출하세요. 값이 없는 경우 null을 반환하세요.",
                is_active=True,
                created_by=admin_user
            )
            print(f"  → 기본 프롬프트 생성")

print("\n" + "="*50)
print("초기 데이터 설정 완료!")
print("="*50)
print("\n로그인 정보:")
print("  관리자: admin / P@ssw0rd")
print("  관세사: 6N001 / init123 (A관세사)")
print("  관세사: 6N002 / init123 (우리관세사)")
print("\n접속 URL: http://localhost:8000")

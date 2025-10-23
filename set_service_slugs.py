import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_system.settings')
django.setup()

from core.models import Service

# 서비스 목록 조회
services = Service.objects.all()

print("현재 서비스 목록:")
for service in services:
    print(f"  ID: {service.id}, 이름: {service.name}, Slug: {service.slug}")

print("\n서비스 slug 업데이트:")

# 서비스별 slug 설정 (수동으로 매핑)
slug_mapping = {
    '협회통관': 'customs-association',
    'HelpManager': 'help-manager',
    'RK통관': 'rk-customs'
}

for service in services:
    if service.name in slug_mapping:
        new_slug = slug_mapping[service.name]
        service.slug = new_slug
        service.save()
        print(f"  '{service.name}' -> slug: '{new_slug}'")
    else:
        # 영문명이거나 매핑에 없는 경우 자동 생성
        new_slug = service.name.lower().replace(' ', '-')
        service.slug = new_slug
        service.save()
        print(f"  '{service.name}' -> slug: '{new_slug}'")

print("\n업데이트 완료!")
print("\n최종 서비스 목록:")
for service in Service.objects.all():
    print(f"  {service.name} (slug: {service.slug})")

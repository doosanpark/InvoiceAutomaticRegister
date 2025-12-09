from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from .models import (
    CustomUser, Service, ServiceUser, Declaration,
    MappingInfo, PromptConfig, TableProcessConfig
)
from .forms import LoginForm, PasswordChangeForm, ServiceForm, CustomUserForm, DeclarationForm
import os


def login_view(request):
    """로그인 페이지"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                # 최초 로그인 체크
                if user.is_first_login:
                    return redirect('change_password')

                # 로그인 후 대시보드로 이동 (admin도 대시보드에서 서비스 리스트로)
                return redirect('dashboard')
            else:
                messages.error(request, '아이디 또는 비밀번호가 올바르지 않습니다.')
        else:
            messages.error(request, '입력 정보를 확인해주세요.')
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form})


@login_required
def logout_view(request):
    """로그아웃"""
    logout(request)
    return redirect('login')


@login_required
def change_password_view(request):
    """비밀번호 변경"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST, user=request.user)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user = request.user
            user.set_password(new_password)
            user.is_first_login = False
            user.save()

            # 세션 유지
            update_session_auth_hash(request, user)

            messages.success(request, '비밀번호가 성공적으로 변경되었습니다.')

            if user.user_type == 'admin':
                return redirect('service_list')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, '비밀번호를 확인해주세요.')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'core/change_password.html', {'form': form})


@login_required
def dashboard(request):
    """대시보드"""
    if request.user.user_type == 'admin':
        # 관리자는 서비스 리스트로 리다이렉트
        return redirect('service_list')

    # 관세사: 사용자가 속한 서비스 가져오기
    service_users = ServiceUser.objects.filter(user=request.user).select_related('service')

    return render(request, 'core/dashboard.html', {
        'service_users': service_users
    })


@login_required
def service_list_view(request):
    """서비스 리스트 페이지 (관리자 전용)"""
    if request.user.user_type != 'admin':
        messages.error(request, '관리자만 접근할 수 있습니다.')
        return redirect('dashboard')

    services = Service.objects.filter(is_active=True)

    return render(request, 'core/service_list.html', {
        'services': services
    })


@login_required
def service_add_view(request):
    """서비스 추가 (관리자 전용)"""
    if request.user.user_type != 'admin':
        messages.error(request, '관리자만 접근할 수 있습니다.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()

            # 기본 ServiceUser 생성
            ServiceUser.objects.create(
                service=service,
                user=None,
                is_default=True
            )

            messages.success(request, f'{service.name} 서비스가 추가되었습니다.')
            return redirect('service_list')
        else:
            messages.error(request, '입력 정보를 확인해주세요.')
    else:
        form = ServiceForm()

    return render(request, 'core/service_add.html', {'form': form})


@login_required
def service_detail_view(request, service_slug):
    """서비스 상세 - 업체 리스트 (관리자 전용)"""
    if request.user.user_type != 'admin':
        messages.error(request, '관리자만 접근할 수 있습니다.')
        return redirect('dashboard')

    service = get_object_or_404(Service, slug=service_slug)

    # 해당 서비스를 사용하는 모든 업체 (관세사)
    service_users = ServiceUser.objects.filter(
        service=service
    ).select_related('user').order_by('-is_default', 'user__customs_name')

    return render(request, 'core/service_detail.html', {
        'service': service,
        'service_users': service_users
    })


@login_required
def add_customs_to_service(request, service_slug):
    """서비스에 관세사 추가 (관리자 전용)"""
    if request.user.user_type != 'admin':
        messages.error(request, '관리자만 접근할 수 있습니다.')
        return redirect('dashboard')

    service = get_object_or_404(Service, slug=service_slug)

    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            customs_code = form.cleaned_data['customs_code']
            customs_name = form.cleaned_data['customs_name']

            # 기존 사용자 확인
            user = CustomUser.objects.filter(customs_code=customs_code).first()

            if user:
                # 기존 사용자가 있으면 해당 서비스에 연결만
                service_user, created = ServiceUser.objects.get_or_create(
                    service=service,
                    user=user,
                    defaults={'is_default': False}
                )
                if created:
                    messages.success(request, f'{user.customs_name} 관세사가 {service.name}에 추가되었습니다.')
                else:
                    messages.info(request, f'{user.customs_name} 관세사는 이미 이 서비스에 등록되어 있습니다.')
            else:
                # 새 관세사 사용자 생성
                user = CustomUser.objects.create_user(
                    username=customs_code,
                    password='init123',
                    user_type='customs',
                    customs_code=customs_code,
                    customs_name=customs_name,
                    is_first_login=True
                )

                # 서비스에 연결
                ServiceUser.objects.create(
                    service=service,
                    user=user,
                    is_default=False
                )

                messages.success(request, f'{customs_name} 관세사가 생성되고 {service.name}에 추가되었습니다.')

            return redirect('service_detail', service_id=service.id)
        else:
            messages.error(request, '입력 정보를 확인해주세요.')
    else:
        form = CustomUserForm()

    return render(request, 'core/add_customs.html', {
        'form': form,
        'service': service
    })


@login_required
def declaration_list_view(request, service_slug=None, customs_code=None):
    """신고서 관리 페이지"""
    # service_slug와 customs_code가 없으면 현재 사용자의 첫 번째 서비스 사용
    if not service_slug or not customs_code:
        if request.user.user_type == 'admin':
            return redirect('service_list')

        service_user = ServiceUser.objects.filter(user=request.user).first()
        if not service_user:
            messages.error(request, '할당된 서비스가 없습니다.')
            return redirect('dashboard')
    else:
        # service_slug와 customs_code로 ServiceUser 찾기
        service = get_object_or_404(Service, slug=service_slug)

        # customs_code가 'default'면 기본 설정
        if customs_code == 'default':
            service_user = get_object_or_404(ServiceUser, service=service, is_default=True)
        else:
            user = get_object_or_404(CustomUser, customs_code=customs_code)
            service_user = get_object_or_404(ServiceUser, service=service, user=user)

        # 권한 체크
        if request.user.user_type != 'admin' and service_user.user != request.user:
            messages.error(request, '접근 권한이 없습니다.')
            return redirect('dashboard')

    # 해당 서비스의 신고서 목록
    declarations = Declaration.objects.filter(
        service=service_user.service,
        is_active=True
    )

    return render(request, 'core/declaration_list.html', {
        'service_user': service_user,
        'declarations': declarations
    })


@login_required
def declaration_detail_view(request, service_slug, customs_code, declaration_code):
    """신고서 상세 - 매핑정보, 프롬프트 설정"""
    # service_slug와 customs_code로 ServiceUser 찾기
    service = get_object_or_404(Service, slug=service_slug)
    declaration = get_object_or_404(Declaration, service=service, code=declaration_code)

    if customs_code == 'default':
        service_user = get_object_or_404(ServiceUser, service=service, is_default=True)
    else:
        user = get_object_or_404(CustomUser, customs_code=customs_code)
        service_user = get_object_or_404(ServiceUser, service=service, user=user)

    # 권한 체크
    if request.user.user_type != 'admin':
        if service_user.user != request.user:
            messages.error(request, '접근 권한이 없습니다.')
            return redirect('dashboard')

    # 매핑 정보
    mappings = MappingInfo.objects.filter(
        declaration=declaration,
        is_active=True
    ).order_by('db_table_name', 'priority')

    # 각 매핑에 대한 프롬프트 정보
    mapping_data = []
    for mapping in mappings:
        # 기본 프롬프트 (service_user가 null인 것)
        basic_prompt = PromptConfig.objects.filter(
            mapping=mapping,
            prompt_type='basic',
            service_user__isnull=True,
            is_active=True
        ).first()

        # 추가 프롬프트 (해당 service_user)
        additional_prompt = PromptConfig.objects.filter(
            mapping=mapping,
            prompt_type='additional',
            service_user=service_user,
            is_active=True
        ).first()

        mapping_data.append({
            'mapping': mapping,
            'basic_prompt': basic_prompt,
            'additional_prompt': additional_prompt
        })

    # 편집 권한
    can_edit_basic = request.user.user_type == 'admin'
    can_edit_additional = (
        request.user.user_type == 'admin' or
        (service_user.user == request.user and not service_user.is_default)
    )

    # 테이블 처리 설정 (기본 설정이고 관리자인 경우만)
    table_configs = []
    if service_user.is_default and request.user.user_type == 'admin':
        table_configs = TableProcessConfig.objects.filter(
            declaration=declaration,
            service_user=service_user,
            is_active=True
        ).order_by('process_order')

    return render(request, 'core/declaration_detail.html', {
        'declaration': declaration,
        'service_user': service_user,
        'mapping_data': mapping_data,
        'can_edit_basic': can_edit_basic,
        'can_edit_additional': can_edit_additional,
        'table_configs': table_configs
    })


@login_required
@require_http_methods(["POST"])
def update_prompt_view(request, mapping_id):
    """프롬프트 업데이트 (AJAX)"""
    mapping = get_object_or_404(MappingInfo, pk=mapping_id)
    prompt_type = request.POST.get('prompt_type')
    prompt_text = request.POST.get('prompt_text')
    service_user_id = request.POST.get('service_user_id')

    # 권한 체크
    if prompt_type == 'basic':
        if request.user.user_type != 'admin':
            return JsonResponse({'success': False, 'error': '관리자만 수정할 수 있습니다.'})

        # 기본 프롬프트 업데이트 (service_user는 null)
        prompt, created = PromptConfig.objects.update_or_create(
            mapping=mapping,
            prompt_type='basic',
            service_user=None,
            defaults={
                'prompt_text': prompt_text,
                'created_by': request.user,
                'is_active': True
            }
        )

    elif prompt_type == 'additional':
        service_user = get_object_or_404(ServiceUser, pk=service_user_id)

        # 권한 체크
        if request.user.user_type != 'admin' and service_user.user != request.user:
            return JsonResponse({'success': False, 'error': '권한이 없습니다.'})

        # 추가 프롬프트 업데이트
        prompt, created = PromptConfig.objects.update_or_create(
            mapping=mapping,
            prompt_type='additional',
            service_user=service_user,
            defaults={
                'prompt_text': prompt_text,
                'created_by': request.user,
                'is_active': True
            }
        )

    else:
        return JsonResponse({'success': False, 'error': '잘못된 프롬프트 유형입니다.'})

    return JsonResponse({
        'success': True,
        'message': '저장되었습니다.',
        'prompt_id': prompt.id
    })


@login_required
@require_http_methods(["POST"])
def add_mapping_view(request, declaration_id):
    """매핑 정보 추가 (AJAX)"""
    declaration = get_object_or_404(Declaration, pk=declaration_id)

    # 권한 체크 (관리자 또는 해당 서비스 사용자)
    if request.user.user_type != 'admin':
        service_user_id = request.POST.get('service_user_id')
        service_user = get_object_or_404(ServiceUser, pk=service_user_id)
        if service_user.user != request.user:
            return JsonResponse({'success': False, 'error': '권한이 없습니다.'})

    unipass_field_name = request.POST.get('unipass_field_name')
    db_table_name = request.POST.get('db_table_name')
    db_field_name = request.POST.get('db_field_name')
    field_type = request.POST.get('field_type', 'string')
    field_length = request.POST.get('field_length')
    service_user_id = request.POST.get('service_user_id')

    if not all([unipass_field_name, db_table_name, db_field_name]):
        return JsonResponse({'success': False, 'error': '필수 필드를 입력해주세요.'})

    service_user = None
    if service_user_id:
        service_user = get_object_or_404(ServiceUser, pk=service_user_id)

    mapping = MappingInfo.objects.create(
        declaration=declaration,
        service_user=service_user,
        unipass_field_name=unipass_field_name,
        db_table_name=db_table_name,
        db_field_name=db_field_name,
        field_type=field_type,
        field_length=int(field_length) if field_length else None,
        is_active=True
    )

    return JsonResponse({
        'success': True,
        'message': '매핑 정보가 추가되었습니다.',
        'mapping_id': mapping.id
    })


@login_required
@require_http_methods(["POST"])
def update_mapping_view(request, mapping_id):
    """매핑 정보 수정 (AJAX)"""
    mapping = get_object_or_404(MappingInfo, pk=mapping_id)

    # 권한 체크
    if request.user.user_type != 'admin':
        if mapping.service_user and mapping.service_user.user != request.user:
            return JsonResponse({'success': False, 'error': '권한이 없습니다.'})

    unipass_field_name = request.POST.get('unipass_field_name')
    db_table_name = request.POST.get('db_table_name')
    db_field_name = request.POST.get('db_field_name')
    field_type = request.POST.get('field_type', 'string')
    field_length = request.POST.get('field_length')

    if not all([unipass_field_name, db_table_name, db_field_name]):
        return JsonResponse({'success': False, 'error': '필수 필드를 입력해주세요.'})

    mapping.unipass_field_name = unipass_field_name
    mapping.db_table_name = db_table_name
    mapping.db_field_name = db_field_name
    mapping.field_type = field_type
    mapping.field_length = int(field_length) if field_length else None
    mapping.save()

    return JsonResponse({
        'success': True,
        'message': '매핑 정보가 수정되었습니다.'
    })


@login_required
@require_http_methods(["POST"])
def delete_mapping_view(request, mapping_id):
    """매핑 정보 삭제 (AJAX)"""
    mapping = get_object_or_404(MappingInfo, pk=mapping_id)

    # 권한 체크
    if request.user.user_type != 'admin':
        if mapping.service_user and mapping.service_user.user != request.user:
            return JsonResponse({'success': False, 'error': '권한이 없습니다.'})

    mapping.delete()

    return JsonResponse({
        'success': True,
        'message': '매핑 정보가 삭제되었습니다.'
    })

@login_required
def declaration_add_view(request, service_slug, customs_code):
    """신고서 추가"""
    service = get_object_or_404(Service, slug=service_slug)

    # service_user 찾기
    if customs_code == 'default':
        service_user = get_object_or_404(ServiceUser, service=service, is_default=True)
    else:
        user = get_object_or_404(CustomUser, customs_code=customs_code)
        service_user = get_object_or_404(ServiceUser, service=service, user=user)

    # 권한 체크
    if request.user.user_type != 'admin':
        messages.error(request, '관리자만 접근할 수 있습니다.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = DeclarationForm(request.POST)
        if form.is_valid():
            declaration = form.save(commit=False)
            declaration.service = service
            declaration.save()
            messages.success(request, f'{declaration.name} 신고서가 추가되었습니다.')
            return redirect('declaration_list_with_user', service_slug=service.slug, customs_code=customs_code)
    else:
        form = DeclarationForm()

    return render(request, 'core/declaration_form.html', {
        'form': form,
        'service': service,
        'service_user': service_user,
        'is_edit': False
    })


@login_required
def declaration_edit_view(request, service_slug, customs_code, declaration_code):
    """신고서 수정"""
    service = get_object_or_404(Service, slug=service_slug)
    declaration = get_object_or_404(Declaration, service=service, code=declaration_code)

    # service_user 찾기
    if customs_code == 'default':
        service_user = get_object_or_404(ServiceUser, service=service, is_default=True)
    else:
        user = get_object_or_404(CustomUser, customs_code=customs_code)
        service_user = get_object_or_404(ServiceUser, service=service, user=user)

    # 권한 체크
    if request.user.user_type != 'admin':
        messages.error(request, '관리자만 접근할 수 있습니다.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = DeclarationForm(request.POST, instance=declaration)
        if form.is_valid():
            form.save()
            messages.success(request, f'{declaration.name} 신고서가 수정되었습니다.')
            return redirect('declaration_list_with_user', service_slug=service.slug, customs_code=customs_code)
    else:
        form = DeclarationForm(instance=declaration)

    return render(request, 'core/declaration_form.html', {
        'form': form,
        'service': service,
        'service_user': service_user,
        'declaration': declaration,
        'is_edit': True
    })


@login_required
@require_http_methods(["POST"])
def declaration_delete_view(request, service_slug, customs_code, declaration_code):
    """신고서 삭제"""
    # 권한 체크
    if request.user.user_type != 'admin':
        messages.error(request, '관리자만 접근할 수 있습니다.')
        return redirect('dashboard')

    service = get_object_or_404(Service, slug=service_slug)
    declaration = get_object_or_404(Declaration, service=service, code=declaration_code)

    declaration_name = declaration.name
    declaration.delete()
    messages.success(request, f'{declaration_name} 신고서가 삭제되었습니다.')
    return redirect('declaration_list_with_user', service_slug=service.slug, customs_code=customs_code)


@login_required
@require_http_methods(["POST"])
def update_metadata_view(request, declaration_id):
    """신고서 메타데이터 업데이트 (AJAX)"""
    declaration = get_object_or_404(Declaration, pk=declaration_id)

    # 권한 체크 (관리자만)
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': '관리자만 수정할 수 있습니다.'})

    metadata = request.POST.get('metadata', '')

    declaration.description = metadata
    declaration.save()

    return JsonResponse({
        'success': True,
        'message': '메타데이터가 저장되었습니다.'
    })


@login_required
@require_http_methods(["POST"])
def upload_specification_view(request, declaration_id):
    """항목정의서 파일 업로드 (AJAX)"""
    declaration = get_object_or_404(Declaration, pk=declaration_id)

    # 권한 체크 (관리자만)
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': '관리자만 업로드할 수 있습니다.'})

    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': '파일이 필요합니다.'})

    file = request.FILES['file']

    # 파일 확장자 검증 (엑셀 파일만)
    allowed_extensions = ['.xlsx', '.xls']
    file_ext = os.path.splitext(file.name)[1].lower()
    if file_ext not in allowed_extensions:
        return JsonResponse({'success': False, 'error': '엑셀 파일(.xlsx, .xls)만 업로드 가능합니다.'})

    # 기존 파일 삭제
    if declaration.specification_file:
        if os.path.exists(declaration.specification_file.path):
            os.remove(declaration.specification_file.path)

    # 새 파일 저장
    declaration.specification_file = file
    declaration.save()

    return JsonResponse({
        'success': True,
        'message': '항목정의서가 업로드되었습니다.',
        'file_name': file.name
    })


@login_required
def download_specification_view(request, declaration_id):
    """항목정의서 파일 다운로드"""
    declaration = get_object_or_404(Declaration, pk=declaration_id)

    if not declaration.specification_file:
        raise Http404('파일이 존재하지 않습니다.')

    # 파일 경로
    file_path = declaration.specification_file.path

    if not os.path.exists(file_path):
        raise Http404('파일이 존재하지 않습니다.')

    # 파일 이름
    file_name = os.path.basename(file_path)

    # 파일 응답
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    return response


@login_required
@require_http_methods(["POST"])
def add_table_config_view(request, declaration_id):
    """테이블 처리 설정 추가 (AJAX)"""
    declaration = get_object_or_404(Declaration, pk=declaration_id)
    
    # 권한 체크 (관리자만)
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': '관리자만 추가할 수 있습니다.'})
    
    work_group = request.POST.get('work_group', '').strip()
    db_table_name = request.POST.get('db_table_name', '').strip()
    process_order = request.POST.get('process_order', '').strip()
    service_user_id = request.POST.get('service_user_id')
    
    # 유효성 검사
    if not all([work_group, db_table_name, process_order]):
        return JsonResponse({'success': False, 'error': '모든 필수 필드를 입력해주세요.'})
    
    try:
        process_order = int(process_order)
    except ValueError:
        return JsonResponse({'success': False, 'error': '처리 순서는 숫자여야 합니다.'})
    
    # ServiceUser 조회
    service_user = None
    if service_user_id:
        service_user = get_object_or_404(ServiceUser, pk=service_user_id)
    
    # 중복 체크
    existing = TableProcessConfig.objects.filter(
        declaration=declaration,
        service_user=service_user,
        db_table_name=db_table_name
    ).exists()
    
    if existing:
        return JsonResponse({'success': False, 'error': '이미 동일한 테이블명의 설정이 존재합니다.'})
    
    # 테이블 처리 설정 생성
    config = TableProcessConfig.objects.create(
        declaration=declaration,
        service_user=service_user,
        work_group=work_group,
        db_table_name=db_table_name,
        process_order=process_order,
        is_active=True
    )
    
    return JsonResponse({
        'success': True,
        'message': '테이블 처리 설정이 추가되었습니다.',
        'config_id': config.id
    })


@login_required
@require_http_methods(["POST"])
def update_table_config_view(request, config_id):
    """테이블 처리 설정 수정 (AJAX)"""
    config = get_object_or_404(TableProcessConfig, pk=config_id)
    
    # 권한 체크 (관리자만)
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': '관리자만 수정할 수 있습니다.'})
    
    work_group = request.POST.get('work_group', '').strip()
    db_table_name = request.POST.get('db_table_name', '').strip()
    process_order = request.POST.get('process_order', '').strip()
    
    # 유효성 검사
    if not all([work_group, db_table_name, process_order]):
        return JsonResponse({'success': False, 'error': '모든 필수 필드를 입력해주세요.'})
    
    try:
        process_order = int(process_order)
    except ValueError:
        return JsonResponse({'success': False, 'error': '처리 순서는 숫자여야 합니다.'})
    
    # 중복 체크 (자기 자신 제외)
    existing = TableProcessConfig.objects.filter(
        declaration=config.declaration,
        service_user=config.service_user,
        db_table_name=db_table_name
    ).exclude(pk=config_id).exists()
    
    if existing:
        return JsonResponse({'success': False, 'error': '이미 동일한 테이블명의 설정이 존재합니다.'})
    
    # 업데이트
    config.work_group = work_group
    config.db_table_name = db_table_name
    config.process_order = process_order
    config.save()
    
    return JsonResponse({
        'success': True,
        'message': '테이블 처리 설정이 수정되었습니다.'
    })


@login_required
@require_http_methods(["POST"])
def delete_table_config_view(request, config_id):
    """테이블 처리 설정 삭제 (AJAX)"""
    config = get_object_or_404(TableProcessConfig, pk=config_id)
    
    # 권한 체크 (관리자만)
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': '관리자만 삭제할 수 있습니다.'})
    
    config.delete()
    
    return JsonResponse({
        'success': True,
        'message': '테이블 처리 설정이 삭제되었습니다.'
    })

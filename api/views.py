"""
REST API Views
인보이스 처리 API 엔드포인트
"""
import os
import time
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils import timezone
from core.models import (
    ServiceUser, Declaration, MappingInfo, TableProcessConfig,
    PromptConfig, InvoiceProcessLog, Service, CustomUser
)
from core.services import InvoiceProcessor

logger = logging.getLogger('api')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_invoice(request):
    """
    인보이스 처리 API

    Request Body:
    - image: 인보이스 이미지 파일 (multipart/form-data)
    - service_slug: 서비스 slug (예: rk-customs)
    - customs_code: 관세사 코드 (예: 6N003) 또는 'default'
    - declaration_code: 신고서 코드 (예: CUSDEC929)
    - ai_engine: AI 엔진 선택 (gemini 또는 gpt, 기본값: gemini)

    Response:
    - success: 성공 여부
    - data: 정리된 JSON 데이터
    - ocr_text: OCR 추출 텍스트
    - processing_time: 처리 시간(초)
    - log_id: 처리 로그 ID
    - ai_engine: 사용된 AI 엔진
    """

    logger.info("\n" + "="*80)
    logger.info("[API REQUEST] /api/process/")
    logger.info("="*80)
    logger.info(f"User: {request.user.username}")
    logger.info(f"Request Data: {dict(request.data)}")
    logger.info("="*80 + "\n")

    # Step 1: 요청 데이터 검증
    if 'image' not in request.FILES:
        return Response(
            {'success': False, 'error': '이미지 파일이 필요합니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    service_slug = request.data.get('service_slug')
    customs_code = request.data.get('customs_code')
    declaration_code = request.data.get('declaration_code')
    ai_engine = request.data.get('ai_engine', 'gpt').lower()  # 기본값: gpt

    if not service_slug or not customs_code or not declaration_code:
        return Response(
            {'success': False, 'error': 'service_slug, customs_code, declaration_code가 필요합니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 서비스 조회
    service = get_object_or_404(Service, slug=service_slug)

    # ServiceUser 조회
    if customs_code == 'default':
        service_user = get_object_or_404(ServiceUser, service=service, is_default=True)
    else:
        user = get_object_or_404(CustomUser, customs_code=customs_code)
        service_user = get_object_or_404(ServiceUser, service=service, user=user)

    # Declaration 조회
    declaration = get_object_or_404(Declaration, service=service, code=declaration_code)

    if request.user.user_type != 'admin':
        if service_user.user != request.user:
            return Response(
                {'success': False, 'error': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

    # Step 1: 이미지 파일 저장
    image_file = request.FILES['image']

    # 로그 생성
    process_log = InvoiceProcessLog.objects.create(
        service_user=service_user,
        declaration=declaration,
        image_file=image_file,
        status='processing'
    )

    try:
        # 이미지 파일 경로
        image_path = process_log.image_file.path

        # 테이블 처리 설정 정보 가져오기 (테이블명으로 매칭)
        table_configs = {}
        configs = TableProcessConfig.objects.filter(
            declaration=declaration,
            service_user=service_user,
            is_active=True
        )
        for config in configs:
            table_configs[config.db_table_name] = {
                'process_order': config.process_order,
                'work_group': config.work_group
            }

        # 매핑 정보 가져오기
        mappings = MappingInfo.objects.filter(
            declaration=declaration,
            is_active=True
        ).order_by('priority')

        mapping_info = []

        for mapping in mappings:
            # 기본 프롬프트
            basic_prompt = PromptConfig.objects.filter(
                mapping=mapping,
                prompt_type='basic',
                service_user__isnull=True,
                is_active=True
            ).first()

            # 추가 프롬프트
            additional_prompt = PromptConfig.objects.filter(
                mapping=mapping,
                prompt_type='additional',
                service_user=service_user,
                is_active=True
            ).first()

            # 테이블 처리 설정 정보 (테이블명으로 조회)
            process_order = None
            work_group = None
            table_config = table_configs.get(mapping.db_table_name)
            if table_config:
                process_order = table_config['process_order']
                work_group = table_config['work_group']

            # 매핑 정보에 프롬프트 및 처리 순서 포함
            mapping_info.append({
                'unipass_field_name': mapping.unipass_field_name,
                'db_table_name': mapping.db_table_name,
                'db_field_name': mapping.db_field_name,
                'basic_prompt': basic_prompt.prompt_text if basic_prompt else None,
                'additional_prompt': additional_prompt.prompt_text if additional_prompt else None,
                'process_order': process_order,
                'work_group': work_group
            })

        # AI 메타데이터 (최상위 프롬프트)
        ai_metadata = declaration.description if declaration.description else None

        # 순차 처리 여부 확인
        has_process_order = any(mapping.get('process_order') is not None for mapping in mapping_info)

        # 매핑 정보 출력 (순차 처리가 아닐 때만 상세 출력)
        logger.info("\n" + "="*80)
        logger.info("[MAPPING INFO]")
        logger.info("="*80)
        logger.info(f"Service: {service.name} ({service.slug})")
        logger.info(f"Declaration: {declaration.name} ({declaration.code})")
        logger.info(f"AI Engine: {'Gemini' if ai_engine == 'gemini' else 'ChatGPT'}")
        logger.info(f"AI Metadata: {ai_metadata}")
        logger.info(f"Total {len(mapping_info)} field mappings")

        if has_process_order:
            # 순차 처리 시에는 간략하게
            ordered_count = sum(1 for m in mapping_info if m.get('process_order') is not None)
            logger.info(f"  - Ordered mappings: {ordered_count}")
            logger.info(f"  - Unordered mappings: {len(mapping_info) - ordered_count}")
            logger.info("  (Detailed mapping info will be shown in each step)")
        else:
            # 일괄 처리 시에는 전체 출력
            for idx, mapping in enumerate(mapping_info, 1):
                logger.info(f"\n  [{idx}] {mapping['unipass_field_name']}")
                logger.info(f"      -> DB: {mapping['db_table_name']}.{mapping['db_field_name']}")
                if mapping.get('basic_prompt'):
                    logger.info(f"      -> Basic Prompt: {mapping['basic_prompt'][:50]}...")
                if mapping.get('additional_prompt'):
                    logger.info(f"      -> Additional Prompt: {mapping['additional_prompt'][:50]}...")

        logger.info("="*80 + "\n")

        # 인보이스 처리 (AI 엔진 선택)
        use_gemini = ai_engine == 'gemini'
        processor = InvoiceProcessor(use_gemini=use_gemini)
        result = processor.process(
            image_path=image_path,
            mapping_info=mapping_info,
            ai_metadata=ai_metadata
        )

        # 로그 업데이트
        process_log.ocr_text = result.get('ocr_text')
        process_log.gpt_response = result.get('gpt_response')
        process_log.result_json = result.get('result_json')
        process_log.processing_time = result.get('processing_time')

        if result['success']:
            process_log.status = 'completed'
            process_log.completed_at = timezone.now()
        else:
            process_log.status = 'failed'
            process_log.error_message = result.get('error')

        process_log.save()

        # Step 5: 응답 반환
        response_data = {
            'success': result['success'],
            'data': result.get('result_json'),
            'ocr_text': result.get('ocr_text'),
            'processing_time': result.get('processing_time'),
            'log_id': process_log.id,
            'ai_engine': 'Gemini' if use_gemini else 'ChatGPT',
            'ai_metadata': ai_metadata,
            'mapping_info': mapping_info,
            'prompt': result.get('prompt'),
            'steps': result.get('steps'),  # 단계별 프롬프트 및 응답
            'total_steps': result.get('total_steps'),  # 총 단계 수
            'hs_code_recommendation': result.get('hs_code_recommendation'),
            'hs_prompt': result.get('hs_prompt'),
            'error': result.get('error')
        }

        # 응답 출력
        logger.info("\n" + "="*80)
        logger.info("[API RESPONSE]")
        logger.info("="*80)
        logger.info(f"Success: {response_data['success']}")
        logger.info(f"Processing Time: {response_data['processing_time']:.2f}s")
        logger.info(f"Log ID: {response_data['log_id']}")
        logger.info(f"AI Engine: {response_data['ai_engine']}")
        if response_data.get('total_steps'):
            logger.info(f"Total Steps: {response_data['total_steps']}")

        # 단계별 정보 출력
        if response_data.get('steps'):
            logger.info(f"\nStep-by-Step Processing Details:")
            for step in response_data['steps']:
                logger.info(f"\n  [Step {step['step']}/{response_data.get('total_steps', '?')}] {step['work_group']} (Order: {step['order']})")
                logger.info(f"  - Mapping Count: {step['mapping_count']}")

                # 이 단계의 매핑 목록 출력
                if step.get('mappings'):
                    logger.info(f"  - Mappings in this step:")
                    for idx, m in enumerate(step['mappings'], 1):
                        logger.info(f"      {idx}. {m['unipass_field_name']} -> {m['db_table_name']}.{m['db_field_name']}")

                logger.info(f"  - Has Prompt: {'Yes' if step.get('prompt') else 'No'}")
                logger.info(f"  - Has Response: {'Yes' if step.get('response') else 'No'}")

        if response_data.get('error'):
            logger.info(f"Error: {response_data['error']}")
        if response_data.get('data'):
            logger.info(f"\nExtracted Data:")
            logger.info(f"[DEBUG api/views.py:213] response_data['data'] type: {type(response_data['data'])}")
            logger.info(f"[DEBUG api/views.py:214] response_data['data'] value: {response_data['data']}")
            try:
                if isinstance(response_data['data'], dict):
                    logger.info(f"[DEBUG api/views.py:217] Iterating dict with .items()")
                    for key, value in response_data['data'].items():
                        logger.info(f"  - {key}: {value}")
                elif isinstance(response_data['data'], list):
                    logger.info(f"[DEBUG api/views.py:221] Iterating list")
                    for item in response_data['data']:
                        logger.info(f"  - {item}")
                else:
                    logger.info(f"[DEBUG api/views.py:225] Other type, printing directly")
                    logger.info(f"  {response_data['data']}")
            except Exception as e:
                logger.error(f"[ERROR api/views.py:228] Error while logging data: {str(e)}")
                logger.error(f"[ERROR api/views.py:229] Data type: {type(response_data['data'])}")
                logger.error(f"[ERROR api/views.py:230] Data value: {response_data['data']}")
        logger.info("="*80 + "\n")

        return Response(response_data, status=status.HTTP_200_OK if result['success'] else status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        # 오류 처리
        process_log.status = 'failed'
        process_log.error_message = str(e)
        process_log.save()

        return Response(
            {'success': False, 'error': str(e), 'log_id': process_log.id},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_process_log(request, log_id):
    """
    처리 로그 조회 API

    Parameters:
    - log_id: 처리 로그 ID

    Response:
    - 처리 로그 상세 정보
    """
    process_log = get_object_or_404(InvoiceProcessLog, pk=log_id)

    # 권한 확인
    if request.user.user_type != 'admin':
        if process_log.service_user.user != request.user:
            return Response(
                {'success': False, 'error': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

    return Response({
        'success': True,
        'data': {
            'id': process_log.id,
            'service': process_log.service_user.service.name,
            'declaration': process_log.declaration.name,
            'status': process_log.status,
            'ocr_text': process_log.ocr_text,
            'result_json': process_log.result_json,
            'error_message': process_log.error_message,
            'processing_time': process_log.processing_time,
            'created_at': process_log.created_at,
            'completed_at': process_log.completed_at,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_process_logs(request):
    """
    처리 로그 목록 조회 API

    Query Parameters:
    - service_user_id: 서비스 사용자 ID (optional)
    - declaration_id: 신고서 ID (optional)
    - status: 상태 (optional)
    - limit: 결과 개수 제한 (default: 50)

    Response:
    - 처리 로그 목록
    """
    logs = InvoiceProcessLog.objects.all()

    # 권한에 따른 필터링
    if request.user.user_type != 'admin':
        logs = logs.filter(service_user__user=request.user)

    # 필터 적용
    service_user_id = request.query_params.get('service_user_id')
    if service_user_id:
        logs = logs.filter(service_user_id=service_user_id)

    declaration_id = request.query_params.get('declaration_id')
    if declaration_id:
        logs = logs.filter(declaration_id=declaration_id)

    log_status = request.query_params.get('status')
    if log_status:
        logs = logs.filter(status=log_status)

    # 개수 제한
    limit = int(request.query_params.get('limit', 50))
    logs = logs.order_by('-created_at')[:limit]

    # 데이터 구성
    data = []
    for log in logs:
        data.append({
            'id': log.id,
            'service': log.service_user.service.name,
            'declaration': log.declaration.name,
            'status': log.status,
            'processing_time': log.processing_time,
            'created_at': log.created_at,
            'completed_at': log.completed_at,
            'has_error': bool(log.error_message),
        })

    return Response({
        'success': True,
        'count': len(data),
        'data': data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_declaration_config(request, declaration_id):
    """
    신고서 설정 조회 API

    Parameters:
    - declaration_id: 신고서 ID

    Query Parameters:
    - service_user_id: 서비스 사용자 ID

    Response:
    - 매핑 정보 및 프롬프트 설정
    """
    declaration = get_object_or_404(Declaration, pk=declaration_id)
    service_user_id = request.query_params.get('service_user_id')

    if not service_user_id:
        return Response(
            {'success': False, 'error': 'service_user_id가 필요합니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    service_user = get_object_or_404(ServiceUser, pk=service_user_id)

    # 권한 확인
    if request.user.user_type != 'admin':
        if service_user.user != request.user:
            return Response(
                {'success': False, 'error': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

    # 테이블 처리 설정 정보 가져오기 (테이블명으로 매칭)
    table_configs = {}
    configs = TableProcessConfig.objects.filter(
        declaration=declaration,
        service_user=service_user,
        is_active=True
    )
    for config in configs:
        table_configs[config.db_table_name] = {
            'process_order': config.process_order,
            'work_group': config.work_group
        }

    # 매핑 정보 가져오기
    mappings = MappingInfo.objects.filter(
        declaration=declaration,
        is_active=True
    ).order_by('priority')

    mapping_data = []
    for mapping in mappings:
        # 기본 프롬프트
        basic_prompt = PromptConfig.objects.filter(
            mapping=mapping,
            prompt_type='basic',
            service_user__isnull=True,
            is_active=True
        ).first()

        # 추가 프롬프트
        additional_prompt = PromptConfig.objects.filter(
            mapping=mapping,
            prompt_type='additional',
            service_user=service_user,
            is_active=True
        ).first()

        # 테이블 처리 설정 정보 (테이블명으로 조회)
        process_order = None
        work_group = None
        table_config = table_configs.get(mapping.db_table_name)
        if table_config:
            process_order = table_config['process_order']
            work_group = table_config['work_group']

        mapping_data.append({
            'id': mapping.id,
            'unipass_field_name': mapping.unipass_field_name,
            'db_table_name': mapping.db_table_name,
            'db_field_name': mapping.db_field_name,
            'priority': mapping.priority,
            'basic_prompt': basic_prompt.prompt_text if basic_prompt else None,
            'additional_prompt': additional_prompt.prompt_text if additional_prompt else None,
            'process_order': process_order,
            'work_group': work_group,
        })

    return Response({
        'success': True,
        'declaration': {
            'id': declaration.id,
            'name': declaration.name,
            'type': declaration.declaration_type,
        },
        'service': {
            'id': service_user.service.id,
            'name': service_user.service.name,
        },
        'mappings': mapping_data
    })

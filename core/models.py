from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    """
    커스텀 사용자 모델
    - admin: 관리자 계정
    - 관세사: 관세사부호 5자리를 username으로 사용
    """
    USER_TYPE_CHOICES = [
        ('admin', '관리자'),
        ('customs', '관세사'),
    ]

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='customs')
    customs_code = models.CharField(max_length=5, blank=True, null=True, unique=True,
                                   verbose_name='관세사부호')
    customs_name = models.CharField(max_length=100, blank=True, null=True,
                                   verbose_name='관세사명')
    is_first_login = models.BooleanField(default=True, verbose_name='최초 로그인 여부')

    class Meta:
        db_table = 'users'
        verbose_name = '사용자'
        verbose_name_plural = '사용자'

    def __str__(self):
        if self.user_type == 'admin':
            return f"관리자 - {self.username}"
        return f"{self.customs_name} ({self.customs_code})"


class Service(models.Model):
    """
    서비스 모델 (RK통관, 협회통관, HelpManager 등)
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='서비스명')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='영문명')
    description = models.TextField(blank=True, null=True, verbose_name='설명')

    # DB 접속 정보
    db_host = models.CharField(max_length=255, blank=True, null=True, verbose_name='DB 호스트')
    db_port = models.CharField(max_length=10, blank=True, null=True, verbose_name='DB 포트')
    db_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='DB 이름')
    db_user = models.CharField(max_length=100, blank=True, null=True, verbose_name='DB 사용자')
    db_password = models.CharField(max_length=255, blank=True, null=True, verbose_name='DB 비밀번호')

    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        db_table = 'services'
        verbose_name = '서비스'
        verbose_name_plural = '서비스'
        ordering = ['name']

    def __str__(self):
        return self.name


class ServiceUser(models.Model):
    """
    서비스와 관세사 연결 테이블
    - '기본' 항목은 user가 null인 경우
    """
    service = models.ForeignKey(Service, on_delete=models.CASCADE,
                               related_name='service_users', verbose_name='서비스')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                            blank=True, null=True,
                            related_name='service_users', verbose_name='관세사')
    is_default = models.BooleanField(default=False, verbose_name='기본 설정 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')

    class Meta:
        db_table = 'service_users'
        verbose_name = '서비스 사용자'
        verbose_name_plural = '서비스 사용자'
        unique_together = ['service', 'user']

    def __str__(self):
        if self.is_default or not self.user:
            return f"{self.service.name} - 기본"
        return f"{self.service.name} - {self.user.customs_name}"


class Declaration(models.Model):
    """
    신고서 모델 (수출신고서, 수입신고서 등)
    """
    DECLARATION_TYPE_CHOICES = [
        ('export', '수출신고서'),
        ('import', '수입신고서'),
        ('correction', '수출정정'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE,
                               related_name='declarations', verbose_name='서비스')
    name = models.CharField(max_length=100, verbose_name='신고서명')
    code = models.CharField(max_length=50, unique=True, verbose_name='신고서 코드')
    declaration_type = models.CharField(max_length=20, choices=DECLARATION_TYPE_CHOICES,
                                       blank=True, null=True, verbose_name='신고서 유형')
    description = models.TextField(blank=True, null=True, verbose_name='설명')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        db_table = 'declarations'
        verbose_name = '신고서'
        verbose_name_plural = '신고서'
        ordering = ['service', 'name']

    def __str__(self):
        return f"{self.service.name} - {self.name}"


class MappingInfo(models.Model):
    """
    매핑정보 모델
    유니패스 정의서의 항목명 : DB 테이블 필드 매핑
    """
    FIELD_TYPE_CHOICES = [
        ('string', '문자열'),
        ('number', '숫자'),
        ('date', '날짜'),
        ('datetime', '날짜시간'),
        ('boolean', '참/거짓'),
    ]

    declaration = models.ForeignKey(Declaration, on_delete=models.CASCADE,
                                   related_name='mappings', verbose_name='신고서')
    service_user = models.ForeignKey(ServiceUser, on_delete=models.CASCADE,
                                    blank=True, null=True,
                                    related_name='mappings', verbose_name='서비스 사용자')

    # 매핑 정보
    unipass_field_name = models.CharField(max_length=200, verbose_name='유니패스 항목명')
    db_table_name = models.CharField(max_length=100, verbose_name='DB 테이블명')
    db_field_name = models.CharField(max_length=100, verbose_name='DB 필드명')

    # 필드 상세 정보
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES,
                                  default='string', verbose_name='필드 타입')
    field_length = models.IntegerField(blank=True, null=True, verbose_name='필드 길이')

    # 우선순위 (같은 항목에 대해 여러 매핑이 있을 경우)
    priority = models.IntegerField(default=0, verbose_name='우선순위')

    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        db_table = 'mapping_info'
        verbose_name = '매핑정보'
        verbose_name_plural = '매핑정보'
        ordering = ['declaration', 'priority']

    def __str__(self):
        return f"{self.unipass_field_name} -> {self.db_table_name}.{self.db_field_name}"


class PromptConfig(models.Model):
    """
    프롬프트 설정 모델
    - 기본 입력항목: admin만 수정 가능, 모든 관세사에 일괄 반영
    - 추가 입력항목: admin 또는 해당 관세사만 수정 가능
    """
    PROMPT_TYPE_CHOICES = [
        ('basic', '기본 입력항목'),
        ('additional', '추가 입력항목'),
    ]

    mapping = models.ForeignKey(MappingInfo, on_delete=models.CASCADE,
                               related_name='prompts', verbose_name='매핑정보')
    prompt_type = models.CharField(max_length=20, choices=PROMPT_TYPE_CHOICES,
                                  verbose_name='프롬프트 유형')

    # 프롬프트 내용
    prompt_text = models.TextField(verbose_name='프롬프트 내용')

    # 기본 입력항목의 경우 service_user가 null
    # 추가 입력항목의 경우 특정 service_user에 할당
    service_user = models.ForeignKey(ServiceUser, on_delete=models.CASCADE,
                                    blank=True, null=True,
                                    related_name='prompts', verbose_name='서비스 사용자')

    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                                  null=True, related_name='created_prompts',
                                  verbose_name='생성자')

    class Meta:
        db_table = 'prompt_configs'
        verbose_name = '프롬프트 설정'
        verbose_name_plural = '프롬프트 설정'
        unique_together = ['mapping', 'prompt_type', 'service_user']

    def __str__(self):
        prompt_type_display = dict(self.PROMPT_TYPE_CHOICES)[self.prompt_type]
        return f"{self.mapping} - {prompt_type_display}"


class InvoiceProcessLog(models.Model):
    """
    인보이스 처리 로그
    API 요청/응답 기록
    """
    STATUS_CHOICES = [
        ('pending', '처리 대기'),
        ('processing', '처리 중'),
        ('completed', '완료'),
        ('failed', '실패'),
    ]

    service_user = models.ForeignKey(ServiceUser, on_delete=models.CASCADE,
                                    related_name='process_logs', verbose_name='서비스 사용자')
    declaration = models.ForeignKey(Declaration, on_delete=models.CASCADE,
                                   related_name='process_logs', verbose_name='신고서')

    # 이미지 파일
    image_file = models.ImageField(upload_to='invoices/%Y/%m/%d/', verbose_name='인보이스 이미지')

    # OCR 결과
    ocr_text = models.TextField(blank=True, null=True, verbose_name='OCR 추출 텍스트')

    # ChatGPT 요청/응답
    gpt_request = models.TextField(blank=True, null=True, verbose_name='GPT 요청')
    gpt_response = models.TextField(blank=True, null=True, verbose_name='GPT 응답')

    # 최종 JSON 결과
    result_json = models.JSONField(blank=True, null=True, verbose_name='결과 JSON')

    # 처리 상태
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                             default='pending', verbose_name='처리 상태')
    error_message = models.TextField(blank=True, null=True, verbose_name='에러 메시지')

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='완료일시')

    # 처리 시간 (초)
    processing_time = models.FloatField(blank=True, null=True, verbose_name='처리 시간')

    class Meta:
        db_table = 'invoice_process_logs'
        verbose_name = '인보이스 처리 로그'
        verbose_name_plural = '인보이스 처리 로그'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.declaration.name} - {self.status} ({self.created_at})"

# Invoice 자동 인식 시스템

생성형 AI(ChatGPT)와 OCR 기술을 이용한 Invoice 자동 인식 및 DB 연동 시스템

## 기술 스택

- **Backend**: Django 4.2 (Python MVT 패턴)
- **Database**: Microsoft SQL Server (MSSQL)
- **OCR**: Google Cloud Vision API
- **AI**: OpenAI ChatGPT API (GPT-4 Vision)
- **Frontend**: HTML/CSS (Toss Design System)

## 주요 기능

### 1. 인증 시스템
- 관리자 계정 (admin) 및 관세사 계정 (관세사부호 5자리)
- 최초 로그인 시 비밀번호 변경 필수
- 기본 계정:
  - 관리자: `admin` / `P@ssw0rd`
  - 관세사: 관세사부호 / `init123` (최초)

### 2. 서비스 관리 (관리자)
- 서비스 목록 카드 형식 표시
- 서비스별 업체(관세사) 목록 관리
- '기본' 설정 프로필 지원

### 3. 신고서 관리
- 수출신고서, 수입신고서, 수출정정 등
- 매핑정보 관리 (유니패스 항목명 ↔ DB 필드)
- 기본 입력항목: admin만 수정 가능, 전체 반영
- 추가 입력항목: 해당 관세사만 수정 가능

### 4. AI 기반 Invoice 처리
**처리 파이프라인:**
1. API 서버로 Invoice 이미지 전달 (Request)
2. Google Vision OCR로 텍스트 추출
3. ChatGPT로 이미지 + 텍스트 인식
4. GPT가 매핑정보에 맞게 JSON 데이터 정리
5. 정리된 JSON 데이터 반환 (Response)

## 설치 및 실행

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example`을 복사하여 `.env` 파일 생성:

```bash
copy .env.example .env
```

`.env` 파일에 필요한 값 입력:
- `DJANGO_SECRET_KEY`: Django 시크릿 키
- `DB_*`: MSSQL 데이터베이스 연결 정보
- `GOOGLE_VISION_CREDENTIALS`: Google Vision API 인증 파일 경로
- `OPENAI_API_KEY`: OpenAI API 키

### 3. 데이터베이스 마이그레이션

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. 초기 데이터 생성

관리자 계정 생성:

```bash
python manage.py createsuperuser
# Username: admin
# Password: P@ssw0rd
```

또는 Django Shell에서:

```bash
python manage.py shell
```

```python
from core.models import CustomUser, Service, ServiceUser

# 관리자 계정
admin = CustomUser.objects.create_user(
    username='admin',
    password='P@ssw0rd',
    user_type='admin',
    is_staff=True,
    is_superuser=True,
    is_first_login=False
)

# 관세사 계정 예시
customs_user = CustomUser.objects.create_user(
    username='6N001',
    password='init123',
    user_type='customs',
    customs_code='6N001',
    customs_name='A관세사',
    is_first_login=True
)

# 서비스 생성 예시
service = Service.objects.create(
    name='RK통관',
    description='RK통관 서비스'
)

# 서비스-사용자 연결 (기본)
ServiceUser.objects.create(
    service=service,
    user=None,
    is_default=True
)

# 서비스-사용자 연결 (관세사)
ServiceUser.objects.create(
    service=service,
    user=customs_user,
    is_default=False
)
```

### 5. 서버 실행
# cd C:\Users\erid3\workspace\INVOICE
```bash
python manage.py runserver
```

브라우저에서 `http://localhost:8000` 접속

## API 사용법

### 1. 인보이스 처리 API

**Endpoint:** `POST /api/process/`

**Request:**
```bash
curl -X POST http://localhost:8000/api/process/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image=@invoice.jpg" \
  -F "service_user_id=1" \
  -F "declaration_id=1"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "신고번호": "Rpt_num",
    "시리얼번호": "SN",
    "품명": "상품명"
  },
  "ocr_text": "추출된 텍스트...",
  "processing_time": 5.23,
  "log_id": 123
}
```

### 2. 처리 로그 조회 API

**Endpoint:** `GET /api/logs/`

**Query Parameters:**
- `service_user_id`: 서비스 사용자 ID (optional)
- `declaration_id`: 신고서 ID (optional)
- `status`: 상태 (pending/processing/completed/failed) (optional)
- `limit`: 결과 개수 제한 (default: 50)

### 3. 신고서 설정 조회 API

**Endpoint:** `GET /api/declaration/{declaration_id}/config/?service_user_id=1`

## 프로젝트 구조

```
INVOICE/
├── invoice_system/          # Django 프로젝트 설정
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                    # 핵심 앱
│   ├── models.py           # 데이터베이스 모델
│   ├── views.py            # 웹 뷰
│   ├── forms.py            # 폼
│   ├── services.py         # OCR/ChatGPT 서비스
│   ├── admin.py            # Django Admin
│   └── urls.py
├── api/                     # REST API 앱
│   ├── views.py            # API 뷰
│   └── urls.py
├── templates/               # HTML 템플릿
│   ├── base.html
│   └── core/
│       ├── login.html
│       ├── dashboard.html
│       ├── service_list.html
│       └── ...
├── static/                  # 정적 파일
├── media/                   # 업로드 파일
├── manage.py
├── requirements.txt
└── .env
```

## 데이터베이스 모델

### CustomUser
- 사용자 (관리자/관세사)
- 관세사부호, 관세사명

### Service
- 서비스 (RK통관, 협회통관, HelpManager 등)

### ServiceUser
- 서비스와 사용자 연결
- 기본 설정 지원

### Declaration
- 신고서 (수출신고서, 수입신고서 등)

### MappingInfo
- 매핑정보 (유니패스 항목 ↔ DB 필드)

### PromptConfig
- 프롬프트 설정 (기본/추가 입력항목)

### InvoiceProcessLog
- 인보이스 처리 로그

## 디자인 시스템

Toss Design System 기반:
- 깔끔하고 직관적인 UI
- 카드 기반 레이아웃
- Soft Blue 톤 컬러
- 부드러운 그라데이션 효과
- 명확한 CTA 버튼

## 라이선스

Proprietary

## 문의

eRequest 문의: support@erequest.com

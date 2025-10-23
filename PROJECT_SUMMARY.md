# Invoice 자동 인식 시스템 - 프로젝트 요약

## 📋 프로젝트 개요

생성형 AI(ChatGPT)와 OCR 기술을 활용하여 Invoice를 자동으로 인식하고 데이터베이스와 연동하는 웹 기반 관리 시스템입니다.

## 🎯 핵심 기능

### 1. 사용자 인증 및 권한 관리
- **관리자 계정**: 모든 서비스 및 관세사 관리
- **관세사 계정**: 관세사부호(5자리) 기반 인증
- **최초 로그인 시 비밀번호 변경 강제**
- 기본 계정:
  - 관리자: `admin` / `P@ssw0rd`
  - 관세사: 관세사부호 / `init123`

### 2. 서비스 관리 (관리자 전용)
- 서비스 목록을 카드 형식으로 표시
- 각 서비스별 업체(관세사) 관리
- '기본' 설정 프로필 지원

### 3. 신고서 관리
- **신고서 유형**: 수출신고서, 수입신고서, 수출정정 등
- **매핑정보 관리**: 유니패스 항목명 ↔ DB 필드 매핑
- **기본 입력항목**: admin만 수정, 전체 관세사에 일괄 반영
- **추가 입력항목**: 해당 관세사만 개별 수정 가능

### 4. AI 기반 Invoice 자동 처리
**5단계 처리 파이프라인:**
1. **Request**: API 서버로 Invoice 이미지 전달
2. **OCR**: Google Vision API로 텍스트 추출
3. **AI 분석**: ChatGPT (GPT-4 Vision)로 이미지 + 텍스트 인식
4. **JSON 변환**: 매핑정보에 맞게 데이터 구조화
5. **Response**: 정리된 JSON 데이터 반환

## 🏗️ 기술 스택

### Backend
- **Framework**: Django 4.2 (Python MVT 패턴)
- **API**: Django REST Framework
- **Database**: Microsoft SQL Server (MSSQL)
- **Authentication**: Django Session Auth

### AI/ML
- **OCR**: Google Cloud Vision API
- **AI**: OpenAI GPT-4 Vision
- **Image Processing**: Pillow

### Frontend
- **Design System**: Toss Design System
- **Layout**: 카드 기반, 반응형 디자인
- **Color Scheme**: Soft Blue Tone, Gradient Effects
- **Components**: HTML5, CSS3, Vanilla JavaScript

## 📁 프로젝트 구조

```
INVOICE/
├── invoice_system/          # Django 프로젝트 설정
│   ├── settings.py         # 전역 설정
│   ├── urls.py             # URL 라우팅
│   └── wsgi.py             # WSGI 설정
│
├── core/                    # 핵심 앱 (웹 UI)
│   ├── models.py           # 데이터베이스 모델
│   ├── views.py            # 웹 뷰 (로그인, 대시보드 등)
│   ├── forms.py            # 폼 (로그인, 비밀번호 변경)
│   ├── services.py         # OCR/ChatGPT 통합 서비스
│   ├── admin.py            # Django Admin 설정
│   └── urls.py             # URL 패턴
│
├── api/                     # REST API 앱
│   ├── views.py            # API 뷰 (Invoice 처리 등)
│   └── urls.py             # API URL 패턴
│
├── templates/               # HTML 템플릿
│   ├── base.html           # 베이스 템플릿
│   └── core/
│       ├── login.html              # 로그인 페이지
│       ├── change_password.html    # 비밀번호 변경
│       ├── dashboard.html          # 대시보드
│       ├── service_list.html       # 서비스 리스트
│       ├── service_detail.html     # 서비스 상세
│       ├── declaration_list.html   # 신고서 리스트
│       └── declaration_detail.html # 신고서 상세 (매핑/프롬프트)
│
├── static/                  # 정적 파일 (CSS, JS, Images)
├── media/                   # 업로드 파일 (Invoice 이미지)
│
├── manage.py               # Django 관리 스크립트
├── requirements.txt        # Python 패키지 목록
├── .env.example            # 환경 변수 예시
├── .gitignore             # Git 제외 파일
│
├── README.md              # 프로젝트 설명서
├── API_DOCUMENTATION.md   # API 문서
├── DEPLOYMENT_GUIDE.md    # 배포 가이드
├── PROJECT_SUMMARY.md     # 프로젝트 요약 (이 파일)
│
├── setup_initial_data.py  # 초기 데이터 설정 스크립트
└── test_setup.py          # 설정 테스트 스크립트
```

## 🗄️ 데이터베이스 스키마

### CustomUser (사용자)
- `user_type`: admin / customs
- `customs_code`: 관세사부호 (5자리)
- `customs_name`: 관세사명
- `is_first_login`: 최초 로그인 여부

### Service (서비스)
- `name`: 서비스명 (RK통관, 협회통관 등)
- `description`: 설명
- `is_active`: 활성화 여부

### ServiceUser (서비스-사용자 연결)
- `service`: 서비스 FK
- `user`: 사용자 FK (null 가능 - '기본' 설정)
- `is_default`: 기본 설정 여부

### Declaration (신고서)
- `service`: 서비스 FK
- `name`: 신고서명
- `declaration_type`: export / import / correction
- `description`: 설명

### MappingInfo (매핑정보)
- `declaration`: 신고서 FK
- `service_user`: 서비스 사용자 FK
- `unipass_field_name`: 유니패스 항목명
- `db_table_name`: DB 테이블명
- `db_field_name`: DB 필드명
- `priority`: 우선순위

### PromptConfig (프롬프트 설정)
- `mapping`: 매핑정보 FK
- `prompt_type`: basic / additional
- `prompt_text`: 프롬프트 내용
- `service_user`: 서비스 사용자 FK (null이면 기본 프롬프트)
- `created_by`: 생성자

### InvoiceProcessLog (처리 로그)
- `service_user`: 서비스 사용자 FK
- `declaration`: 신고서 FK
- `image_file`: Invoice 이미지 파일
- `ocr_text`: OCR 추출 텍스트
- `gpt_request`: GPT 요청 내용
- `gpt_response`: GPT 응답 내용
- `result_json`: 최종 JSON 결과
- `status`: pending / processing / completed / failed
- `processing_time`: 처리 시간(초)

## 🎨 UI/UX 디자인 (Toss Design System)

### 디자인 원칙
- **간편함**: 직관적이고 이해하기 쉬운 UI
- **신뢰감**: 안정적인 블루 톤 사용
- **친근함**: 부드러운 그라데이션과 라운드 모서리

### 주요 컬러
- Primary Blue: `#3182F6`
- Background: `#F9FAFB`
- Card Background: `#FFFFFF`
- Text Primary: `#191F28`
- Text Secondary: `#4E5968`

### 컴포넌트
- **카드**: 12px 라운드, 섀도우 효과
- **버튼**: 8px 라운드, 호버 시 lift 효과
- **폼 입력**: 14px 패딩, 포커스 시 블루 보더
- **알림**: 컬러별 구분 (에러, 성공, 정보)

## 🔌 API 엔드포인트

### 1. POST /api/process/
Invoice 이미지 처리 (OCR + AI 분석)

**Request:**
```json
{
  "image": "file",
  "service_user_id": 1,
  "declaration_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "신고번호": "2024-01-12345",
    "시리얼번호": "SN-12345",
    ...
  },
  "ocr_text": "...",
  "processing_time": 5.23,
  "log_id": 123
}
```

### 2. GET /api/logs/
처리 로그 목록 조회

### 3. GET /api/logs/{log_id}/
특정 로그 상세 조회

### 4. GET /api/declaration/{declaration_id}/config/
신고서 설정 조회 (매핑정보 + 프롬프트)

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정
copy .env.example .env
# .env 파일 편집
```

### 2. 데이터베이스 설정
```bash
# 마이그레이션
python manage.py makemigrations
python manage.py migrate

# 초기 데이터 생성
python manage.py shell < setup_initial_data.py
```

### 3. 서버 실행
```bash
python manage.py runserver
```

브라우저에서 `http://localhost:8000` 접속

## 📊 화면 구성

### 1. 로그인 페이지
- 중앙 정렬 로그인 폼
- 아이디/비밀번호 입력
- eRequest 문의 버튼
- 로그인 정보 안내

### 2. 비밀번호 변경 페이지 (최초 로그인)
- 새 비밀번호 입력
- 비밀번호 확인
- 비밀번호 정책 안내

### 3. 대시보드 (관세사)
- 환영 메시지
- 할당된 서비스 카드 리스트
- 각 서비스 클릭 → 신고서 관리

### 4. 서비스 리스트 (관리자)
- 서비스 카드 그리드
- 각 서비스 클릭 → 업체 리스트

### 5. 서비스 상세 (관리자)
- 해당 서비스의 업체 리스트
- '기본' 항목 표시
- 관세사 정보 표시

### 6. 신고서 리스트
- 신고서 카드 그리드
- 신고서 유형 표시
- 클릭 → 신고서 상세 (매핑/프롬프트)

### 7. 신고서 상세
- 매핑정보 리스트
- 기본 입력항목 (admin만 수정)
- 추가 입력항목 (관세사 수정)
- 매핑 추가 기능
- AJAX 저장

## 🔐 보안 고려사항

### 인증 및 권한
- Django Session 기반 인증
- CSRF 토큰 보호
- 최초 로그인 시 비밀번호 변경 강제
- 권한별 접근 제어 (admin / customs)

### API 보안
- 인증된 사용자만 API 접근
- 권한 검증 (service_user 소유권)
- CORS 설정

### 데이터 보안
- 비밀번호 해싱 (Django 기본)
- API 키 환경 변수 분리
- 민감 정보 .gitignore 처리

## 📈 성능 최적화

### 데이터베이스
- 적절한 인덱스 설정
- Foreign Key 관계 최적화
- select_related / prefetch_related 사용

### API 응답
- JSON 직렬화 최적화
- 불필요한 데이터 제외
- 페이지네이션 (로그 조회)

### 이미지 처리
- 이미지 크기 제한 (10MB)
- 효율적인 파일 저장 구조
- 미디어 파일 정리 스케줄링

## 🧪 테스트 및 검증

### 설정 테스트
```bash
python manage.py shell < test_setup.py
```

### 수동 테스트 체크리스트
- [ ] 로그인 (관리자/관세사)
- [ ] 비밀번호 변경
- [ ] 서비스 리스트 표시
- [ ] 신고서 관리 페이지
- [ ] 매핑정보 추가
- [ ] 프롬프트 저장
- [ ] API Invoice 처리
- [ ] 로그 조회

## 📝 추가 개발 계획 (향후)

### Phase 2 기능
- [ ] 배치 처리 (여러 Invoice 동시 처리)
- [ ] 처리 이력 통계 대시보드
- [ ] Export 기능 (Excel, CSV)
- [ ] 템플릿 관리 (자주 사용하는 매핑)
- [ ] 알림 시스템 (이메일, SMS)

### Phase 3 기능
- [ ] 실시간 처리 상태 (WebSocket)
- [ ] 모바일 앱 연동
- [ ] AI 학습 데이터 수집
- [ ] 정확도 개선 피드백 시스템
- [ ] 다국어 지원

## 👥 팀 및 역할

### 개발팀
- **Backend**: Django, API, Database
- **AI/ML**: OCR, ChatGPT 통합
- **Frontend**: UI/UX, Toss Design System
- **DevOps**: 배포, 모니터링

### 운영팀
- **관리자**: 시스템 설정 및 관리
- **관세사**: Invoice 처리 및 설정

## 📞 문의 및 지원

- **기술 지원**: support@erequest.com
- **API 문의**: api@erequest.com
- **배포 문의**: devops@erequest.com

## 📄 라이선스

Proprietary - All rights reserved

---

**마지막 업데이트**: 2024-01-15
**버전**: 1.0.0
**작성자**: Invoice System Development Team

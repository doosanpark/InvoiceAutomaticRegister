# Invoice 자동 인식 시스템 - 문서 인덱스

## 📚 프로젝트 문서 목록

### 🚀 시작하기
| 문서 | 설명 | 대상 |
|------|------|------|
| **[QUICK_START.md](QUICK_START.md)** | 5분 안에 시작하기 가이드 | 모든 사용자 |
| **[README.md](README.md)** | 프로젝트 전체 설명서 | 개발자, 운영자 |
| **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** | 프로젝트 요약 및 기능 소개 | 관리자, PM |

### 📖 기술 문서
| 문서 | 설명 | 대상 |
|------|------|------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | 시스템 아키텍처 다이어그램 | 개발자, 아키텍트 |
| **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** | REST API 사용 가이드 | API 사용자, 개발자 |
| **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** | 배포 및 운영 가이드 | DevOps, 운영자 |

### 🛠️ 설정 및 스크립트
| 파일 | 설명 | 사용법 |
|------|------|--------|
| **setup_initial_data.py** | 초기 데이터 설정 스크립트 | `python manage.py shell < setup_initial_data.py` |
| **test_setup.py** | 시스템 설정 검증 스크립트 | `python manage.py shell < test_setup.py` |
| **.env.example** | 환경 변수 예시 파일 | `.env`로 복사 후 편집 |

### 📋 디자인 참고
| 파일 | 설명 |
|------|------|
| **toss_design_system.md** | Toss 디자인 시스템 가이드 |
| **site1.png, site2.png, site3.png** | 페이지 설계 참고 이미지 |

---

## 🗂️ 프로젝트 구조

```
INVOICE/
├── 📄 문서
│   ├── INDEX.md (이 파일)
│   ├── QUICK_START.md
│   ├── README.md
│   ├── PROJECT_SUMMARY.md
│   ├── ARCHITECTURE.md
│   ├── API_DOCUMENTATION.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── toss_design_system.md
│
├── 🐍 Django 프로젝트
│   ├── invoice_system/      # 프로젝트 설정
│   ├── core/                # 웹 UI 앱
│   ├── api/                 # REST API 앱
│   └── manage.py
│
├── 🎨 프론트엔드
│   ├── templates/           # HTML 템플릿
│   └── static/              # CSS, JS, 이미지
│
├── 🔧 설정 및 스크립트
│   ├── requirements.txt
│   ├── .env.example
│   ├── .gitignore
│   ├── setup_initial_data.py
│   └── test_setup.py
│
└── 📸 참고 자료
    ├── site1.png
    ├── site2.png
    └── site3.png
```

---

## 🎯 문서 선택 가이드

### "처음 사용합니다"
→ **[QUICK_START.md](QUICK_START.md)** 먼저 읽으세요

### "전체 기능을 알고 싶습니다"
→ **[README.md](README.md)** 또는 **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)**

### "API를 사용하고 싶습니다"
→ **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)**

### "서버에 배포하고 싶습니다"
→ **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**

### "시스템 구조를 이해하고 싶습니다"
→ **[ARCHITECTURE.md](ARCHITECTURE.md)**

### "설정에 문제가 있습니다"
→ `test_setup.py` 실행 후 **[README.md](README.md)** 문제 해결 섹션 참조

---

## 📖 주요 기능별 문서 참조

### 로그인 및 인증
- [README.md](README.md) - 관리 화면 구성 > 최초 로그인 페이지
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 사용자 인증 및 권한 관리

### 서비스 관리
- [README.md](README.md) - 관리 화면 구성 > 서비스 리스트 페이지
- [ARCHITECTURE.md](ARCHITECTURE.md) - 사용자 권한 흐름도

### 신고서 관리
- [README.md](README.md) - 관리 화면 구성 > 신고서 관리 페이지
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 신고서 관리

### Invoice 처리 API
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - 전체 API 가이드
- [ARCHITECTURE.md](ARCHITECTURE.md) - 데이터 흐름도

### 매핑정보 및 프롬프트
- [README.md](README.md) - 관리 화면 구성 > 신고서 관리 페이지
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 신고서 관리

---

## 🔍 키워드별 검색

### 설치 및 설정
- **QUICK_START.md**: 빠른 설치
- **DEPLOYMENT_GUIDE.md**: 상세 설치 및 배포
- **test_setup.py**: 설정 검증

### API 사용
- **API_DOCUMENTATION.md**: API 명세
- **README.md**: API 사용법
- **PROJECT_SUMMARY.md**: API 엔드포인트

### 데이터베이스
- **README.md**: 데이터베이스 모델
- **ARCHITECTURE.md**: ERD 다이어그램
- **DEPLOYMENT_GUIDE.md**: DB 설정

### 보안
- **DEPLOYMENT_GUIDE.md**: 보안 설정 체크리스트
- **ARCHITECTURE.md**: 보안 레이어
- **PROJECT_SUMMARY.md**: 보안 고려사항

### UI/UX
- **toss_design_system.md**: 디자인 시스템
- **site1.png, site2.png, site3.png**: 화면 설계
- **PROJECT_SUMMARY.md**: 화면 구성

---

## 📞 지원 및 문의

### 기술 지원
- **이메일**: support@erequest.com
- **문서**: [README.md](README.md) - 문제 해결 섹션

### API 관련
- **이메일**: api@erequest.com
- **문서**: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

### 배포 관련
- **이메일**: devops@erequest.com
- **문서**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## ✅ 체크리스트

### 초기 설정 체크리스트
- [ ] Python 3.9+ 설치
- [ ] MSSQL Server 설치
- [ ] ODBC Driver 17 설치
- [ ] requirements.txt 패키지 설치
- [ ] .env 파일 생성 및 설정
- [ ] 데이터베이스 마이그레이션
- [ ] 초기 데이터 생성
- [ ] test_setup.py 검증 통과

### API 사용 체크리스트
- [ ] Google Vision API 키 발급
- [ ] OpenAI API 키 발급
- [ ] API 문서 검토
- [ ] 테스트 Invoice 이미지 준비
- [ ] API 엔드포인트 테스트

### 배포 체크리스트
- [ ] DEBUG=False 설정
- [ ] SECRET_KEY 변경
- [ ] ALLOWED_HOSTS 설정
- [ ] HTTPS 설정
- [ ] 데이터베이스 백업
- [ ] 로그 설정
- [ ] 모니터링 설정

---

## 🔄 업데이트 히스토리

| 버전 | 날짜 | 변경 사항 |
|------|------|-----------|
| 1.0.0 | 2024-01-15 | 초기 릴리스 |

---

## 📌 빠른 명령어 참조

```bash
# 서버 실행
python manage.py runserver

# 마이그레이션
python manage.py migrate

# 초기 데이터
python manage.py shell < setup_initial_data.py

# 설정 테스트
python manage.py shell < test_setup.py

# 관리자 생성
python manage.py createsuperuser
```

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2024-01-15
**프로젝트**: Invoice 자동 인식 시스템

# Invoice System - 빠른 시작 가이드

## ⚡ 5분 안에 시작하기

### 1단계: 환경 설정 (1분)

```bash
# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 2단계: 환경 변수 설정 (1분)

```bash
# .env 파일 생성
copy .env.example .env
```

`.env` 파일 편집 (최소 설정):
```env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=invoice_db
DB_USER=sa
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=1433

GOOGLE_VISION_CREDENTIALS=path/to/credentials.json
OPENAI_API_KEY=sk-your-api-key
```

### 3단계: 데이터베이스 설정 (1분)

```bash
# SQL Server에서 데이터베이스 생성
# CREATE DATABASE invoice_db;

# Django 마이그레이션
python manage.py migrate
```

### 4단계: 초기 데이터 생성 (1분)

```bash
python manage.py shell < setup_initial_data.py
```

### 5단계: 서버 실행 (1분)

```bash
python manage.py runserver
```

## 🎉 완료!

브라우저에서 접속: `http://localhost:8000`

### 로그인 정보
- **관리자**: `admin` / `P@ssw0rd`
- **관세사**: `6N001` / `init123`

---

## 📌 주요 명령어

### 서버 실행
```bash
python manage.py runserver
```

### 마이그레이션
```bash
python manage.py makemigrations
python manage.py migrate
```

### 관리자 계정 생성
```bash
python manage.py createsuperuser
```

### Django Shell
```bash
python manage.py shell
```

### 테스트 실행
```bash
python manage.py shell < test_setup.py
```

---

## 🔧 문제 해결

### ODBC Driver 오류
```bash
# Windows: ODBC Driver 17 설치
https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

### 마이그레이션 오류
```bash
# 모든 마이그레이션 초기화
python manage.py migrate --run-syncdb
```

### 정적 파일 오류
```bash
python manage.py collectstatic --noinput
```

---

## 📚 추가 문서

- **전체 설명**: README.md
- **API 문서**: API_DOCUMENTATION.md
- **배포 가이드**: DEPLOYMENT_GUIDE.md
- **프로젝트 요약**: PROJECT_SUMMARY.md

---

## 🆘 도움말

문제가 발생하면:
1. `test_setup.py` 실행하여 설정 확인
2. `README.md` 참조
3. support@erequest.com으로 문의

**즐거운 개발 되세요! 🚀**

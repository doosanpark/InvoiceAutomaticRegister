# Invoice System - 배포 가이드

## 사전 준비

### 1. 시스템 요구사항
- Python 3.9 이상
- Microsoft SQL Server 2017 이상
- ODBC Driver 17 for SQL Server
- 최소 2GB RAM, 10GB 디스크 공간

### 2. API 키 준비
- **Google Cloud Vision API**
  - Google Cloud Console에서 프로젝트 생성
  - Vision API 활성화
  - 서비스 계정 생성 및 JSON 키 다운로드

- **OpenAI API**
  - OpenAI 플랫폼에서 API 키 발급
  - GPT-4 Vision 액세스 권한 확인

---

## Windows 환경 배포

### 1. Python 및 가상환경 설정

```powershell
# Python 설치 확인
python --version

# 프로젝트 디렉토리로 이동
cd C:\Users\erid3\workspace\INVOICE

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate
```

### 2. ODBC Driver 설치

Microsoft ODBC Driver 17 for SQL Server 다운로드 및 설치:
https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

### 3. 패키지 설치

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`.env.example`을 복사하여 `.env` 파일 생성:

```powershell
copy .env.example .env
```

`.env` 파일 편집:
```env
DJANGO_SECRET_KEY=your-generated-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

DB_NAME=invoice_db
DB_USER=sa
DB_PASSWORD=your-strong-password
DB_HOST=localhost
DB_PORT=1433

GOOGLE_VISION_CREDENTIALS=C:\path\to\google-credentials.json
OPENAI_API_KEY=sk-proj-your-api-key-here

CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-domain.com
```

**Django Secret Key 생성:**
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. 데이터베이스 설정

#### SQL Server 데이터베이스 생성
```sql
-- SQL Server Management Studio 또는 sqlcmd에서 실행
CREATE DATABASE invoice_db;
GO

USE invoice_db;
GO

-- 사용자 생성 (필요한 경우)
CREATE LOGIN invoice_user WITH PASSWORD = 'your-strong-password';
CREATE USER invoice_user FOR LOGIN invoice_user;
GRANT ALL TO invoice_user;
GO
```

#### Django 마이그레이션
```powershell
# 마이그레이션 파일 생성
python manage.py makemigrations

# 마이그레이션 실행
python manage.py migrate

# 정적 파일 수집
python manage.py collectstatic --noinput
```

### 6. 초기 데이터 설정

```powershell
# 초기 데이터 스크립트 실행
python manage.py shell < setup_initial_data.py
```

또는 Django shell에서 직접:
```powershell
python manage.py shell
```
```python
exec(open('setup_initial_data.py').read())
```

### 7. 개발 서버 실행

```powershell
python manage.py runserver 0.0.0.0:8000
```

브라우저에서 `http://localhost:8000` 접속

---

## Linux 환경 배포 (Ubuntu)

### 1. 시스템 패키지 설치

```bash
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3-pip
sudo apt install -y unixodbc unixodbc-dev
```

### 2. Microsoft ODBC Driver 설치

```bash
# Microsoft repository 추가
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list

# ODBC Driver 설치
sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql17
```

### 3. 프로젝트 설정

```bash
# 프로젝트 디렉토리로 이동
cd /var/www/invoice

# 가상환경 생성
python3.9 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Gunicorn 설정

```bash
pip install gunicorn
```

`gunicorn_config.py` 생성:
```python
bind = "0.0.0.0:8000"
workers = 4
threads = 2
timeout = 120
accesslog = "/var/log/invoice/access.log"
errorlog = "/var/log/invoice/error.log"
loglevel = "info"
```

### 5. systemd 서비스 설정

`/etc/systemd/system/invoice.service` 생성:
```ini
[Unit]
Description=Invoice System Django Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/invoice
Environment="PATH=/var/www/invoice/venv/bin"
ExecStart=/var/www/invoice/venv/bin/gunicorn \
    --config gunicorn_config.py \
    invoice_system.wsgi:application

[Install]
WantedBy=multi-user.target
```

서비스 시작:
```bash
sudo systemctl daemon-reload
sudo systemctl enable invoice
sudo systemctl start invoice
sudo systemctl status invoice
```

### 6. Nginx 설정

Nginx 설치:
```bash
sudo apt install -y nginx
```

`/etc/nginx/sites-available/invoice` 생성:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 10M;

    location /static/ {
        alias /var/www/invoice/staticfiles/;
    }

    location /media/ {
        alias /var/www/invoice/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

활성화:
```bash
sudo ln -s /etc/nginx/sites-available/invoice /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 프로덕션 배포 체크리스트

### 보안 설정

- [ ] `DEBUG=False` 설정
- [ ] `SECRET_KEY` 강력한 키로 변경
- [ ] `ALLOWED_HOSTS` 실제 도메인으로 설정
- [ ] HTTPS 설정 (SSL/TLS 인증서)
- [ ] CSRF, CORS 설정 확인
- [ ] 데이터베이스 백업 설정
- [ ] 방화벽 규칙 설정

### 성능 최적화

- [ ] 정적 파일 CDN 설정
- [ ] 데이터베이스 인덱스 최적화
- [ ] Redis 캐시 서버 설정 (선택)
- [ ] 로그 로테이션 설정

### 모니터링

- [ ] 에러 로깅 설정 (Sentry 등)
- [ ] 성능 모니터링 도구 설정
- [ ] 서버 리소스 모니터링
- [ ] API 응답 시간 측정

---

## Docker 배포 (옵션)

### Dockerfile
```dockerfile
FROM python:3.9-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    unixodbc unixodbc-dev \
    curl gnupg \
    && rm -rf /var/lib/apt/lists/*

# ODBC Driver 설치
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "invoice_system.wsgi:application"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DB_HOST=db
    depends_on:
      - db
    volumes:
      - ./media:/app/media
      - ./staticfiles:/app/staticfiles

  db:
    image: mcr.microsoft.com/mssql/server:2019-latest
    environment:
      - ACCEPT_EULA=Y
      - SA_PASSWORD=YourStrong@Password
    ports:
      - "1433:1433"
    volumes:
      - mssql_data:/var/opt/mssql

volumes:
  mssql_data:
```

빌드 및 실행:
```bash
docker-compose build
docker-compose up -d
```

---

## 문제 해결

### ODBC Driver 연결 오류
```
Error: [unixODBC][Driver Manager]Data source name not found
```
**해결방법:**
- ODBC Driver 17 설치 확인
- `/etc/odbcinst.ini` 파일 확인 (Linux)

### Google Vision API 인증 오류
```
Error: Could not automatically determine credentials
```
**해결방법:**
- `GOOGLE_APPLICATION_CREDENTIALS` 환경 변수 확인
- JSON 키 파일 경로 및 권한 확인

### OpenAI API Rate Limit
```
Error: Rate limit exceeded
```
**해결방법:**
- API 사용량 확인
- 요청 간격 조절
- OpenAI 플랜 업그레이드 고려

---

## 백업 및 복구

### 데이터베이스 백업
```bash
# MSSQL 백업
sqlcmd -S localhost -U sa -P password \
  -Q "BACKUP DATABASE invoice_db TO DISK = '/backup/invoice_db.bak'"
```

### 미디어 파일 백업
```bash
tar -czf media_backup.tar.gz media/
```

### 복구
```bash
# 데이터베이스 복구
sqlcmd -S localhost -U sa -P password \
  -Q "RESTORE DATABASE invoice_db FROM DISK = '/backup/invoice_db.bak'"

# 미디어 파일 복구
tar -xzf media_backup.tar.gz
```

---

## 지원

- 배포 문의: devops@erequest.com
- 기술 지원: support@erequest.com

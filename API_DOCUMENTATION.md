# Invoice System API Documentation

## 개요

Invoice 자동 인식 시스템의 REST API 문서입니다.

## 인증

모든 API 요청은 Django Session 인증이 필요합니다.

### 로그인
```bash
curl -X POST http://localhost:8000/login/ \
  -d "username=admin&password=P@ssw0rd" \
  -c cookies.txt
```

이후 요청에 `-b cookies.txt` 플래그를 추가하여 세션 유지

---

## API 엔드포인트

### 1. 인보이스 처리 API

Invoice 이미지를 받아 OCR 및 ChatGPT로 처리하여 JSON 데이터를 반환합니다.

**URL:** `POST /api/process/`

**Request Parameters:**
- `image` (file, required): Invoice 이미지 파일 (jpg, png 등)
- `service_user_id` (integer, required): 서비스 사용자 ID
- `declaration_id` (integer, required): 신고서 ID

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/process/ \
  -b cookies.txt \
  -F "image=@invoice.jpg" \
  -F "service_user_id=1" \
  -F "declaration_id=1"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "신고번호": "2024-01-12345",
    "시리얼번호": "SN-12345",
    "품명": "전자제품",
    "HS부호": "8517.62.00.00"
  },
  "ocr_text": "INVOICE\n신고번호: 2024-01-12345\n...",
  "processing_time": 5.23,
  "log_id": 123
}
```

**Response Fields:**
- `success` (boolean): 처리 성공 여부
- `data` (object): 추출된 JSON 데이터 (매핑정보에 따라 구조화됨)
- `ocr_text` (string): OCR로 추출된 원본 텍스트
- `processing_time` (float): 처리 시간 (초)
- `log_id` (integer): 처리 로그 ID
- `error` (string, optional): 에러 메시지 (실패 시)

**HTTP Status Codes:**
- `200 OK`: 처리 성공
- `400 Bad Request`: 잘못된 요청 (필수 파라미터 누락 등)
- `403 Forbidden`: 권한 없음
- `500 Internal Server Error`: 처리 실패

---

### 2. 처리 로그 목록 조회

**URL:** `GET /api/logs/`

**Query Parameters:**
- `service_user_id` (integer, optional): 서비스 사용자 ID로 필터링
- `declaration_id` (integer, optional): 신고서 ID로 필터링
- `status` (string, optional): 상태로 필터링 (pending, processing, completed, failed)
- `limit` (integer, optional): 결과 개수 제한 (default: 50)

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/logs/?status=completed&limit=10" \
  -b cookies.txt
```

**Response:**
```json
{
  "success": true,
  "count": 10,
  "data": [
    {
      "id": 123,
      "service": "RK통관",
      "declaration": "수입신고서",
      "status": "completed",
      "processing_time": 5.23,
      "created_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:30:05Z",
      "has_error": false
    },
    ...
  ]
}
```

---

### 3. 처리 로그 상세 조회

**URL:** `GET /api/logs/{log_id}/`

**Path Parameters:**
- `log_id` (integer, required): 처리 로그 ID

**Example Request:**
```bash
curl -X GET http://localhost:8000/api/logs/123/ \
  -b cookies.txt
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 123,
    "service": "RK통관",
    "declaration": "수입신고서",
    "status": "completed",
    "ocr_text": "INVOICE\n신고번호: 2024-01-12345\n...",
    "result_json": {
      "신고번호": "2024-01-12345",
      "시리얼번호": "SN-12345",
      ...
    },
    "error_message": null,
    "processing_time": 5.23,
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:30:05Z"
  }
}
```

---

### 4. 신고서 설정 조회

신고서의 매핑정보 및 프롬프트 설정을 조회합니다.

**URL:** `GET /api/declaration/{declaration_id}/config/`

**Path Parameters:**
- `declaration_id` (integer, required): 신고서 ID

**Query Parameters:**
- `service_user_id` (integer, required): 서비스 사용자 ID

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/declaration/1/config/?service_user_id=1" \
  -b cookies.txt
```

**Response:**
```json
{
  "success": true,
  "declaration": {
    "id": 1,
    "name": "수입신고서",
    "type": "import"
  },
  "service": {
    "id": 1,
    "name": "RK통관"
  },
  "mappings": [
    {
      "id": 1,
      "unipass_field_name": "신고번호",
      "db_table_name": "ImportDeclaration",
      "db_field_name": "Rpt_num",
      "priority": 0,
      "basic_prompt": "신고번호 항목을 정확하게 추출하세요...",
      "additional_prompt": "날짜 형식은 YYYY-MM-DD로 변환하세요"
    },
    ...
  ]
}
```

---

## 에러 응답 형식

모든 에러 응답은 다음 형식을 따릅니다:

```json
{
  "success": false,
  "error": "에러 메시지"
}
```

**일반적인 에러 코드:**
- `400 Bad Request`: 잘못된 요청
- `401 Unauthorized`: 인증 필요
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스를 찾을 수 없음
- `500 Internal Server Error`: 서버 내부 오류

---

## 처리 흐름 (Step 1-5)

### Step 1: API 요청
클라이언트가 Invoice 이미지와 설정 정보를 API 서버로 전송

### Step 2: OCR 텍스트 추출
Google Cloud Vision API를 사용하여 이미지에서 텍스트 추출

### Step 3: ChatGPT 분석
추출된 텍스트와 원본 이미지를 ChatGPT (GPT-4 Vision)로 전송하여 분석

### Step 4: JSON 데이터 정리
ChatGPT가 매핑정보와 프롬프트 설정에 따라 데이터를 JSON 형태로 구조화

### Step 5: 결과 반환
정리된 JSON 데이터를 API 응답으로 반환

---

## 통합 예제

### Python 예제

```python
import requests

# 1. 로그인
session = requests.Session()
login_data = {
    'username': 'admin',
    'password': 'P@ssw0rd'
}
session.post('http://localhost:8000/login/', data=login_data)

# 2. Invoice 처리
with open('invoice.jpg', 'rb') as f:
    files = {'image': f}
    data = {
        'service_user_id': 1,
        'declaration_id': 1
    }
    response = session.post('http://localhost:8000/api/process/',
                          files=files, data=data)
    result = response.json()

if result['success']:
    print(f"처리 완료 (처리 시간: {result['processing_time']}초)")
    print(f"추출된 데이터: {result['data']}")
else:
    print(f"처리 실패: {result['error']}")

# 3. 로그 조회
log_response = session.get(f"http://localhost:8000/api/logs/{result['log_id']}/")
log_data = log_response.json()
print(f"로그 상세: {log_data}")
```

### JavaScript 예제

```javascript
// 1. Invoice 처리
const formData = new FormData();
formData.append('image', fileInput.files[0]);
formData.append('service_user_id', 1);
formData.append('declaration_id', 1);

fetch('http://localhost:8000/api/process/', {
  method: 'POST',
  body: formData,
  credentials: 'include'
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    console.log('처리 완료:', data.data);
    console.log('처리 시간:', data.processing_time, '초');
  } else {
    console.error('처리 실패:', data.error);
  }
});

// 2. 로그 목록 조회
fetch('http://localhost:8000/api/logs/?limit=10', {
  credentials: 'include'
})
.then(response => response.json())
.then(data => {
  console.log(`${data.count}개의 로그:`, data.data);
});
```

---

## 제한사항

1. **파일 크기**: 이미지 파일은 10MB 이하 권장
2. **처리 시간**: 평균 5-10초 소요 (이미지 크기 및 복잡도에 따라 다름)
3. **Rate Limit**: 사용자당 분당 60회 요청 제한
4. **지원 이미지 형식**: JPG, PNG, GIF, BMP, TIFF

---

## 문의

- 기술 지원: support@erequest.com
- API 관련 문의: api@erequest.com

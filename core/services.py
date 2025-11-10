"""
OCR 및 AI API 통합 서비스 (ChatGPT / Gemini)
"""
import os
import json
import time
from typing import Dict, Any, Optional
from django.conf import settings
from google.cloud import vision
from openai import OpenAI
import google.generativeai as genai
import base64
from PIL import Image


class OCRService:
    """Google Vision API를 사용한 OCR 서비스"""

    def __init__(self):
        self.use_google_vision = False
        if settings.GOOGLE_VISION_CREDENTIALS and os.path.exists(settings.GOOGLE_VISION_CREDENTIALS):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_VISION_CREDENTIALS
            self.client = vision.ImageAnnotatorClient()
            self.use_google_vision = True

    def extract_text_from_image(self, image_path: str) -> str:
        """
        이미지에서 텍스트 추출

        Args:
            image_path: 이미지 파일 경로

        Returns:
            추출된 텍스트
        """
        # Google Vision을 사용하지 않는 경우 빈 문자열 반환
        # (GPT-4o Vision이 이미지를 직접 분석함)
        if not self.use_google_vision:
            return ""

        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()

            image = vision.Image(content=content)
            response = self.client.text_detection(image=image)

            if response.error.message:
                raise Exception(f'OCR API Error: {response.error.message}')

            texts = response.text_annotations
            if texts:
                return texts[0].description
            return ""

        except Exception as e:
            raise Exception(f"OCR 처리 중 오류 발생: {str(e)}")

    def extract_text_from_bytes(self, image_bytes: bytes) -> str:
        """
        이미지 바이트에서 텍스트 추출

        Args:
            image_bytes: 이미지 바이트 데이터

        Returns:
            추출된 텍스트
        """
        try:
            image = vision.Image(content=image_bytes)
            response = self.client.text_detection(image=image)

            if response.error.message:
                raise Exception(f'OCR API Error: {response.error.message}')

            texts = response.text_annotations
            if texts:
                return texts[0].description
            return ""

        except Exception as e:
            raise Exception(f"OCR 처리 중 오류 발생: {str(e)}")


class GeminiService:
    """Google Gemini API 서비스"""

    def __init__(self):
        genai.configure(api_key=getattr(settings, 'GEMINI_API_KEY', None))
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    def process_invoice(
        self,
        image_path: str,
        ocr_text: str,
        mapping_info: list,
        ai_metadata: str = None
    ) -> Dict[str, Any]:
        """
        인보이스 이미지와 OCR 텍스트를 분석하여 JSON 형태로 데이터 정리

        Args:
            image_path: 이미지 파일 경로
            ocr_text: OCR로 추출된 텍스트
            mapping_info: 매핑 정보 리스트 (프롬프트 포함)
            ai_metadata: AI 메타데이터 (최상위 컨텍스트)

        Returns:
            정리된 JSON 데이터
        """
        try:
            # 이미지 로드
            img = Image.open(image_path)

            # 매핑 정보를 JSON 형태로 구성 (한글명 -> 영문 필드명)
            mapping_structure = {}
            for mapping in mapping_info:
                field_key = f"{mapping['db_table_name']}.{mapping['db_field_name']}"
                mapping_structure[mapping['unipass_field_name']] = field_key

            # 프롬프트 구성
            prompt = self._build_prompt(
                mapping_info,
                ai_metadata,
                ocr_text
            )

            # Gemini API 호출
            response = self.model.generate_content([prompt, img])

            # 응답 파싱
            result_text = response.text

            # JSON 추출 (한글 키)
            result_json_korean = self._extract_json(result_text)

            # 한글 키를 영문 필드명으로 변환
            result_json = self._convert_to_english_keys(result_json_korean, mapping_structure)

            return {
                'success': True,
                'data': result_json,
                'raw_response': result_text
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

    def _convert_to_english_keys(self, korean_json: Dict, mapping_structure: Dict) -> Dict:
        """한글 키를 영문 필드명으로 변환"""
        english_json = {}
        for korean_key, value in korean_json.items():
            # 매핑에서 영문 필드명 찾기
            english_key = mapping_structure.get(korean_key)
            if english_key:
                english_json[english_key] = value
            else:
                # 매핑에 없는 경우 원본 키 사용
                english_json[korean_key] = value
        return english_json

    def _build_prompt(
        self,
        mapping_info: list,
        ai_metadata: str,
        ocr_text: str
    ) -> str:
        """프롬프트 구성"""

        prompt = "당신은 인보이스(Invoice) 데이터를 분석하고 구조화하는 전문가입니다.\n\n"

        prompt += "=== 중요: 첨부된 이미지를 우선적으로 분석하세요 ===\n"
        prompt += "이 요청에는 인보이스 이미지가 첨부되어 있습니다. 반드시 이미지를 직접 확인하여 정확한 정보를 추출하세요.\n\n"

        # AI 메타데이터를 최상위로 배치
        if ai_metadata:
            prompt += f"[문서 정보]\n{ai_metadata}\n\n"

        # 매핑 정보 표시
        prompt += "[데이터베이스 매핑 정보]\n"
        prompt += "추출된 데이터는 다음 DB 구조에 저장됩니다:\n\n"

        current_table = None
        for mapping in mapping_info:
            table_name = mapping['db_table_name']
            field_name = mapping['db_field_name']
            unipass_name = mapping['unipass_field_name']

            # 테이블이 변경되면 테이블명 표시
            if current_table != table_name:
                if current_table is not None:
                    prompt += "\n"
                prompt += f"📦 {table_name} 테이블:\n"
                current_table = table_name

            prompt += f"  - {field_name} ← {unipass_name}\n"

        prompt += "\n"

        # 추출할 항목 및 규칙
        prompt += "[추출할 항목 및 규칙]\n"
        prompt += "다음 항목들의 데이터를 이미지에서 찾아 아래 규칙에 따라 추출해주세요:\n\n"

        # 각 매핑 정보별로 항목과 프롬프트 배치
        for mapping in mapping_info:
            field_name = mapping['unipass_field_name']
            db_info = f"{mapping['db_table_name']}.{mapping['db_field_name']}"

            prompt += f"• {field_name} (→ {db_info})\n"

            if mapping.get('basic_prompt'):
                prompt += f"  - {mapping['basic_prompt']}\n"

            if mapping.get('additional_prompt'):
                prompt += f"  - {mapping['additional_prompt']}\n"

            prompt += "\n"

        # OCR 텍스트 (참고용)
        if ocr_text:
            prompt += "[OCR 추출 텍스트 - 참고용]\n"
            prompt += "다음은 OCR로 추출한 텍스트입니다. 참고용으로만 사용하고, 반드시 이미지를 직접 확인하여 정확한 값을 추출하세요:\n\n"
            prompt += f"{ocr_text}\n\n"

        prompt += """[응답 형식]
반드시 다음 형식의 JSON으로 응답해주세요.
**중요**: JSON의 키는 위에 제시된 한글 항목명(유니패스 필드명)을 그대로 사용해야 합니다.

```json
{
  "항목명1": "추출된_값1",
  "항목명2": "추출된_값2",
  ...
}
```

예시:
```json
{
  "판매자명": "N.S TRADING",
  "송장일자": "2025-05-22",
  "차대번호": "KMHDU41BP7U253602"
}
```

주의사항:
1. **반드시 첨부된 이미지를 직접 분석**하여 정확한 정보를 추출하세요.
2. OCR 텍스트는 참고용이며, 이미지가 우선입니다.
3. 값을 찾을 수 없는 경우 null을 사용하세요.
4. 날짜는 YYYY-MM-DD 형식으로 변환하세요.
5. 숫자는 천단위 구분자 없이 숫자만 추출하세요.
6. JSON 키는 위에 제시된 한글 항목명을 정확히 사용하세요.
7. 반드시 JSON 형식으로만 응답하세요.
8. 각 항목별로 제시된 규칙을 준수하세요.
"""
        return prompt

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """응답에서 JSON 추출"""
        try:
            # ```json ... ``` 형태로 온 경우 추출
            if '```json' in text:
                start = text.find('```json') + 7
                end = text.find('```', start)
                json_text = text[start:end].strip()
            elif '```' in text:
                start = text.find('```') + 3
                end = text.find('```', start)
                json_text = text[start:end].strip()
            else:
                json_text = text.strip()

            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise Exception(f"JSON 파싱 오류: {str(e)}\n응답 텍스트: {text}")


class ChatGPTService:
    """OpenAI ChatGPT API 서비스"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def process_invoice(
        self,
        image_path: str,
        ocr_text: str,
        mapping_info: list,
        ai_metadata: str = None
    ) -> Dict[str, Any]:
        """
        인보이스 이미지와 OCR 텍스트를 분석하여 JSON 형태로 데이터 정리

        Args:
            image_path: 이미지 파일 경로
            ocr_text: OCR로 추출된 텍스트
            mapping_info: 매핑 정보 리스트 (프롬프트 포함)
            ai_metadata: AI 메타데이터 (최상위 컨텍스트)

        Returns:
            정리된 JSON 데이터
        """
        try:
            # 이미지를 base64로 인코딩
            with open(image_path, 'rb') as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

            # 매핑 정보를 JSON 형태로 구성
            mapping_structure = {}
            for mapping in mapping_info:
                field_key = f"{mapping['db_table_name']}.{mapping['db_field_name']}"
                mapping_structure[mapping['unipass_field_name']] = field_key

            # 프롬프트 구성
            system_prompt = self._build_system_prompt(
                mapping_info,
                ai_metadata
            )

            if ocr_text:
                user_prompt = f"""
첨부된 인보이스 이미지를 분석하여 데이터를 추출해주세요.

[OCR 추출 텍스트 - 참고용]
다음은 OCR로 추출한 텍스트입니다. 참고용으로만 사용하고, 반드시 이미지를 직접 확인하여 정확한 값을 추출하세요:

{ocr_text}

**중요**: 위 OCR 텍스트는 참고용이며, 실제 데이터는 첨부된 이미지를 직접 분석하여 추출해주세요.
시스템 프롬프트에 명시된 매핑 정보와 규칙에 따라 JSON 형태로 데이터를 정리해주세요.
"""
            else:
                user_prompt = "첨부된 인보이스 이미지를 직접 분석하여 시스템 프롬프트에 명시된 매핑 정보와 규칙에 따라 JSON 형태로 데이터를 정리해주세요."

            # ChatGPT API 호출 (GPT-4 Vision)
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.1
            )

            # 응답 파싱
            result_text = response.choices[0].message.content

            # JSON 추출 (한글 키)
            result_json_korean = self._extract_json(result_text)

            # 한글 키를 영문 필드명으로 변환
            result_json = self._convert_to_english_keys(result_json_korean, mapping_structure)

            return {
                'success': True,
                'data': result_json,
                'raw_response': result_text
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None
            }

    def _convert_to_english_keys(self, korean_json: Dict, mapping_structure: Dict) -> Dict:
        """한글 키를 영문 필드명으로 변환"""
        english_json = {}
        for korean_key, value in korean_json.items():
            # 매핑에서 영문 필드명 찾기
            english_key = mapping_structure.get(korean_key)
            if english_key:
                english_json[english_key] = value
            else:
                # 매핑에 없는 경우 원본 키 사용
                english_json[korean_key] = value
        return english_json

    def _build_system_prompt(
        self,
        mapping_info: list,
        ai_metadata: str
    ) -> str:
        """시스템 프롬프트 구성"""

        prompt = "당신은 인보이스(Invoice) 데이터를 분석하고 구조화하는 전문가입니다.\n\n"

        prompt += "=== 중요: 첨부된 이미지를 우선적으로 분석하세요 ===\n"
        prompt += "이 요청에는 인보이스 이미지가 첨부되어 있습니다. 반드시 이미지를 직접 확인하여 정확한 정보를 추출하세요.\n\n"

        # AI 메타데이터를 최상위로 배치
        if ai_metadata:
            prompt += f"[문서 정보]\n{ai_metadata}\n\n"

        # 매핑 정보 표시
        prompt += "[데이터베이스 매핑 정보]\n"
        prompt += "추출된 데이터는 다음 DB 구조에 저장됩니다:\n\n"

        current_table = None
        for mapping in mapping_info:
            table_name = mapping['db_table_name']
            field_name = mapping['db_field_name']
            unipass_name = mapping['unipass_field_name']

            # 테이블이 변경되면 테이블명 표시
            if current_table != table_name:
                if current_table is not None:
                    prompt += "\n"
                prompt += f"📦 {table_name} 테이블:\n"
                current_table = table_name

            prompt += f"  - {field_name} ← {unipass_name}\n"

        prompt += "\n"

        # 추출할 항목 및 규칙
        prompt += "[추출할 항목 및 규칙]\n"
        prompt += "다음 항목들의 데이터를 이미지에서 찾아 아래 규칙에 따라 추출해주세요:\n\n"

        # 각 매핑 정보별로 항목과 프롬프트 배치
        for mapping in mapping_info:
            field_name = mapping['unipass_field_name']
            db_info = f"{mapping['db_table_name']}.{mapping['db_field_name']}"

            prompt += f"• {field_name} (→ {db_info})\n"

            if mapping.get('basic_prompt'):
                prompt += f"  - {mapping['basic_prompt']}\n"

            if mapping.get('additional_prompt'):
                prompt += f"  - {mapping['additional_prompt']}\n"

            prompt += "\n"

        prompt += """[응답 형식]
반드시 다음 형식의 JSON으로 응답해주세요.
**중요**: JSON의 키는 위에 제시된 한글 항목명(유니패스 필드명)을 그대로 사용해야 합니다.

```json
{
  "항목명1": "추출된_값1",
  "항목명2": "추출된_값2",
  ...
}
```

예시:
```json
{
  "판매자명": "N.S TRADING",
  "송장일자": "2025-05-22",
  "차대번호": "KMHDU41BP7U253602"
}
```

주의사항:
1. **반드시 첨부된 이미지를 직접 분석**하여 정확한 정보를 추출하세요.
2. OCR 텍스트는 참고용이며, 이미지가 우선입니다.
3. 값을 찾을 수 없는 경우 null을 사용하세요.
4. 날짜는 YYYY-MM-DD 형식으로 변환하세요.
5. 숫자는 천단위 구분자 없이 숫자만 추출하세요.
6. JSON 키는 위에 제시된 한글 항목명을 정확히 사용하세요.
7. 반드시 JSON 형식으로만 응답하세요.
8. 각 항목별로 제시된 규칙을 준수하세요.
"""
        return prompt

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """응답에서 JSON 추출"""
        try:
            # ```json ... ``` 형태로 온 경우 추출
            if '```json' in text:
                start = text.find('```json') + 7
                end = text.find('```', start)
                json_text = text[start:end].strip()
            elif '```' in text:
                start = text.find('```') + 3
                end = text.find('```', start)
                json_text = text[start:end].strip()
            else:
                json_text = text.strip()

            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise Exception(f"JSON 파싱 오류: {str(e)}\n응답 텍스트: {text}")


class InvoiceProcessor:
    """인보이스 처리 통합 서비스"""

    def __init__(self, use_gemini=True):
        self.ocr_service = OCRService()
        self.use_gemini = use_gemini
        if use_gemini:
            self.ai_service = GeminiService()
        else:
            self.ai_service = ChatGPTService()

    def process(
        self,
        image_path: str,
        mapping_info: list,
        ai_metadata: str = None
    ) -> Dict[str, Any]:
        """
        전체 인보이스 처리 파이프라인
        Step 1-5 구현

        Args:
            image_path: 이미지 파일 경로
            mapping_info: 매핑 정보 (프롬프트 포함)
            ai_metadata: AI 메타데이터 (최상위 컨텍스트)

        Returns:
            처리 결과
        """
        start_time = time.time()
        result = {
            'success': False,
            'ocr_text': None,
            'gpt_response': None,
            'result_json': None,
            'error': None,
            'processing_time': 0
        }

        try:
            # Step 2: OCR로 텍스트 추출 (선택적)
            ocr_text = self.ocr_service.extract_text_from_image(image_path)
            result['ocr_text'] = ocr_text if ocr_text else "OCR 미사용 (GPT-4o Vision 직접 분석)"

            # Step 3-4: AI로 데이터 분석 및 JSON 변환 (Gemini 또는 ChatGPT)
            ai_result = self.ai_service.process_invoice(
                image_path=image_path,
                ocr_text=ocr_text,
                mapping_info=mapping_info,
                ai_metadata=ai_metadata
            )

            result['gpt_response'] = ai_result.get('raw_response')

            if not ai_result['success']:
                raise Exception(ai_result.get('error', 'AI 처리 중 오류 발생'))

            # Step 5: 정리된 JSON 데이터
            result['result_json'] = ai_result['data']
            result['success'] = True

        except Exception as e:
            result['error'] = str(e)
            result['success'] = False

        finally:
            result['processing_time'] = time.time() - start_time

        return result

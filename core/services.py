"""
OCR 및 AI API 통합 서비스 (ChatGPT / Gemini)
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from google.cloud import vision
from openai import OpenAI
import google.generativeai as genai
import base64
from PIL import Image
import httpx

logger = logging.getLogger('core')


class OCRService:
    """Google Vision API를 사용한 OCR 서비스"""

    def __init__(self):
        # OCR 필수: Google Vision API 설정 필수
        if not settings.GOOGLE_VISION_CREDENTIALS:
            raise Exception("Google Vision API 자격증명이 설정되지 않았습니다. .env 파일에 GOOGLE_VISION_CREDENTIALS를 설정해주세요.")

        if not os.path.exists(settings.GOOGLE_VISION_CREDENTIALS):
            raise Exception(f"Google Vision API 자격증명 파일을 찾을 수 없습니다: {settings.GOOGLE_VISION_CREDENTIALS}")

        try:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_VISION_CREDENTIALS
            self.client = vision.ImageAnnotatorClient()
            logger.info("[INFO] Google Vision OCR 초기화 성공")
        except Exception as e:
            raise Exception(f"Google Vision API 초기화 실패: {str(e)}\n\n해결 방법:\n1. Google Cloud Console에서 Vision API 활성화\n2. 서비스 계정에 'Cloud Vision API User' 역할 부여")

    def extract_text_from_image(self, image_path: str) -> str:
        """
        이미지에서 텍스트 추출 (필수)

        Args:
            image_path: 이미지 파일 경로

        Returns:
            추출된 텍스트

        Raises:
            Exception: OCR 처리 실패 시 예외 발생
        """
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()

            image = vision.Image(content=content)
            response = self.client.text_detection(image=image)

            if response.error.message:
                raise Exception(f'Google Vision API 오류: {response.error.message}')

            texts = response.text_annotations
            if texts:
                logger.info(f"[INFO] OCR 성공 - {len(texts[0].description)} 글자 추출됨")
                return texts[0].description

            # 텍스트가 없는 경우에도 빈 문자열 반환 (정상)
            logger.info("[INFO] OCR 완료 - 추출된 텍스트 없음")
            return ""

        except Exception as e:
            # OCR 필수이므로 예외를 그대로 전파
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
        # Gemini 2.5 Flash - 빠르고 안정적인 멀티모달 모델
        self.model = genai.GenerativeModel('gemini-2.5-flash')

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

            # 프롬프트를 반환값에 저장하기 위해 인스턴스 변수에 저장
            self.last_prompt = prompt

            # Gemini API 호출
            response = self.model.generate_content([prompt, img])

            # 응답 파싱
            result_text = response.text

            # JSON 추출 (한글 키)
            logger.info(f"[DEBUG GeminiService] Before _extract_json, result_text: {result_text[:200]}")
            result_json_korean = self._extract_json(result_text)
            logger.info(f"[DEBUG GeminiService] After _extract_json, result_json_korean type: {type(result_json_korean)}")
            logger.info(f"[DEBUG GeminiService] After _extract_json, result_json_korean value: {result_json_korean}")

            # 한글 키를 영문 필드명으로 변환
            result_json = self._convert_to_english_keys(result_json_korean, mapping_structure)

            return {
                'success': True,
                'data': result_json,
                'raw_response': result_text,
                'prompt': self.last_prompt
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None,
                'prompt': getattr(self, 'last_prompt', None)
            }

    def _convert_to_english_keys(self, korean_json, mapping_structure: Dict):
        """한글 키를 영문 필드명으로 변환"""
        logger.info(f"[DEBUG GeminiService._convert_to_english_keys LINE 176] START")
        logger.info(f"[DEBUG GeminiService._convert_to_english_keys LINE 177] korean_json type: {type(korean_json)}")
        logger.info(f"[DEBUG GeminiService._convert_to_english_keys LINE 178] korean_json value: {korean_json}")

        try:
            # 리스트인 경우: 각 항목(딕셔너리)을 변환
            if isinstance(korean_json, list):
                logger.info(f"[DEBUG GeminiService._convert_to_english_keys LINE 183] Processing list with {len(korean_json)} items")
                english_list = []
                for idx, item in enumerate(korean_json):
                    logger.info(f"[DEBUG GeminiService._convert_to_english_keys LINE 186] Processing list item {idx+1}")
                    if isinstance(item, dict):
                        english_item = {}
                        for korean_key, value in item.items():
                            english_key = mapping_structure.get(korean_key)
                            if english_key:
                                english_item[english_key] = value
                            else:
                                english_item[korean_key] = value
                        english_list.append(english_item)
                    else:
                        english_list.append(item)
                logger.info(f"[DEBUG GeminiService._convert_to_english_keys LINE 198] SUCCESS - Returning list: {english_list}")
                return english_list

            # 딕셔너리인 경우: 기존 로직
            elif isinstance(korean_json, dict):
                english_json = {}
                logger.info(f"[DEBUG GeminiService._convert_to_english_keys LINE 203] Processing dict with {len(korean_json)} keys")
                for korean_key, value in korean_json.items():
                    logger.info(f"[DEBUG GeminiService._convert_to_english_keys LINE 205] Processing key: {korean_key}")
                    english_key = mapping_structure.get(korean_key)
                    if english_key:
                        english_json[english_key] = value
                    else:
                        english_json[korean_key] = value
                logger.info(f"[DEBUG GeminiService._convert_to_english_keys LINE 211] SUCCESS - Returning dict: {english_json}")
                return english_json

            # 기타 타입: 그대로 반환
            else:
                logger.info(f"[DEBUG GeminiService._convert_to_english_keys LINE 216] Unknown type, returning as-is")
                return korean_json

        except Exception as e:
            logger.error(f"[ERROR GeminiService._convert_to_english_keys LINE 220] Exception: {str(e)}")
            logger.error(f"[ERROR GeminiService._convert_to_english_keys LINE 221] korean_json type: {type(korean_json)}")
            logger.error(f"[ERROR GeminiService._convert_to_english_keys LINE 222] korean_json value: {korean_json}")
            raise

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

        # 추출할 항목 및 규칙
        prompt += "[추출할 항목 및 규칙]\n"
        prompt += "다음 항목들의 데이터를 이미지에서 찾아 아래 규칙에 따라 추출해주세요:\n\n"

        # 각 매핑 정보별로 항목과 프롬프트 배치
        for mapping in mapping_info:
            field_name = mapping['unipass_field_name']

            prompt += f"• {field_name}\n"

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

            logger.info(f"[DEBUG _extract_json] json_text to parse: {json_text[:200]}")
            parsed_result = json.loads(json_text)
            logger.info(f"[DEBUG _extract_json] parsed_result type: {type(parsed_result)}")
            logger.info(f"[DEBUG _extract_json] parsed_result value: {parsed_result}")
            return parsed_result
        except json.JSONDecodeError as e:
            raise Exception(f"JSON 파싱 오류: {str(e)}\n응답 텍스트: {text}")

    def recommend_hs_code(
        self,
        extracted_data,
        image_path: str
    ) -> Dict[str, Any]:
        """
        추출된 Invoice 데이터를 분석하여 HS코드 추천하고 데이터에 병합

        Args:
            extracted_data: 1차로 추출된 Invoice 데이터 (dict 또는 list)
            image_path: Invoice 이미지 경로

        Returns:
            HS코드가 병합된 데이터
        """
        try:
            # 이미지 로드
            img = Image.open(image_path)

            # HS코드 추천 프롬프트 구성
            prompt = self._build_hs_code_prompt(extracted_data)

            # Gemini API 호출
            response = self.model.generate_content([prompt, img])
            result_text = response.text

            logger.info("\n" + "="*80)
            logger.info("[HS CODE RECOMMENDATION PROMPT]")
            logger.info("="*80)
            logger.info(prompt)
            logger.info("\n[HS CODE RECOMMENDATION RESPONSE]")
            logger.info("-"*80)
            logger.info(result_text)
            logger.info("="*80 + "\n")

            # JSON 파싱
            hs_codes = self._extract_json(result_text)
            logger.info(f"[DEBUG GeminiService.recommend_hs_code] hs_codes type: {type(hs_codes)}")
            logger.info(f"[DEBUG GeminiService.recommend_hs_code] hs_codes value: {hs_codes}")

            # HS코드를 기존 데이터에 병합
            if isinstance(extracted_data, list) and isinstance(hs_codes, list):
                # 리스트인 경우: 각 항목에 HS코드 추가
                merged_data = []
                for idx, (item, hs_item) in enumerate(zip(extracted_data, hs_codes)):
                    if isinstance(item, dict) and isinstance(hs_item, dict):
                        merged_item = {**item, **hs_item}  # 딕셔너리 병합
                        merged_data.append(merged_item)
                    else:
                        merged_data.append(item)
                logger.info(f"[DEBUG GeminiService.recommend_hs_code] merged_data: {merged_data}")
                return {
                    'success': True,
                    'merged_data': merged_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': prompt
                }
            elif isinstance(extracted_data, dict) and isinstance(hs_codes, dict):
                # 딕셔너리인 경우: HS코드 병합
                merged_data = {**extracted_data, **hs_codes}
                logger.info(f"[DEBUG GeminiService.recommend_hs_code] merged_data: {merged_data}")
                return {
                    'success': True,
                    'merged_data': merged_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': prompt
                }
            else:
                # 타입이 맞지 않는 경우: 원본 데이터 반환
                logger.warning(f"[WARNING] HS코드 병합 실패 - extracted_data type: {type(extracted_data)}, hs_codes type: {type(hs_codes)}")
                return {
                    'success': True,
                    'merged_data': extracted_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': prompt
                }

        except Exception as e:
            logger.error(f"[ERROR GeminiService.recommend_hs_code] Exception: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'merged_data': extracted_data,  # 오류 시 원본 데이터 반환
                'hs_code_recommendation': None,
                'hs_prompt': None
            }

    def _build_hs_code_prompt(self, extracted_data: Dict[str, Any]) -> str:
        """HS코드 추천 프롬프트 구성"""

        # 추출된 데이터 타입 로깅
        logger.info(f"[DEBUG] extracted_data type: {type(extracted_data)}")
        logger.info(f"[DEBUG] extracted_data value: {extracted_data}")

        # 리스트인 경우와 딕셔너리인 경우 다르게 처리
        if isinstance(extracted_data, list):
            # 리스트인 경우: 각 항목을 번호와 함께 표시
            data_summary = ""
            for idx, item in enumerate(extracted_data, 1):
                data_summary += f"\n[항목 {idx}]\n"
                if isinstance(item, dict):
                    for key, value in item.items():
                        data_summary += f"  - {key}: {value}\n"
                else:
                    data_summary += f"  {item}\n"

            prompt = f"""당신은 관세 및 무역 전문가입니다.
Invoice에서 추출한 여러 항목의 데이터를 분석하여 각 항목별로 적합한 HS코드(관세율표 품목분류 코드)를 추천해주세요.

[추출된 Invoice 데이터]
{data_summary}

[요청사항]
1. 위 데이터와 첨부된 Invoice 이미지를 종합적으로 분석하세요
2. 각 항목별로 상품의 재질, 용도, 형태 등을 고려하여 가장 적합한 HS코드를 추천하세요
3. HS코드는 10자리 형식으로 제시하세요

[응답 형식]
반드시 다음 JSON 배열 형식으로만 응답해주세요. 설명이나 추가 텍스트 없이 JSON만 반환하세요.
항목 순서대로 HS코드를 배열로 반환하세요.

```json
[
  {{"HS코드": "8703.23.10.00"}},
  {{"HS코드": "8703.24.10.00"}},
  {{"HS코드": "8703.23.10.00"}}
]
```

주의사항:
1. 반드시 JSON 배열 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 8703.23.10.00)
3. 설명, 근거, 기타 텍스트는 포함하지 마세요
4. JSON 키는 "HS코드"를 사용하세요
5. 항목 개수만큼 배열에 포함해주세요 (총 {len(extracted_data)}개)
"""
        elif isinstance(extracted_data, dict):
            # 딕셔너리인 경우: 기존 방식
            data_summary = "\n".join([f"  - {key}: {value}" for key, value in extracted_data.items()])

            prompt = f"""당신은 관세 및 무역 전문가입니다.
Invoice에서 추출한 데이터를 분석하여 적합한 HS코드(관세율표 품목분류 코드)를 추천해주세요.

[추출된 Invoice 데이터]
{data_summary}

[요청사항]
1. 위 데이터와 첨부된 Invoice 이미지를 종합적으로 분석하세요
2. 상품의 재질, 용도, 형태 등을 고려하여 가장 적합한 HS코드를 추천하세요
3. HS코드는 10자리 형식으로 제시하세요

[응답 형식]
반드시 다음 JSON 형식으로만 응답해주세요. 설명이나 추가 텍스트 없이 JSON만 반환하세요.

```json
{{
  "HS코드": "8703.23.10.00"
}}
```

주의사항:
1. 반드시 JSON 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 8703.23.10.00)
3. 설명, 근거, 기타 텍스트는 포함하지 마세요
4. JSON 키는 "HS코드"를 사용하세요
"""
        else:
            # 그 외의 경우
            data_summary = str(extracted_data)
            prompt = f"""당신은 관세 및 무역 전문가입니다.
Invoice에서 추출한 데이터를 분석하여 적합한 HS코드(관세율표 품목분류 코드)를 추천해주세요.

[추출된 Invoice 데이터]
{data_summary}

[요청사항]
1. 위 데이터와 첨부된 Invoice 이미지를 종합적으로 분석하세요
2. 상품의 재질, 용도, 형태 등을 고려하여 가장 적합한 HS코드를 추천하세요
3. HS코드는 10자리 형식으로 제시하세요

[응답 형식]
반드시 다음 JSON 형식으로만 응답해주세요. 설명이나 추가 텍스트 없이 JSON만 반환하세요.

```json
{{
  "HS코드": "8703.23.10.00"
}}
```

주의사항:
1. 반드시 JSON 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 8703.23.10.00)
3. 설명, 근거, 기타 텍스트는 포함하지 마세요
4. JSON 키는 "HS코드"를 사용하세요
"""

        return prompt


class ChatGPTService:
    """OpenAI ChatGPT API 서비스"""

    def __init__(self):
        # OpenAI 클라이언트 초기화 (proxy 없이)
        try:
            # httpx 클라이언트를 직접 생성 (환경 변수의 proxy 설정 무시)
            http_client = httpx.Client(
                timeout=60.0,
                trust_env=False  # 환경 변수의 proxy 설정 무시
            )

            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                http_client=http_client,
                max_retries=2
            )
            logger.info("[INFO] OpenAI ChatGPT 클라이언트 초기화 성공")
        except Exception as e:
            logger.error(f"[ERROR] OpenAI 클라이언트 초기화 실패: {str(e)}")
            raise

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

            # 프롬프트를 반환값에 저장하기 위해 인스턴스 변수에 저장
            self.last_system_prompt = system_prompt

            if ocr_text:
                user_prompt = f"""

[OCR 추출 텍스트 - 참고용]
다음은 OCR로 추출한 텍스트입니다. 참고용으로만 사용하고, 반드시 이미지를 직접 확인하여 정확한 값을 추출하세요:

{ocr_text}

**중요**: 위 OCR 텍스트는 참고용이며, 실제 데이터는 첨부된 이미지를 직접 분석하여 추출해주세요.
시스템 프롬프트에 명시된 매핑 정보와 규칙에 따라 JSON 형태로 데이터를 정리해주세요.
"""
            else:
                user_prompt = "첨부된 인보이스 이미지를 직접 분석하여 시스템 프롬프트에 명시된 매핑 정보와 규칙에 따라 JSON 형태로 데이터를 정리해주세요."

            # ChatGPT API 호출 내용 출력
            logger.info("\n" + "="*80)
            logger.info("[OpenAI API CALL]")
            logger.info("="*80)
            logger.info(f"Model: gpt-4o")
            logger.info(f"Temperature: 0.1")
            logger.info(f"Max Tokens: 4096")
            logger.info("\n[System Prompt]")
            logger.info("-"*80)
            logger.info(system_prompt)
            logger.info("\n[User Prompt]")
            logger.info("-"*80)
            logger.info(user_prompt)
            logger.info("\n[Image Info]")
            logger.info(f"- Image base64 length: {len(image_base64)} characters")
            logger.info(f"- Image path: {image_path}")
            logger.info("="*80 + "\n")

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

            # OpenAI API 응답 출력
            logger.info("\n" + "="*80)
            logger.info("[OpenAI API RESPONSE]")
            logger.info("="*80)
            logger.info(result_text)
            logger.info("="*80 + "\n")

            # JSON 추출 (한글 키)
            logger.info(f"[DEBUG ChatGPTService] Before _extract_json, result_text: {result_text[:200]}")
            result_json_korean = self._extract_json(result_text)
            logger.info(f"[DEBUG ChatGPTService] After _extract_json, result_json_korean type: {type(result_json_korean)}")
            logger.info(f"[DEBUG ChatGPTService] After _extract_json, result_json_korean value: {result_json_korean}")

            # 한글 키를 영문 필드명으로 변환
            result_json = self._convert_to_english_keys(result_json_korean, mapping_structure)

            return {
                'success': True,
                'data': result_json,
                'raw_response': result_text,
                'system_prompt': self.last_system_prompt,
                'user_prompt': user_prompt
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None,
                'system_prompt': getattr(self, 'last_system_prompt', None),
                'user_prompt': None
            }

    def _convert_to_english_keys(self, korean_json, mapping_structure: Dict):
        """한글 키를 영문 필드명으로 변환"""
        logger.info(f"[DEBUG ChatGPTService._convert_to_english_keys LINE 533] START")
        logger.info(f"[DEBUG ChatGPTService._convert_to_english_keys LINE 534] korean_json type: {type(korean_json)}")
        logger.info(f"[DEBUG ChatGPTService._convert_to_english_keys LINE 535] korean_json value: {korean_json}")

        try:
            # 리스트인 경우: 각 항목(딕셔너리)을 변환
            if isinstance(korean_json, list):
                logger.info(f"[DEBUG ChatGPTService._convert_to_english_keys LINE 540] Processing list with {len(korean_json)} items")
                english_list = []
                for idx, item in enumerate(korean_json):
                    logger.info(f"[DEBUG ChatGPTService._convert_to_english_keys LINE 543] Processing list item {idx+1}")
                    if isinstance(item, dict):
                        english_item = {}
                        for korean_key, value in item.items():
                            english_key = mapping_structure.get(korean_key)
                            if english_key:
                                english_item[english_key] = value
                            else:
                                english_item[korean_key] = value
                        english_list.append(english_item)
                    else:
                        english_list.append(item)
                logger.info(f"[DEBUG ChatGPTService._convert_to_english_keys LINE 555] SUCCESS - Returning list: {english_list}")
                return english_list

            # 딕셔너리인 경우: 기존 로직
            elif isinstance(korean_json, dict):
                english_json = {}
                logger.info(f"[DEBUG ChatGPTService._convert_to_english_keys LINE 560] Processing dict with {len(korean_json)} keys")
                for korean_key, value in korean_json.items():
                    logger.info(f"[DEBUG ChatGPTService._convert_to_english_keys LINE 562] Processing key: {korean_key}")
                    english_key = mapping_structure.get(korean_key)
                    if english_key:
                        english_json[english_key] = value
                    else:
                        english_json[korean_key] = value
                logger.info(f"[DEBUG ChatGPTService._convert_to_english_keys LINE 568] SUCCESS - Returning dict: {english_json}")
                return english_json

            # 기타 타입: 그대로 반환
            else:
                logger.info(f"[DEBUG ChatGPTService._convert_to_english_keys LINE 573] Unknown type, returning as-is")
                return korean_json

        except Exception as e:
            logger.error(f"[ERROR ChatGPTService._convert_to_english_keys LINE 577] Exception: {str(e)}")
            logger.error(f"[ERROR ChatGPTService._convert_to_english_keys LINE 578] korean_json type: {type(korean_json)}")
            logger.error(f"[ERROR ChatGPTService._convert_to_english_keys LINE 579] korean_json value: {korean_json}")
            raise

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

        # 추출할 항목 및 규칙
        prompt += "[추출할 항목 및 규칙]\n"
        prompt += "다음 항목들의 데이터를 이미지에서 찾아 아래 규칙에 따라 추출해주세요:\n\n"

        # 각 매핑 정보별로 항목과 프롬프트 배치
        for mapping in mapping_info:
            field_name = mapping['unipass_field_name']

            prompt += f"• {field_name}\n"

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
3. 값을 찾을 수 없는 경우 생략하세요.
4. 날짜는 YYYY-MM-DD 형식으로 변환하세요.
5. 숫자는 천단위 구분자 없이 숫자만 추출하세요.
6. JSON 키는 위에 제시된 한글 항목명을 정확히 사용하세요.
7. 반드시 JSON 형식으로만 응답하세요.
8. 각 항목별로 제시된 규칙을 준수하세요.
9. 현재 JSON 반환 키가 계속 기존 DB 테이블 및 필드명입니다. 유니패스 한글 필드명으로 반환되도록 수정 바랍니다.
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

            logger.info(f"[DEBUG _extract_json] json_text to parse: {json_text[:200]}")
            parsed_result = json.loads(json_text)
            logger.info(f"[DEBUG _extract_json] parsed_result type: {type(parsed_result)}")
            logger.info(f"[DEBUG _extract_json] parsed_result value: {parsed_result}")
            return parsed_result
        except json.JSONDecodeError as e:
            raise Exception(f"JSON 파싱 오류: {str(e)}\n응답 텍스트: {text}")

    def recommend_hs_code(
        self,
        extracted_data,
        image_path: str
    ) -> Dict[str, Any]:
        """
        추출된 Invoice 데이터를 분석하여 HS코드 추천하고 데이터에 병합

        Args:
            extracted_data: 1차로 추출된 Invoice 데이터 (dict 또는 list)
            image_path: Invoice 이미지 경로

        Returns:
            HS코드가 병합된 데이터
        """
        try:
            # 이미지를 base64로 인코딩
            with open(image_path, 'rb') as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

            # HS코드 추천 프롬프트 구성
            hs_prompt = self._build_hs_code_prompt(extracted_data)

            # ChatGPT API 호출
            logger.info("\n" + "="*80)
            logger.info("[HS CODE RECOMMENDATION - OpenAI API CALL]")
            logger.info("="*80)
            logger.info(hs_prompt)
            logger.info("="*80 + "\n")

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": hs_prompt
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
                max_tokens=2048,
                temperature=0.3
            )

            result_text = response.choices[0].message.content

            logger.info("\n" + "="*80)
            logger.info("[HS CODE RECOMMENDATION RESPONSE]")
            logger.info("="*80)
            logger.info(result_text)
            logger.info("="*80 + "\n")

            # JSON 파싱
            hs_codes = self._extract_json(result_text)
            logger.info(f"[DEBUG ChatGPTService.recommend_hs_code] hs_codes type: {type(hs_codes)}")
            logger.info(f"[DEBUG ChatGPTService.recommend_hs_code] hs_codes value: {hs_codes}")

            # HS코드를 기존 데이터에 병합
            if isinstance(extracted_data, list) and isinstance(hs_codes, list):
                # 리스트인 경우: 각 항목에 HS코드 추가
                merged_data = []
                for idx, (item, hs_item) in enumerate(zip(extracted_data, hs_codes)):
                    if isinstance(item, dict) and isinstance(hs_item, dict):
                        merged_item = {**item, **hs_item}  # 딕셔너리 병합
                        merged_data.append(merged_item)
                    else:
                        merged_data.append(item)
                logger.info(f"[DEBUG ChatGPTService.recommend_hs_code] merged_data: {merged_data}")
                return {
                    'success': True,
                    'merged_data': merged_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': hs_prompt
                }
            elif isinstance(extracted_data, dict) and isinstance(hs_codes, dict):
                # 딕셔너리인 경우: HS코드 병합
                merged_data = {**extracted_data, **hs_codes}
                logger.info(f"[DEBUG ChatGPTService.recommend_hs_code] merged_data: {merged_data}")
                return {
                    'success': True,
                    'merged_data': merged_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': hs_prompt
                }
            else:
                # 타입이 맞지 않는 경우: 원본 데이터 반환
                logger.warning(f"[WARNING] HS코드 병합 실패 - extracted_data type: {type(extracted_data)}, hs_codes type: {type(hs_codes)}")
                return {
                    'success': True,
                    'merged_data': extracted_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': hs_prompt
                }

        except Exception as e:
            logger.error(f"[ERROR ChatGPTService.recommend_hs_code] Exception: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'merged_data': extracted_data,  # 오류 시 원본 데이터 반환
                'hs_code_recommendation': None,
                'hs_prompt': None
            }

    def _build_hs_code_prompt(self, extracted_data: Dict[str, Any]) -> str:
        """HS코드 추천 프롬프트 구성"""

        # 추출된 데이터 타입 로깅
        logger.info(f"[DEBUG] extracted_data type: {type(extracted_data)}")
        logger.info(f"[DEBUG] extracted_data value: {extracted_data}")

        # 리스트인 경우와 딕셔너리인 경우 다르게 처리
        if isinstance(extracted_data, list):
            # 리스트인 경우: 각 항목을 번호와 함께 표시
            data_summary = ""
            for idx, item in enumerate(extracted_data, 1):
                data_summary += f"\n[항목 {idx}]\n"
                if isinstance(item, dict):
                    for key, value in item.items():
                        data_summary += f"  - {key}: {value}\n"
                else:
                    data_summary += f"  {item}\n"

            prompt = f"""당신은 관세 및 무역 전문가입니다.
Invoice에서 추출한 여러 항목의 데이터를 분석하여 각 항목별로 적합한 HS코드(관세율표 품목분류 코드)를 추천해주세요.

[추출된 Invoice 데이터]
{data_summary}

[요청사항]
1. 위 데이터와 첨부된 Invoice 이미지를 종합적으로 분석하세요
2. 각 항목별로 상품의 재질, 용도, 형태 등을 고려하여 가장 적합한 HS코드를 추천하세요
3. HS코드는 10자리 형식으로 제시하세요

[응답 형식]
반드시 다음 JSON 배열 형식으로만 응답해주세요. 설명이나 추가 텍스트 없이 JSON만 반환하세요.
항목 순서대로 HS코드를 배열로 반환하세요.

```json
[
  {{"HS코드": "8703.23.10.00"}},
  {{"HS코드": "8703.24.10.00"}},
  {{"HS코드": "8703.23.10.00"}}
]
```

주의사항:
1. 반드시 JSON 배열 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 8703.23.10.00)
3. 설명, 근거, 기타 텍스트는 포함하지 마세요
4. JSON 키는 "HS코드"를 사용하세요
5. 항목 개수만큼 배열에 포함해주세요 (총 {len(extracted_data)}개)
"""
        elif isinstance(extracted_data, dict):
            # 딕셔너리인 경우: 기존 방식
            data_summary = "\n".join([f"  - {key}: {value}" for key, value in extracted_data.items()])

            prompt = f"""당신은 관세 및 무역 전문가입니다.
Invoice에서 추출한 데이터를 분석하여 적합한 HS코드(관세율표 품목분류 코드)를 추천해주세요.

[추출된 Invoice 데이터]
{data_summary}

[요청사항]
1. 위 데이터와 첨부된 Invoice 이미지를 종합적으로 분석하세요
2. 상품의 재질, 용도, 형태 등을 고려하여 가장 적합한 HS코드를 추천하세요
3. HS코드는 10자리 형식으로 제시하세요

[응답 형식]
반드시 다음 JSON 형식으로만 응답해주세요. 설명이나 추가 텍스트 없이 JSON만 반환하세요.

```json
{{
  "HS코드": "8703.23.10.00"
}}
```

주의사항:
1. 반드시 JSON 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 8703.23.10.00)
3. 설명, 근거, 기타 텍스트는 포함하지 마세요
4. JSON 키는 "HS코드"를 사용하세요
"""
        else:
            # 그 외의 경우
            data_summary = str(extracted_data)
            prompt = f"""당신은 관세 및 무역 전문가입니다.
Invoice에서 추출한 데이터를 분석하여 적합한 HS코드(관세율표 품목분류 코드)를 추천해주세요.

[추출된 Invoice 데이터]
{data_summary}

[요청사항]
1. 위 데이터와 첨부된 Invoice 이미지를 종합적으로 분석하세요
2. 상품의 재질, 용도, 형태 등을 고려하여 가장 적합한 HS코드를 추천하세요
3. HS코드는 10자리 형식으로 제시하세요

[응답 형식]
반드시 다음 JSON 형식으로만 응답해주세요. 설명이나 추가 텍스트 없이 JSON만 반환하세요.

```json
{{
  "HS코드": "8703.23.10.00"
}}
```

주의사항:
1. 반드시 JSON 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 8703.23.10.00)
3. 설명, 근거, 기타 텍스트는 포함하지 마세요
4. JSON 키는 "HS코드"를 사용하세요
"""

        return prompt


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
            'processing_time': 0,
            'prompt': None,
            'hs_code_recommendation': None,
            'hs_prompt': None
        }

        try:
            # Step 2: OCR로 텍스트 추출 (필수)
            logger.info("\n" + "="*80)
            logger.info("[Google Vision OCR START]")
            logger.info("="*80)
            ocr_text = self.ocr_service.extract_text_from_image(image_path)
            result['ocr_text'] = ocr_text
            logger.info(f"\nOCR COMPLETE - {len(ocr_text)} characters extracted")
            logger.info(f"\n[OCR Extracted Text]")
            logger.info("-"*80)
            logger.info(ocr_text[:500] + ("..." if len(ocr_text) > 500 else ""))
            logger.info("="*80 + "\n")

            # Step 3-4: AI로 데이터 분석 및 JSON 변환 (Gemini 또는 ChatGPT)
            ai_result = self.ai_service.process_invoice(
                image_path=image_path,
                ocr_text=ocr_text,
                mapping_info=mapping_info,
                ai_metadata=ai_metadata
            )

            result['gpt_response'] = ai_result.get('raw_response')

            # 프롬프트 정보 저장 (ChatGPT인 경우 system_prompt + user_prompt, Gemini인 경우 통합 prompt)
            if self.use_gemini:
                result['prompt'] = ai_result.get('prompt')
            else:
                # ChatGPT의 경우 system_prompt와 user_prompt를 합침
                system_prompt = ai_result.get('system_prompt', '')
                user_prompt = ai_result.get('user_prompt', '')
                result['prompt'] = f"[System Prompt]\n{system_prompt}\n\n[User Prompt]\n{user_prompt}"

            if not ai_result['success']:
                raise Exception(ai_result.get('error', 'AI 처리 중 오류 발생'))

            # Step 5: 정리된 JSON 데이터
            result['result_json'] = ai_result['data']
            result['success'] = True

            # Step 6: HS코드 추천 및 데이터 병합 (선택적)
            if result['success'] and result['result_json']:
                logger.info("\n" + "="*80)
                logger.info("[HS CODE RECOMMENDATION START]")
                logger.info("="*80 + "\n")

                hs_result = self.ai_service.recommend_hs_code(
                    extracted_data=result['result_json'],
                    image_path=image_path
                )

                # HS코드가 병합된 데이터로 업데이트
                if hs_result.get('success') and hs_result.get('merged_data'):
                    result['result_json'] = hs_result.get('merged_data')
                    logger.info(f"[INFO] HS코드가 병합된 데이터로 업데이트: {result['result_json']}")

                result['hs_code_recommendation'] = hs_result.get('hs_code_recommendation')
                result['hs_prompt'] = hs_result.get('hs_prompt')

                logger.info("\n" + "="*80)
                logger.info("[HS CODE RECOMMENDATION COMPLETE]")
                logger.info("="*80 + "\n")

        except Exception as e:
            result['error'] = str(e)
            result['success'] = False

        finally:
            result['processing_time'] = time.time() - start_time

        return result

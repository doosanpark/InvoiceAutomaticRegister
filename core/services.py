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
import httpx
import logging

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
                return texts[0].description

            # 텍스트가 없는 경우에도 빈 문자열 반환 (정상)
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

            # 테이블별 처리 순서가 있는지 확인
            has_process_order = any(mapping.get('process_order') is not None for mapping in mapping_info)
            return self._process_invoice_sequential(img, image_path, ocr_text, mapping_info, ai_metadata)        
            #if has_process_order:
            #    # 순차 처리 로직
            #    return self._process_invoice_sequential(img, image_path, ocr_text, mapping_info, ai_metadata)
            #else:
            #    # 기존 일괄 처리 로직
            #    return self._process_invoice_batch(img, image_path, ocr_text, mapping_info, ai_metadata)

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None,
                'prompt': getattr(self, 'last_prompt', None)
            }

    def _process_invoice_batch(
        self,
        img,
        image_path: str,
        ocr_text: str,
        mapping_info: list,
        ai_metadata: str = None
    ) -> Dict[str, Any]:
        """기존 일괄 처리 로직"""
        # 매핑 정보를 JSON 형태로 구성 (한글명 -> 영문 필드명)
        mapping_structure = {}
        for mapping in mapping_info:
            field_key = f"{mapping['db_table_name']}.{mapping['db_field_name']}"
            mapping_structure[mapping['unipass_field_name']] = field_key

        # 프롬프트 구성
        prompt = self._build_prompt(
            mapping_structure,
            ai_metadata,
            ocr_text
        )

        # 프롬프트를 반환값에 저장하기 위해 인스턴스 변수에 저장
        self.last_prompt = prompt

        # Request 로깅
        logger = logging.getLogger('core')
        logger.info(f"\nGEMINI REQUEST:\n{prompt}\n")

        # Gemini API 호출
        response = self.model.generate_content([prompt, img])

        # 응답 파싱
        result_text = response.text

        # Response 로깅
        logger = logging.getLogger('core')
        logger.info(f"\nGEMINI RESPONSE:\n{result_text}\n")

        # JSON 추출 (한글 키)
        result_json_korean = self._extract_json(result_text)

        # 한글 키를 영문 필드명으로 변환
        result_json = self._convert_to_english_keys(result_json_korean, mapping_structure)

        return {
            'success': True,
            'data': result_json,
            'raw_response': result_text,
            'prompt': self.last_prompt
        }

    def _process_invoice_sequential(
        self,
        img,
        image_path: str,
        ocr_text: str,
        mapping_info: list,
        ai_metadata: str = None
    ) -> Dict[str, Any]:
        """순차 처리 로직 - 처리 순서대로 단계별 처리"""
        # 처리 순서별로 매핑 정보 그룹화
        ordered_mappings = {}
        unordered_mappings = []

        for mapping in mapping_info:
            order = mapping.get('process_order')
            # process_order가 None이거나 0인 경우 미설정으로 간주
            if order is None or order == 0:
                unordered_mappings.append(mapping)
            else:
                if order not in ordered_mappings:
                    ordered_mappings[order] = []
                ordered_mappings[order].append(mapping)

        # 처리 순서 정렬
        sorted_orders = sorted(ordered_mappings.keys())

        # 미설정 매핑이 있으면 가장 마지막에 추가
        if unordered_mappings:
            last_order = max(sorted_orders) + 1 if sorted_orders else 1
            for m in unordered_mappings:
                if not m.get('work_group'):
                    m['work_group'] = '미설정 항목'
            ordered_mappings[last_order] = unordered_mappings
            sorted_orders.append(last_order)

        grouped_mappings = ordered_mappings

        # 전체 매핑 구조 (한글 -> 영문 필드명)
        mapping_structure = {}
        for mapping in mapping_info:
            field_key = f"{mapping['db_table_name']}.{mapping['db_field_name']}"
            mapping_structure[mapping['unipass_field_name']] = field_key

        # 전체 프롬프트 저장용
        all_prompts = []
        all_responses = []

        # 이전 단계 결과 누적
        previous_results = {}
        logger = logging.getLogger('core')

        # 각 순서별로 처리
        for step_num, order in enumerate(sorted_orders, 1):
            current_mappings = grouped_mappings[order]
            work_group = current_mappings[0].get('work_group', f'순서 {order}')

            # 현재 단계 프롬프트 구성 (이전 결과 포함)
            prompt = self._build_prompt_with_previous_results(
                current_mappings,
                ai_metadata,
                ocr_text,
                previous_results,
                step_num,
                len(sorted_orders)
            )

            all_prompts.append(f"[STEP {step_num}: {work_group}]\n{prompt}")

            # Request 로깅 (길이 포함)
            prompt_length = len(prompt)
            logger.info(f"\n[STEP {step_num}] REQUEST:")
            logger.info(f"Prompt Length: {prompt_length:,} chars")
            logger.info(f"\n{prompt}\n")

            # 프롬프트가 너무 길면 경고
            if prompt_length > 50000:  # 약 12,500 토큰
                logger.warning(f"[WARNING] Prompt is very long ({prompt_length:,} chars). This may cause API issues.")

            # Gemini API 호출
            response = self.model.generate_content([prompt, img])
            result_text = response.text
            all_responses.append(f"[STEP {step_num}: {work_group}]\n{result_text}")

            # Response 로깅
            logger.info(f"\n[STEP {step_num}] RESPONSE:\n{result_text}\n")

            # JSON 추출
            step_result_korean = self._extract_json(result_text)

            # 현재 단계 결과를 이전 결과에 병합
            if isinstance(step_result_korean, dict):
                previous_results.update(step_result_korean)
            elif isinstance(step_result_korean, list):
                # 리스트인 경우 테이블명을 키로 저장 (이전 결과 보존)
                db_table_name = current_mappings[0].get('db_table_name', f'items_step_{order}')
                previous_results[db_table_name] = step_result_korean


        # AI가 테이블명.필드명 형식을 사용한 경우를 한글 키로 정규화
        reverse_mapping = {}  # {"CUSDEC830C1.qty": "수량(단위)", ...}
        for mapping in mapping_info:
            table_field = f"{mapping['db_table_name']}.{mapping['db_field_name']}"
            reverse_mapping[table_field] = mapping['unipass_field_name']

        previous_results = self._normalize_keys_to_korean(previous_results, reverse_mapping)

        # 한글 키를 영문 필드명으로 변환
        result_json = self._convert_to_english_keys(previous_results, mapping_structure)

        # 모든 프롬프트와 응답 합치기
        combined_prompt = "\n\n".join(all_prompts)
        combined_response = "\n\n".join(all_responses)

        self.last_prompt = combined_prompt

        # 단계별 프롬프트와 응답을 구조화
        steps_detail = []
        for idx, order in enumerate(sorted_orders, 1):
            work_group = grouped_mappings[order][0].get('work_group', f'순서 {order}')

            # 이 단계의 매핑 정보만 추출
            step_mappings = []
            for m in grouped_mappings[order]:
                step_mappings.append({
                    'unipass_field_name': m['unipass_field_name'],
                    'db_table_name': m['db_table_name'],
                    'db_field_name': m['db_field_name'],
                    'basic_prompt': m.get('basic_prompt'),
                    'additional_prompt': m.get('additional_prompt')
                })

            steps_detail.append({
                'step': idx,
                'order': order,
                'work_group': work_group,
                'prompt': all_prompts[idx - 1] if idx - 1 < len(all_prompts) else '',
                'response': all_responses[idx - 1] if idx - 1 < len(all_responses) else '',
                'mapping_count': len(grouped_mappings[order]),
                'mappings': step_mappings  # 이 단계의 매핑만 포함
            })

        return {
            'success': True,
            'data': result_json,
            'raw_response': combined_response,
            'prompt': combined_prompt,
            'steps': steps_detail,  # 단계별 상세 정보
            'total_steps': len(sorted_orders)
        }

    def _normalize_keys_to_korean(self, data, reverse_mapping: Dict):
        """테이블명.필드명 형식의 키를 한글 키로 정규화 (재귀적으로 중첩된 구조 처리)"""
        if isinstance(data, list):
            return [self._normalize_keys_to_korean(item, reverse_mapping) for item in data]
        elif isinstance(data, dict):
            normalized = {}
            for key, value in data.items():
                # 테이블명.필드명 → 한글 키로 변환
                normalized_key = reverse_mapping.get(key, key)
                # 값도 재귀적으로 처리
                normalized[normalized_key] = self._normalize_keys_to_korean(value, reverse_mapping)
            return normalized
        else:
            return data

    def _convert_to_english_keys(self, korean_json, mapping_structure: Dict):
        """한글 키를 영문 필드명으로 변환 (재귀적으로 중첩된 구조 처리)"""
        try:
            # 리스트인 경우: 각 항목을 재귀적으로 변환
            if isinstance(korean_json, list):
                english_list = []
                for idx, item in enumerate(korean_json):
                    # 재귀 호출로 중첩된 dict/list 처리
                    english_list.append(self._convert_to_english_keys(item, mapping_structure))
                return english_list

            # 딕셔너리인 경우: 키 변환 및 값을 재귀적으로 처리
            elif isinstance(korean_json, dict):
                english_json = {}
                for korean_key, value in korean_json.items():
                    english_key = mapping_structure.get(korean_key)

                    # 키 변환
                    final_key = english_key if english_key else korean_key

                    # 값도 재귀적으로 변환 (중첩된 dict/list 처리)
                    english_json[final_key] = self._convert_to_english_keys(value, mapping_structure)

                return english_json

            # 기타 타입(str, int, float, bool, None 등): 그대로 반환
            else:
                return korean_json

        except Exception as e:
            raise

    def _build_prompt_with_previous_results(
        self,
        mapping_info: list,
        ai_metadata: str,
        ocr_text: str,
        previous_results: dict,
        step_num: int,
        total_steps: int
    ) -> str:
        """이전 결과를 포함한 프롬프트 구성 (순차 처리용)"""

        prompt = f"당신은 인보이스(Invoice) 데이터를 분석하고 구조화하는 전문가입니다.\n\n"

        prompt += f"=== 현재 단계: {step_num}/{total_steps} ===\n"
        prompt += "이 작업은 여러 단계로 나뉘어 처리됩니다. 현재 단계에서는 아래 지정된 항목만 추출하면 됩니다.\n\n"

        # 이전 단계 결과가 있으면 포함
        if previous_results:
            prompt += "[이전 단계에서 추출된 데이터]\n"
            prompt += "참고: 아래는 이전 단계에서 이미 추출된 데이터입니다. 이 정보를 참고하여 현재 단계의 데이터를 추출하세요.\n\n"
            if isinstance(previous_results, dict):
                for key, value in previous_results.items():
                    prompt += f"  - {key}: {value}\n"
            else:
                prompt += f"{previous_results}\n"
            prompt += "\n"

        prompt += "=== 중요: 첨부된 이미지를 우선적으로 분석하세요 ===\n"
        prompt += "이 요청에는 인보이스 이미지가 첨부되어 있습니다. 반드시 이미지를 직접 확인하여 정확한 정보를 추출하세요.\n\n"

        # AI 메타데이터를 최상위로 배치
        if ai_metadata:
            prompt += f"[문서 정보]\n{ai_metadata}\n\n"

        # 추출할 항목 및 규칙
        prompt += "[이번 단계에서 추출할 항목 및 규칙]\n"
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
**주의**: 이번 단계에서 요청한 항목만 JSON에 포함하세요. 이전 단계 데이터는 포함하지 마세요.

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
3. 이전 단계 데이터는 참고만 하고, 현재 단계 항목만 추출하세요.
4. 값을 찾을 수 없는 경우 null을 사용하세요.
5. 날짜는 YYYY-MM-DD 형식으로 변환하세요.
6. 숫자는 천단위 구분자 없이 숫자만 추출하세요.
7. JSON 키는 위에 제시된 한글 항목명을 정확히 사용하세요.
8. 반드시 JSON 형식으로만 응답하세요.
9. 각 항목별로 제시된 규칙을 준수하세요.
"""
        return prompt

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

            parsed_result = json.loads(json_text)
            return parsed_result
        except json.JSONDecodeError as e:
            # AI가 JSON이 아닌 일반 텍스트로 응답한 경우
            error_msg = f"AI가 JSON 형식이 아닌 텍스트로 응답했습니다.\n\n"
            error_msg += f"파싱 오류: {str(e)}\n\n"
            error_msg += f"AI 응답 내용:\n{text}\n\n"
            error_msg += "가능한 원인:\n"
            error_msg += "1. 이미지가 불명확하거나 AI가 인식할 수 없는 형식입니다.\n"
            error_msg += "2. 프롬프트가 명확하지 않아 AI가 JSON을 생성하지 못했습니다.\n"
            error_msg += "3. 매핑 정보나 테이블 처리 설정이 누락되었을 수 있습니다."
            raise Exception(error_msg)

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

            # Request 로깅
            logger = logging.getLogger('core')
            logger.info(f"\nGEMINI HS CODE REQUEST:\n{prompt}\n")

            # Gemini API 호출
            response = self.model.generate_content([prompt, img])
            result_text = response.text

            # Response 로깅
            logger.info(f"\nGEMINI HS CODE RESPONSE:\n{result_text}\n")

            # JSON 파싱
            hs_codes = self._extract_json(result_text)

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
                return {
                    'success': True,
                    'merged_data': merged_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': prompt
                }
            elif isinstance(extracted_data, dict) and isinstance(hs_codes, dict):
                # 딕셔너리인 경우: HS코드 병합
                merged_data = {**extracted_data, **hs_codes}
                return {
                    'success': True,
                    'merged_data': merged_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': prompt
                }
            else:
                # 타입이 맞지 않는 경우: 원본 데이터 반환
                return {
                    'success': True,
                    'merged_data': extracted_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': prompt
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'merged_data': extracted_data,  # 오류 시 원본 데이터 반환
                'hs_code_recommendation': None,
                'hs_prompt': None
            }

    def _build_hs_code_prompt(self, extracted_data: Dict[str, Any]) -> str:
        """HS코드 추천 프롬프트 구성"""

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
  {{"HS코드": "0000.00.00.00"}},
  {{"HS코드": "0000.00.00.00"}},
  {{"HS코드": "0000.00.00.00"}}
]
```

주의사항:
1. 반드시 JSON 배열 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 0000.00.00.00)
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
  "HS코드": "0000.00.00.00"
}}
```

주의사항:
1. 반드시 JSON 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 0000.00.00.00)
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
  "HS코드": "0000.00.00.00"
}}
```

주의사항:
1. 반드시 JSON 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 0000.00.00.00)
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
        except Exception as e:
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
            # 테이블별 처리 순서가 있는지 확인
            has_process_order = any(mapping.get('process_order') is not None for mapping in mapping_info)
            return self._process_invoice_sequential(image_path, ocr_text, mapping_info, ai_metadata)
            #if has_process_order:
            #    # 순차 처리 로직
            #    return self._process_invoice_sequential(image_path, ocr_text, mapping_info, ai_metadata)
            #else:
            #    # 기존 일괄 처리 로직
            #    return self._process_invoice_batch(image_path, ocr_text, mapping_info, ai_metadata)

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None,
                'system_prompt': getattr(self, 'last_system_prompt', None),
                'user_prompt': None
            }

    def _process_invoice_sequential(
        self,
        image_path: str,
        ocr_text: str,
        mapping_info: list,
        ai_metadata: str = None
    ) -> Dict[str, Any]:
        """순차 처리 로직 - 처리 순서대로 단계별 처리"""
        try:
            # 이미지를 base64로 인코딩
            with open(image_path, 'rb') as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

            # 처리 순서별로 매핑 정보 그룹화
            ordered_mappings = {}
            unordered_mappings = []

            for mapping in mapping_info:
                order = mapping.get('process_order')
                # process_order가 None이거나 0인 경우 미설정으로 간주
                if order is None or order == 0:
                    unordered_mappings.append(mapping)
                else:
                    if order not in ordered_mappings:
                        ordered_mappings[order] = []
                    ordered_mappings[order].append(mapping)

            # 처리 순서 정렬
            sorted_orders = sorted(ordered_mappings.keys())

            # 미설정 매핑이 있으면 가장 마지막에 추가
            if unordered_mappings:
                last_order = max(sorted_orders) + 1 if sorted_orders else 1
                for m in unordered_mappings:
                    if not m.get('work_group'):
                        m['work_group'] = '미설정 항목'
                ordered_mappings[last_order] = unordered_mappings
                sorted_orders.append(last_order)

            grouped_mappings = ordered_mappings

            # 전체 매핑 구조 (한글 -> 영문 필드명)
            mapping_structure = {}
            for mapping in mapping_info:
                field_key = f"{mapping['db_table_name']}.{mapping['db_field_name']}"
                mapping_structure[mapping['unipass_field_name']] = field_key

            # 전체 프롬프트 저장용
            all_prompts = []
            all_responses = []

            # 이전 단계 결과 누적
            previous_results = {}
            logger = logging.getLogger('core')

            # 각 순서별로 처리
            for step_num, order in enumerate(sorted_orders, 1):
                current_mappings = grouped_mappings[order]
                logger.info(f"\n[STEP {step_num}] current_mappings:\n{current_mappings}\n")
                work_group = current_mappings[0].get('work_group', f'순서 {order}')
                logger.info(f"\n[STEP {step_num}] work_group:\n{work_group}\n")

                # 현재 단계 시스템 프롬프트 구성 (이전 결과 포함)
                system_prompt = self._build_system_prompt_with_previous_results(
                    current_mappings,
                    ai_metadata,
                    previous_results,
                    step_num,
                    len(sorted_orders)
                )

                if ocr_text:
                    user_prompt = f"""
                [OCR 추출 텍스트 - 참고용]
                {ocr_text}

                **중요**: 위 OCR 텍스트는 참고용이며, 반드시 이미지를 직접 분석하여 정확한 값을 추출하세요.
                시스템 프롬프트에 명시된 매핑 정보와 규칙에 따라 JSON 형태로 데이터를 정리해주세요.
                """
                else:
                    user_prompt = "첨부된 인보이스 이미지를 직접 분석하여 시스템 프롬프트에 명시된 매핑 정보와 규칙에 따라 JSON 형태로 데이터를 정리해주세요."

                all_prompts.append(f"[STEP {step_num}: {work_group}]\n[System Prompt]\n{system_prompt}\n[User Prompt]\n{user_prompt}")

                # Request 로깅 (길이 포함)
                system_prompt_length = len(system_prompt)
                user_prompt_length = len(user_prompt)
                total_prompt_length = system_prompt_length + user_prompt_length

                logger.info(f"\n[STEP {step_num}] REQUEST:")
                logger.info(f"Prompt Length - System: {system_prompt_length:,} chars, User: {user_prompt_length:,} chars, Total: {total_prompt_length:,} chars")
                logger.info(f"\n[System Prompt]\n{system_prompt}\n\n[User Prompt]\n{user_prompt}\n")

                # 프롬프트가 너무 길면 경고
                if total_prompt_length > 50000:  # 약 12,500 토큰
                    logger.warning(f"[WARNING] Prompt is very long ({total_prompt_length:,} chars). This may cause API issues.")

                try:
                    # ChatGPT API 호출
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

                    result_text = response.choices[0].message.content
                    all_responses.append(f"[STEP {step_num}: {work_group}]\n{result_text}")

                    # Response 로깅
                    logger.info(f"\n[STEP {step_num}] RESPONSE11111111111:\n{result_text}\n")

                    # JSON 추출
                    step_result_korean = self._extract_json(result_text)

                    # 현재 단계 결과를 이전 결과에 병합
                    if isinstance(step_result_korean, dict):
                        previous_results.update(step_result_korean)
                    elif isinstance(step_result_korean, list):
                        # 리스트인 경우 테이블명을 키로 저장 (이전 결과 보존)
                        db_table_name = current_mappings[0].get('db_table_name', f'items_step_{order}')
                        previous_results[db_table_name] = step_result_korean
                except Exception as e:
                    continue

            # AI가 테이블명.필드명 형식을 사용한 경우를 한글 키로 정규화
            reverse_mapping = {}  # {"CUSDEC830C1.qty": "수량(단위)", ...}
            for mapping in mapping_info:
                table_field = f"{mapping['db_table_name']}.{mapping['db_field_name']}"
                reverse_mapping[table_field] = mapping['unipass_field_name']

            previous_results = self._normalize_keys_to_korean(previous_results, reverse_mapping)

            # 한글 키를 영문 필드명으로 변환
            result_json = self._convert_to_english_keys(previous_results, mapping_structure)

            # 모든 프롬프트와 응답 합치기
            combined_prompt = "\n\n".join(all_prompts)
            combined_response = "\n\n".join(all_responses)

            # 단계별 프롬프트와 응답을 구조화
            steps_detail = []
            for idx, order in enumerate(sorted_orders, 1):
                work_group = grouped_mappings[order][0].get('work_group', f'순서 {order}')

                # 이 단계의 매핑 정보만 추출
                step_mappings = []
                for m in grouped_mappings[order]:
                    step_mappings.append({
                        'unipass_field_name': m['unipass_field_name'],
                        'db_table_name': m['db_table_name'],
                        'db_field_name': m['db_field_name'],
                        'basic_prompt': m.get('basic_prompt'),
                        'additional_prompt': m.get('additional_prompt')
                    })

                steps_detail.append({
                    'step': idx,
                    'order': order,
                    'work_group': work_group,
                    'prompt': all_prompts[idx - 1] if idx - 1 < len(all_prompts) else '',
                    'response': all_responses[idx - 1] if idx - 1 < len(all_responses) else '',
                    'mapping_count': len(grouped_mappings[order]),
                    'mappings': step_mappings  # 이 단계의 매핑만 포함
                })

            return {
                'success': True,
                'data': result_json,
                'raw_response': combined_response,
                'system_prompt': combined_prompt,
                'user_prompt': 'Sequential processing - see combined prompt',
                'steps': steps_detail,  # 단계별 상세 정보
                'total_steps': len(sorted_orders)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None,
                'system_prompt': None,
                'user_prompt': None
            }

    def _normalize_keys_to_korean(self, data, reverse_mapping: Dict):
        """테이블명.필드명 형식의 키를 한글 키로 정규화 (재귀적으로 중첩된 구조 처리)"""
        if isinstance(data, list):
            return [self._normalize_keys_to_korean(item, reverse_mapping) for item in data]
        elif isinstance(data, dict):
            normalized = {}
            for key, value in data.items():
                # 테이블명.필드명 → 한글 키로 변환
                normalized_key = reverse_mapping.get(key, key)
                # 값도 재귀적으로 처리
                normalized[normalized_key] = self._normalize_keys_to_korean(value, reverse_mapping)
            return normalized
        else:
            return data

    def _convert_to_english_keys(self, korean_json, mapping_structure: Dict):
        """한글 키를 영문 필드명으로 변환 (재귀적으로 중첩된 구조 처리)"""
        try:
            # 리스트인 경우: 각 항목을 재귀적으로 변환
            if isinstance(korean_json, list):
                english_list = []
                for idx, item in enumerate(korean_json):
                    # 재귀 호출로 중첩된 dict/list 처리
                    english_list.append(self._convert_to_english_keys(item, mapping_structure))
                return english_list

            # 딕셔너리인 경우: 키 변환 및 값을 재귀적으로 처리
            elif isinstance(korean_json, dict):
                english_json = {}
                for korean_key, value in korean_json.items():
                    english_key = mapping_structure.get(korean_key)

                    # 키 변환
                    final_key = english_key if english_key else korean_key

                    # 값도 재귀적으로 변환 (중첩된 dict/list 처리)
                    english_json[final_key] = self._convert_to_english_keys(value, mapping_structure)

                return english_json

            # 기타 타입(str, int, float, bool, None 등): 그대로 반환
            else:
                return korean_json

        except Exception as e:
            raise

    def _build_system_prompt_with_previous_results(
        self,
        mapping_info: list,
        ai_metadata: str,
        previous_results: dict,
        step_num: int,
        total_steps: int
    ) -> str:
        """이전 결과를 포함한 시스템 프롬프트 구성 (순차 처리용)"""

        prompt = f"당신은 인보이스(Invoice) 데이터를 분석하고 구조화하는 전문가입니다.\n\n"

        prompt += f"=== 현재 단계: {step_num}/{total_steps} ===\n"
        prompt += "이 작업은 여러 단계로 나뉘어 처리됩니다. 현재 단계에서는 아래 지정된 항목만 추출하면 됩니다.\n\n"

        # 이전 단계 결과가 있으면 포함
        if previous_results:
            prompt += "[이전 단계에서 추출된 데이터]\n"
            prompt += "참고: 아래는 이전 단계에서 이미 추출된 데이터입니다. 이 정보를 참고하여 현재 단계의 데이터를 추출하세요.\n\n"
            if isinstance(previous_results, dict):
                for key, value in previous_results.items():
                    prompt += f"  - {key}: {value}\n"
            else:
                prompt += f"{previous_results}\n"
            prompt += "\n"

        prompt += "=== 중요: 첨부된 이미지를 우선적으로 분석하세요 ===\n"
        prompt += "이 요청에는 인보이스 이미지가 첨부되어 있습니다. 반드시 이미지를 직접 확인하여 정확한 정보를 추출하세요.\n\n"

        # AI 메타데이터를 최상위로 배치
        if ai_metadata:
            prompt += f"[문서 정보]\n{ai_metadata}\n\n"

        # 추출할 항목 및 규칙
        prompt += "[이번 단계에서 추출할 항목 및 규칙]\n"
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
**주의**: 이번 단계에서 요청한 항목만 JSON에 포함하세요. 이전 단계 데이터는 포함하지 마세요.

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
3. 이전 단계 데이터는 참고만 하고, 현재 단계 항목만 추출하세요.
4. 값을 찾을 수 없는 경우 생략하세요.
5. 날짜는 YYYY-MM-DD 형식으로 변환하세요.
6. 숫자는 천단위 구분자 없이 숫자만 추출하세요.
7. JSON 키는 위에 제시된 한글 항목명을 정확히 사용하세요.
8. 반드시 JSON 형식으로만 응답하세요.
9. 각 항목별로 제시된 규칙을 준수하세요.
"""
        return prompt

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

            parsed_result = json.loads(json_text)
            return parsed_result
        except json.JSONDecodeError as e:
            # AI가 JSON이 아닌 일반 텍스트로 응답한 경우
            error_msg = f"AI가 JSON 형식이 아닌 텍스트로 응답했습니다.\n\n"
            error_msg += f"파싱 오류: {str(e)}\n\n"
            error_msg += f"AI 응답 내용:\n{text}\n\n"
            error_msg += "가능한 원인:\n"
            error_msg += "1. 이미지가 불명확하거나 AI가 인식할 수 없는 형식입니다.\n"
            error_msg += "2. 프롬프트가 명확하지 않아 AI가 JSON을 생성하지 못했습니다.\n"
            error_msg += "3. 매핑 정보나 테이블 처리 설정이 누락되었을 수 있습니다."
            raise Exception(error_msg)

    def _build_hs_code_prompt(self, extracted_data: Dict[str, Any]) -> str:
        """HS코드 추천 프롬프트 구성"""

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
  {{"HS코드": "0000.00.00.00"}},
  {{"HS코드": "0000.00.00.00"}},
  {{"HS코드": "0000.00.00.00"}}
]
```

주의사항:
1. 반드시 JSON 배열 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 0000.00.00.00)
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
  "HS코드": "0000.00.00.00"
}}
```

주의사항:
1. 반드시 JSON 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 0000.00.00.00)
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
  "HS코드": "0000.00.00.00"
}}
```

주의사항:
1. 반드시 JSON 형식으로만 응답하세요
2. HS코드는 10자리 형식입니다 (예: 0000.00.00.00)
3. 설명, 근거, 기타 텍스트는 포함하지 마세요
4. JSON 키는 "HS코드"를 사용하세요
"""

        return prompt

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

            # Request 로깅
            logger = logging.getLogger('core')
            logger.info(f"\nCHATGPT HS CODE REQUEST:\n{hs_prompt}\n")

            # ChatGPT API 호출
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

            # Response 로깅
            logger.info(f"\nCHATGPT HS CODE RESPONSE:\n{result_text}\n")

            # JSON 파싱
            hs_codes = self._extract_json(result_text)

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
                return {
                    'success': True,
                    'merged_data': merged_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': hs_prompt
                }
            elif isinstance(extracted_data, dict) and isinstance(hs_codes, dict):
                # 딕셔너리인 경우: HS코드 병합
                merged_data = {**extracted_data, **hs_codes}
                return {
                    'success': True,
                    'merged_data': merged_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': hs_prompt
                }
            else:
                # 타입이 맞지 않는 경우: 원본 데이터 반환
                return {
                    'success': True,
                    'merged_data': extracted_data,
                    'hs_code_recommendation': result_text,
                    'hs_prompt': hs_prompt
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'merged_data': extracted_data,  # 오류 시 원본 데이터 반환
                'hs_code_recommendation': None,
                'hs_prompt': None
            }


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
            ocr_text = self.ocr_service.extract_text_from_image(image_path)
            result['ocr_text'] = ocr_text

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
                hs_result = self.ai_service.recommend_hs_code(
                    extracted_data=result['result_json'],
                    image_path=image_path
                )

                # HS코드가 병합된 데이터로 업데이트
                if hs_result.get('success') and hs_result.get('merged_data'):
                    result['result_json'] = hs_result.get('merged_data')

                result['hs_code_recommendation'] = hs_result.get('hs_code_recommendation')
                result['hs_prompt'] = hs_result.get('hs_prompt')

        except Exception as e:
            result['error'] = str(e)
            result['success'] = False

        finally:
            result['processing_time'] = time.time() - start_time

        return result

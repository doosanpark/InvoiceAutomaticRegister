import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Gemini API 키 설정
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

print("="*70)
print("Available Gemini Models")
print("="*70)

try:
    # 사용 가능한 모델 리스트 조회
    models = genai.list_models()

    print("\nModels that support 'generateContent' (for images):")
    print("-"*70)

    for model in models:
        # generateContent를 지원하는 모델만 출력
        if 'generateContent' in model.supported_generation_methods:
            print(f"\n[OK] {model.name}")
            print(f"   Display Name: {model.display_name}")
            print(f"   Description: {model.description}")
            print(f"   Supported Methods: {', '.join(model.supported_generation_methods)}")

    print("\n" + "="*70)
    print("Recommended model for invoice processing:")
    print("  - gemini-1.5-pro (best quality)")
    print("  - gemini-1.5-flash (faster)")
    print("  - gemini-pro-vision (stable)")
    print("="*70)

except Exception as e:
    print(f"\n[ERROR] {e}")
    print("\nPlease check:")
    print("  1. GEMINI_API_KEY is correct in .env file")
    print("  2. API key has proper permissions")
    print("  3. Gemini API is enabled in Google Cloud Console")

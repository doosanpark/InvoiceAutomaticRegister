"""
Google Vision API 연결 테스트
"""
import os
from dotenv import load_dotenv
from google.cloud import vision

load_dotenv()

# 환경 변수 설정
credentials_path = os.getenv('GOOGLE_VISION_CREDENTIALS')
print(f"Credentials path: {credentials_path}")
print(f"File exists: {os.path.exists(credentials_path)}")

# 환경 변수로 설정
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

try:
    # Vision API 클라이언트 생성
    print("\nCreating Vision API client...")
    client = vision.ImageAnnotatorClient()
    print("[OK] Vision API client created successfully!")

    # 간단한 테스트 이미지 생성 (1x1 픽셀 PNG)
    import base64
    # 1x1 투명 PNG 이미지 (base64)
    test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    image_content = base64.b64decode(test_image_base64)

    print("\nTesting text detection...")
    image = vision.Image(content=image_content)
    response = client.text_detection(image=image)

    print("[OK] Text detection API call successful!")

    if response.error.message:
        print(f"[ERROR] API returned error: {response.error.message}")
    else:
        print("[OK] No errors from API")
        print(f"[INFO] Found {len(response.text_annotations)} text annotations")

    print("\n" + "="*70)
    print("SUCCESS! Google Vision API is working correctly!")
    print("="*70)

except Exception as e:
    print("\n" + "="*70)
    print(f"[ERROR] Google Vision API test failed!")
    print("="*70)
    print(f"\nError details: {str(e)}")
    print("\nPossible solutions:")
    print("1. Enable Vision API in Google Cloud Console:")
    print("   https://console.cloud.google.com/apis/library/vision.googleapis.com?project=invoice-ocr-project-474312")
    print("\n2. Check Service Account permissions:")
    print("   - Go to IAM & Admin -> Service Accounts")
    print("   - Ensure the service account has 'Cloud Vision API User' role")
    print("\n3. Verify credentials file is valid and not expired")

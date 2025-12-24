import os
import json
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

# 1. 환경 변수 로드
load_dotenv()
FIREBASE_KEY = os.getenv("FIREBASE_KEY")
FIREBASE_URL = os.getenv("FIREBASE_URL")

def print_recent_logs():
    # 2. Firebase 연결
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(FIREBASE_KEY)
            firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
            print("✅ Firebase 연결 성공")
        except Exception as e:
            print(f"❌ 연결 실패: {e}")
            return

    # 3. 데이터 가져오기 (최근 5개)
    ref = db.reference('robot_logs')
    # 가장 마지막(최신) 데이터 5개를 가져옴
    snapshot = ref.order_by_key().limit_to_last(5).get()

    if not snapshot:
        print("📭 데이터베이스가 비어있거나 'robot_logs' 경로에 데이터가 없습니다.")
        return

    print(f"\n📊 최근 로그 {len(snapshot)}개 출력:\n" + "="*40)
    
    # 예쁘게 출력
    for key, val in snapshot.items():
        ts = val.get('timestamp', 'No Time')
        dtype = val.get('type', 'Unknown')
        
        # 로그 내용 요약
        content = ""
        if dtype == 'nav':
            content = f"Status: {val.get('status')} (L:{val.get('val_l')}, R:{val.get('val_r')})"
        elif dtype == 'log':
            content = f"Msg: {val.get('msg')}"
        elif dtype == 'ocr':
            content = f"OCR: {val.get('text')}"
        else:
            content = str(val)

        print(f"[{ts}] {dtype.upper()} | {content}")

if __name__ == "__main__":
    print_recent_logs()
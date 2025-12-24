# 파일명: JetTankGUI.py
import sys, os
import json
import datetime
import requests
import paho.mqtt.client as mqtt
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv
from collections import deque

# [수정] QGridLayout 추가됨
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QPushButton, QLabel, QSplitter, QGroupBox, 
                             QProgressBar, QSlider, QGridLayout, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, pyqtSlot, QThread
from PyQt6.QtGui import QFont
# ==========================================================
# [사용자 설정] 키/주소 입력 필수
# ==========================================================
# 내 컴퓨터에서 브로커가 돌고 있음
BROKER_IP = "127.0.0.1" 
TOPIC_SUB = "ssafy_agv_robotpal/data"
TOPIC_PUB = "ssafy_agv_robotpal/command" # [추가] 명령 송신용 토픽
load_dotenv()

# Firebase 설정 (키 파일 경로 및 DB URL)
FIREBASE_KEY = "path/to/firebase_key.json"
FIREBASE_URL = "https://your-project.firebaseio.com/"

# ==========================================================
# 워커 클래스 (MQTT & AI)
# ==========================================================
class MqttWorker(QObject):
    msg_signal = pyqtSignal(dict) 
    def __init__(self):
        super().__init__()
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
    
    def start(self):
        try:
            self.client.connect(BROKER_IP, 1883, 60)
            self.client.loop_start()
        except: print("MQTT Connection Failed")

    def on_connect(self, client, userdata, flags, rc):
        print("MQTT Connected")
        client.subscribe(TOPIC_SUB)

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            self.msg_signal.emit(data)
        except: pass
    
    # [추가] 명령 전송 메서드
    def send_command(self, cmd_data):
        try:
            payload = json.dumps(cmd_data)
            self.client.publish(TOPIC_PUB, payload)
            # print(f"Sent: {payload}")
        except Exception as e:
            print(f"Send Error: {e}")

class AIAnalysisWorker(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, logs):
        super().__init__()
        self.logs = logs

    def run(self):
        try:
            # 1) 로그 문자열 변환
            log_str = json.dumps(self.logs, indent=2, ensure_ascii=False)

            # 2) 프롬프트 작성
            prompt = f"로봇 로그 분석:\n{log_str}\n\n1. 작업 내용\n2. 안정성 평가\n3. 조언\n요약해서 알려줘."

            # 3) Gemini API endpoint
            api_key = os.getenv("GMS_KEY")
            url = f"https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"

            # 4) JSON payload 생성
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }

            headers = {"Content-Type": "application/json"}

            # 5) POST 요청 (Gemini 호출)
            response = requests.post(url, headers=headers, data=json.dumps(payload))

            if response.status_code != 200:
                self.result_signal.emit(f"API Error: {response.status_code} - {response.text}")
                return

            data = response.json()

            # 6) Gemini 응답 파싱
            gemini_text = data["candidates"][0]["content"]["parts"][0]["text"]

            # 7) GUI로 전달
            self.result_signal.emit(gemini_text)

        except Exception as e:
            self.result_signal.emit(f"Error: {str(e)}")

# ==========================================================
# 메인 GUI
# ==========================================================
class JetTankGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.init_firebase()
        self.mqtt = MqttWorker()
        self.mqtt.msg_signal.connect(self.handle_data)
        self.mqtt.start()
        self.recent_logs = deque(maxlen=100)

        self.initUI()
        
        # 키보드 입력을 받기 위해 포커스 정책 설정
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def init_firebase(self):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(FIREBASE_KEY)
                firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
            self.db_ref = db.reference('robot_logs')
        except: 
            self.db_ref = None

    def initUI(self):
        self.setWindowTitle("JetTank AI Control Center (WASD to Drive)")
        self.resize(1100, 700)
        self.setStyleSheet("background-color:#2b2b2b; color:#e0e0e0; font-family:Arial;")

        layout = QHBoxLayout()
        
        # [Left] Status & Control
        left = QWidget(); lv = QVBoxLayout(); left.setLayout(lv)
        
        # 1. Navigation Status
        gn = QGroupBox("🚀 Navigation"); gnl = QVBoxLayout()
        self.lbl_nav = QLabel("STOPPED")
        self.lbl_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_nav.setStyleSheet("font-size:20px; font-weight:bold; color:#777;")
        self.bar_nav = QProgressBar()
        gnl.addWidget(self.lbl_nav); gnl.addWidget(self.bar_nav)
        gn.setLayout(gnl)

        # 2. [추가] Remote Control Panel
        gc = QGroupBox("🎮 Remote Control (WASD)"); gcl = QGridLayout()
        self.btn_w = QPushButton("▲"); self.btn_w.clicked.connect(lambda: self.pub_cmd(0.3, 0.3))
        self.btn_a = QPushButton("◀"); self.btn_a.clicked.connect(lambda: self.pub_cmd(-0.2, 0.2))
        self.btn_s = QPushButton("▼"); self.btn_s.clicked.connect(lambda: self.pub_cmd(-0.3, -0.3))
        self.btn_d = QPushButton("▶"); self.btn_d.clicked.connect(lambda: self.pub_cmd(0.2, -0.2))
        self.btn_stop = QPushButton("STOP (Space)"); self.btn_stop.clicked.connect(lambda: self.pub_cmd(0.0, 0.0))
        
        # 스타일링
        for btn in [self.btn_w, self.btn_a, self.btn_s, self.btn_d, self.btn_stop]:
            btn.setStyleSheet("font-size:16px; font-weight:bold; padding:10px; background-color:#444;")
        self.btn_stop.setStyleSheet("background-color:#d32f2f; color:white; font-weight:bold;")

        gcl.addWidget(self.btn_w, 0, 1)
        gcl.addWidget(self.btn_a, 1, 0)
        gcl.addWidget(self.btn_stop, 1, 1)
        gcl.addWidget(self.btn_d, 1, 2)
        gcl.addWidget(self.btn_s, 2, 1)
        gc.setLayout(gcl)

        # 3. Arm Joints (기존 유지)
        ga = QGroupBox("🦾 Arm Joints"); gal = QVBoxLayout()
        self.lbl_j2 = QLabel("Joint 2: 0°")
        self.sl_j2 = QSlider(Qt.Orientation.Horizontal); self.sl_j2.setRange(0,180); self.sl_j2.setEnabled(False)
        self.lbl_j3 = QLabel("Joint 3: 0°")
        self.sl_j3 = QSlider(Qt.Orientation.Horizontal); self.sl_j3.setRange(0,180); self.sl_j3.setEnabled(False)
        gal.addWidget(self.lbl_j2); gal.addWidget(self.sl_j2)
        gal.addWidget(self.lbl_j3); gal.addWidget(self.sl_j3)
        ga.setLayout(gal)

        lv.addWidget(gn); lv.addWidget(gc); lv.addWidget(ga); lv.addStretch()

        # [Right] AI & Log (기존 유지)
        right = QWidget(); rv = QVBoxLayout(); right.setLayout(rv)
        
        gai = QGroupBox("🧠 AI Feedback")
        self.ai_view = QTextEdit(); self.ai_view.setReadOnly(True)
        self.btn_ai = QPushButton("✨ Analyze Logs")
        # self.btn_ai.clicked.connect(self.run_ai) # AI Worker 필요시 주석 해제
        self.btn_ai.setStyleSheet("background-color:#0078d7; padding:10px; font-weight:bold;")
        rv.addWidget(gai); rv.addWidget(self.ai_view); rv.addWidget(self.btn_ai)
        
        glog = QGroupBox("📜 Realtime Logs")
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True)
        rv.addWidget(glog); rv.addWidget(self.log_view)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left); splitter.addWidget(right); splitter.setSizes([400,600])
        layout.addWidget(splitter)
        self.setLayout(layout)

    # [추가] 키보드 이벤트 핸들러
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_W: self.pub_cmd(0.3, 0.3)
        elif key == Qt.Key.Key_S: self.pub_cmd(-0.3, -0.3)
        elif key == Qt.Key.Key_A: self.pub_cmd(-0.2, 0.2)
        elif key == Qt.Key.Key_D: self.pub_cmd(0.2, -0.2)
        elif key == Qt.Key.Key_Space: self.pub_cmd(0.0, 0.0)
    
    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat():
            self.pub_cmd(0.0, 0.0)

    def pub_cmd(self, left, right):
        # 로봇이 이해할 수 있는 JSON 포맷으로 전송
        cmd = {"type": "drive", "left": left, "right": right}
        self.mqtt.send_command(cmd)

    @pyqtSlot(dict)
    def handle_data(self, data):
        # (기존 데이터 처리 로직 유지)
        if self.db_ref:
            try:
                data['ts'] = datetime.datetime.now().isoformat()
                self.db_ref.push(data)
            except: pass
        
        self.recent_logs.append(data)
        if len(self.recent_logs) > 20: self.recent_logs.pop(0)

        dtype = data.get("type")
        if dtype == "nav":
            st = data.get("status","stopped")
            tgt = data.get("target", "Manual") # 타겟 표시
            self.lbl_nav.setText(f"{st.upper()} ({tgt})")
            self.bar_nav.setValue(data.get("progress",0))
            color = "#4caf50" if st == "moving" else "#777"
            self.lbl_nav.setStyleSheet(f"font-size:20px; font-weight:bold; color:{color};")
            self.log(f"Nav: {st}")
        elif dtype == "joint":
            pass # (기존 코드 생략)
        elif dtype == "ocr":
             self.log(f"OCR: {data.get('text')}")

    def log(self, msg):
        self.log_view.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = JetTankGUI()
    gui.show()
    sys.exit(app.exec())
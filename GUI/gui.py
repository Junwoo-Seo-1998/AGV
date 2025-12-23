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
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QPushButton, QLabel, QSplitter, QGroupBox, 
                             QProgressBar, QSlider, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, pyqtSlot, QThread
from PyQt6.QtGui import QFont

# ==========================================================
# [사용자 설정] 키/주소 입력 필수
# ==========================================================
# 내 컴퓨터에서 브로커가 돌고 있음
BROKER_IP = "127.0.0.1" # 로봇과 같은 네트워크의 브로커 IP
TOPIC_SUB = "ssafy_agv_robotpal/data"
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

    def init_firebase(self):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(FIREBASE_KEY)
                firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
            self.db_ref = db.reference('robot_logs')
        except: 
            print("Firebase Init Failed (Check Key Path)")
            self.db_ref = None

    def initUI(self):
        self.setWindowTitle("JetTank AI Control Center")
        self.resize(1100, 700)
        self.setStyleSheet("background-color:#2b2b2b; color:#e0e0e0; font-family:Arial;")

        layout = QHBoxLayout()
        
        # [Left] Status Panel
        left = QWidget(); lv = QVBoxLayout(); left.setLayout(lv)
        
        # Nav
        gn = QGroupBox("🚀 Navigation"); gnl = QVBoxLayout()
        self.lbl_nav = QLabel("STOPPED")
        self.lbl_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_nav.setStyleSheet("font-size:20px; font-weight:bold; color:#777;")
        self.bar_nav = QProgressBar()
        gnl.addWidget(self.lbl_nav); gnl.addWidget(self.bar_nav)
        gn.setLayout(gnl)

        # Arm
        ga = QGroupBox("🦾 Arm Joints (IK)"); gal = QVBoxLayout()
        self.lbl_j2 = QLabel("Joint 2: 0°")
        self.sl_j2 = QSlider(Qt.Orientation.Horizontal); self.sl_j2.setRange(0,180); self.sl_j2.setEnabled(False)
        self.lbl_j3 = QLabel("Joint 3: 0°")
        self.sl_j3 = QSlider(Qt.Orientation.Horizontal); self.sl_j3.setRange(0,180); self.sl_j3.setEnabled(False)
        gal.addWidget(self.lbl_j2); gal.addWidget(self.sl_j2)
        gal.addWidget(self.lbl_j3); gal.addWidget(self.sl_j3)
        ga.setLayout(gal)

        lv.addWidget(gn); lv.addWidget(ga); lv.addStretch()

        # [Right] AI & Log
        right = QWidget(); rv = QVBoxLayout(); right.setLayout(rv)
        
        gai = QGroupBox("🧠 AI Feedback")
        self.ai_view = QTextEdit(); self.ai_view.setReadOnly(True)
        self.btn_ai = QPushButton("✨ Analyze Logs")
        self.btn_ai.clicked.connect(self.run_ai)
        self.btn_ai.setStyleSheet("background-color:#0078d7; padding:10px; font-weight:bold;")
        rv.addWidget(gai); rv.addWidget(self.ai_view); rv.addWidget(self.btn_ai)
        
        glog = QGroupBox("📜 Realtime Logs")
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True)
        rv.addWidget(glog); rv.addWidget(self.log_view)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left); splitter.addWidget(right); splitter.setSizes([400,600])
        layout.addWidget(splitter)
        self.setLayout(layout)

    @pyqtSlot(dict)
    def handle_data(self, data):
        # 1. Firebase Save
        if self.db_ref:
            try:
                data['ts'] = datetime.datetime.now().isoformat()
                self.db_ref.push(data)
            except: pass
        
        # 2. Buffer for AI
        self.recent_logs.append(data)
        if len(self.recent_logs) > 20: self.recent_logs.pop(0)

        # 3. GUI Update
        dtype = data.get("type")
        if dtype == "nav":
            st = data.get("status","stopped")
            self.lbl_nav.setText(st.upper())
            self.bar_nav.setValue(data.get("progress",0))
            color = "#4caf50" if st == "moving" else "#777"
            self.lbl_nav.setStyleSheet(f"font-size:20px; font-weight:bold; color:{color};")
            self.log(f"Nav: {st}")
        elif dtype == "joint":
            jid = data.get("id"); ang = int(data.get("angle",0))
            if jid == 2: self.sl_j2.setValue(ang); self.lbl_j2.setText(f"Joint 2: {ang}°")
            elif jid == 3: self.sl_j3.setValue(ang); self.lbl_j3.setText(f"Joint 3: {ang}°")
            self.log(f"Joint {jid} -> {ang}°")
        elif dtype == "grasp":
            self.log(f"Gripper: {data.get('status')}")

    def run_ai(self):
        self.ai_view.setText("Analysing...")
        self.worker = AIAnalysisWorker(self.recent_logs)
        self.worker.result_signal.connect(lambda s: self.ai_view.setText(s))
        self.worker.start()

    def log(self, msg):
        self.log_view.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = JetTankGUI()
    gui.show()
    sys.exit(app.exec())
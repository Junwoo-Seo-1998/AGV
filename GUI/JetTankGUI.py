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
                             QProgressBar, QSlider, QGridLayout, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, pyqtSlot, QThread
from PyQt6.QtGui import QFont

# ==========================================================
# [설정] 환경 변수(.env) 로드
# ==========================================================
load_dotenv() 

BROKER_IP = os.getenv("BROKER_IP", "127.0.0.1") 
FIREBASE_KEY = os.getenv("FIREBASE_KEY")
FIREBASE_URL = os.getenv("FIREBASE_URL")
GMS_KEY = os.getenv("GMS_KEY")

TOPIC_SUB = "ssafy_agv_robotpal/data"
TOPIC_PUB = "ssafy_agv_robotpal/command"

# ==========================================================
# 워커 클래스 1: MQTT 통신
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
            print(f"🔌 Connecting to Broker: {BROKER_IP}...")
            self.client.connect(BROKER_IP, 1883, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"MQTT Connection Failed: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ MQTT Connected")
            client.subscribe(TOPIC_SUB)
        else:
            print(f"⚠️ MQTT Connection Failed (Code: {rc})")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            self.msg_signal.emit(data)
        except: pass
    
    def send_command(self, cmd_data):
        try:
            payload = json.dumps(cmd_data)
            self.client.publish(TOPIC_PUB, payload)
        except Exception as e:
            print(f"Send Error: {e}")

# ==========================================================
# 워커 클래스 2: AI 로그 분석 (Firebase 연동)
# ==========================================================
class AIAnalysisWorker(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, db_ref, local_logs):
        super().__init__()
        self.db_ref = db_ref       # Firebase 참조
        self.local_logs = local_logs # 로컬 백업용 (연결 실패 시 사용)

    def run(self):
        log_data = []
        source_msg = "Local Memory"

        try:
            # 1. Firebase에서 데이터 가져오기 시도
            if self.db_ref:
                # 최근 30개의 로그만 가져오기 (limit_to_last)
                snapshot = self.db_ref.order_by_key().limit_to_last(30).get()
                
                if snapshot:
                    # Firebase는 {key: val, ...} 형태이므로 값만 추출해서 리스트로 변환
                    log_data = list(snapshot.values())
                    source_msg = "Firebase Cloud"
                else:
                    # DB가 비어있으면 로컬 사용
                    log_data = list(self.local_logs)
            else:
                log_data = list(self.local_logs)

            # 데이터가 비어있는 경우 처리
            if not log_data:
                self.result_signal.emit("⚠️ 분석할 로그 데이터가 없습니다.")
                return

            # 2. Gemini에게 보낼 프롬프트 구성
            log_str = json.dumps(log_data, indent=2, ensure_ascii=False)
            prompt = (
                f"데이터 출처: {source_msg}\n"
                f"다음은 로봇의 주행 및 센서 로그입니다:\n{log_str}\n\n"
                f"1. 주요 작업 내용 요약\n"
                f"2. 주행 안정성 평가\n"
                f"3. 개선할 점이나 조언\n"
                f"위 항목을 간단명료하게 분석해줘."
            )

            # 3. Gemini API 호출
            if not GMS_KEY:
                self.result_signal.emit("❌ Error: .env 파일에 GMS_KEY가 없습니다.")
                return

            url = f"https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GMS_KEY}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            headers = {"Content-Type": "application/json"}

            response = requests.post(url, headers=headers, data=json.dumps(payload))

            if response.status_code != 200:
                self.result_signal.emit(f"API Error: {response.status_code} - {response.text}")
                return

            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                gemini_text = data["candidates"][0]["content"]["parts"][0]["text"]
                self.result_signal.emit(f"[{source_msg} 분석 결과]\n{gemini_text}")
            else:
                self.result_signal.emit("⚠️ API 응답에 분석 결과가 없습니다.")

        except Exception as e:
            self.result_signal.emit(f"Error during analysis: {str(e)}")

# ==========================================================
# 메인 GUI 클래스
# ==========================================================
class JetTankGUI(QWidget):
    def __init__(self):
        super().__init__()
        
        self.init_firebase()
        
        self.mqtt = MqttWorker()
        self.mqtt.msg_signal.connect(self.handle_data)
        self.mqtt.start()
        
        self.recent_logs = deque(maxlen=100)
        self.last_cmd_args = (None, None)

        self.initUI()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def init_firebase(self):
        if not FIREBASE_KEY or not FIREBASE_URL:
            print("⚠️ Firebase 설정이 .env에 없습니다. (로컬 모드로 실행)")
            self.db_ref = None
            return

        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(FIREBASE_KEY)
                firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
            self.db_ref = db.reference('robot_logs')
            print("✅ Firebase Connected Successfully!")
        except Exception as e:
            print(f"❌ Firebase Init Failed: {e}")
            self.db_ref = None

    def initUI(self):
        self.setWindowTitle("JetTank AI Control Center (WASD to Drive)")
        self.resize(1100, 700)
        self.setStyleSheet("background-color:#2b2b2b; color:#e0e0e0; font-family:Arial;")

        layout = QHBoxLayout()
        
        # [왼쪽 패널]
        left = QWidget(); lv = QVBoxLayout(); left.setLayout(lv)
        
        # 1. Nav
        gn = QGroupBox("🚀 Navigation"); gnl = QVBoxLayout()
        self.lbl_nav = QLabel("STOPPED")
        self.lbl_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_nav.setStyleSheet("font-size:20px; font-weight:bold; color:#777;")
        self.bar_nav = QProgressBar()
        gnl.addWidget(self.lbl_nav); gnl.addWidget(self.bar_nav)
        gn.setLayout(gnl)

        # 2. Control
        gc = QGroupBox("🎮 Remote Control (WASD)"); gcl = QGridLayout()
        self.btn_w = QPushButton("▲"); self.btn_w.clicked.connect(lambda: self.pub_cmd(0.3, 0.3))
        self.btn_a = QPushButton("◀"); self.btn_a.clicked.connect(lambda: self.pub_cmd(-0.2, 0.2))
        self.btn_s = QPushButton("▼"); self.btn_s.clicked.connect(lambda: self.pub_cmd(-0.3, -0.3))
        self.btn_d = QPushButton("▶"); self.btn_d.clicked.connect(lambda: self.pub_cmd(0.2, -0.2))
        self.btn_stop = QPushButton("STOP (Space)"); self.btn_stop.clicked.connect(lambda: self.pub_cmd(0.0, 0.0))
        
        for btn in [self.btn_w, self.btn_a, self.btn_s, self.btn_d, self.btn_stop]:
            btn.setStyleSheet("font-size:16px; font-weight:bold; padding:10px; background-color:#444;")
        self.btn_stop.setStyleSheet("background-color:#d32f2f; color:white; font-weight:bold;")

        gcl.addWidget(self.btn_w, 0, 1)
        gcl.addWidget(self.btn_a, 1, 0)
        gcl.addWidget(self.btn_stop, 1, 1)
        gcl.addWidget(self.btn_d, 1, 2)
        gcl.addWidget(self.btn_s, 2, 1)
        gc.setLayout(gcl)

        # 3. Arm
        ga = QGroupBox("🦾 Arm Joints"); gal = QVBoxLayout()
        self.lbl_j2 = QLabel("Joint 2: 0°")
        self.sl_j2 = QSlider(Qt.Orientation.Horizontal); self.sl_j2.setRange(0,180); self.sl_j2.setEnabled(False)
        self.lbl_j3 = QLabel("Joint 3: 0°")
        self.sl_j3 = QSlider(Qt.Orientation.Horizontal); self.sl_j3.setRange(0,180); self.sl_j3.setEnabled(False)
        gal.addWidget(self.lbl_j2); gal.addWidget(self.sl_j2)
        gal.addWidget(self.lbl_j3); gal.addWidget(self.sl_j3)
        ga.setLayout(gal)

        lv.addWidget(gn); lv.addWidget(gc); lv.addWidget(ga); lv.addStretch()

        # [오른쪽 패널]
        right = QWidget(); rv = QVBoxLayout(); right.setLayout(rv)
        
        # AI Feedback
        gai = QGroupBox("🧠 AI Feedback")
        self.ai_view = QTextEdit(); self.ai_view.setReadOnly(True)
        self.btn_ai = QPushButton("✨ Analyze Logs")
        self.btn_ai.clicked.connect(self.run_ai)
        self.btn_ai.setStyleSheet("background-color:#0078d7; padding:10px; font-weight:bold;")
        rv.addWidget(gai); rv.addWidget(self.ai_view); rv.addWidget(self.btn_ai)
        
        # Realtime Logs
        glog = QGroupBox("📜 Realtime Logs")
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True)
        font = QFont("Consolas", 10)
        self.log_view.setFont(font)
        rv.addWidget(glog); rv.addWidget(self.log_view)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left); splitter.addWidget(right); splitter.setSizes([450, 650])
        layout.addWidget(splitter)
        self.setLayout(layout)

    # ---------------------------------------------------------
    # 키보드 이벤트
    # ---------------------------------------------------------
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
        if self.last_cmd_args == (left, right):
            return
        self.last_cmd_args = (left, right)
        
        cmd = {"type": "drive", "left": left, "right": right}
        self.mqtt.send_command(cmd)

    # ---------------------------------------------------------
    # 데이터 핸들러 (수신)
    # ---------------------------------------------------------
    @pyqtSlot(dict)
    def handle_data(self, data):
        # 1. Firebase에 저장 (클라우드)
        if self.db_ref:
            try:
                data_to_save = data.copy()
                data_to_save['timestamp'] = datetime.datetime.now().isoformat()
                self.db_ref.push(data_to_save)
            except Exception as e:
                print(f"Firebase Push Error: {e}")
        
        # 2. 로컬 버퍼에 저장
        self.recent_logs.append(data)

        # 3. GUI 업데이트
        dtype = data.get("type")
        
        if dtype == "nav":
            st = data.get("status", "stopped")
            tgt = data.get("target", "Manual")
            l_val = data.get("val_l", 0.0)
            r_val = data.get("val_r", 0.0)

            self.lbl_nav.setText(f"{st.upper()} ({tgt})")
            self.bar_nav.setValue(data.get("progress", 0))
            
            color = "#4caf50" if st == "moving" else "#777"
            self.lbl_nav.setStyleSheet(f"font-size:20px; font-weight:bold; color:{color};")
            
            if st == "moving":
                self.log(f"🚗 [Nav] Moving | L:{l_val:.2f} R:{r_val:.2f}")
            else:
                self.log(f"🛑 [Nav] Stopped")

        elif dtype == "joint":
            jid = data.get("id")
            ang = int(data.get("angle", 0))
            
            if jid == 2: 
                self.sl_j2.setValue(ang); self.lbl_j2.setText(f"Joint 2: {ang}°")
            elif jid == 3: 
                self.sl_j3.setValue(ang); self.lbl_j3.setText(f"Joint 3: {ang}°")
            
            self.log(f"🦾 [Servo] ID:{jid} -> {ang}°")

        elif dtype == "grasp":
            status = data.get('status')
            self.log(f"✊ [Gripper] {status.upper()}")

        elif dtype == "ocr":
            text = data.get('text')
            conf = data.get('confidence', 0)
            self.log(f"👀 [OCR] Result: '{text}' (Conf: {conf:.2f})")
            
        elif dtype == "log":
            msg = data.get("msg", "")
            self.log(f"🤖 [System] {msg}")

    def run_ai(self):
        # [수정됨] 워커에게 db_ref 전달
        self.ai_view.setText("🔍 Fetching Logs from Cloud & Analyzing...")
        self.worker = AIAnalysisWorker(self.db_ref, self.recent_logs)
        self.worker.result_signal.connect(lambda s: self.ai_view.setText(s))
        self.worker.start()

    def log(self, msg):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_view.append(f"[{ts}] {msg}")
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = JetTankGUI()
    gui.show()
    sys.exit(app.exec())
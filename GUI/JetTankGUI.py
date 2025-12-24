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

# PyQt6 모듈 임포트 (QGridLayout 포함)
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QPushButton, QLabel, QSplitter, QGroupBox, 
                             QProgressBar, QSlider, QGridLayout, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, pyqtSlot, QThread
from PyQt6.QtGui import QFont

# ==========================================================
# [사용자 설정] 키/주소 입력 필수
# ==========================================================
# 로봇과 통신할 브로커 IP (로컬에서 브로커 실행 시 127.0.0.1)
BROKER_IP = "127.0.0.1" 
TOPIC_SUB = "ssafy_agv_robotpal/data"    # 로봇 -> GUI (로그 수신)
TOPIC_PUB = "ssafy_agv_robotpal/command" # GUI -> 로봇 (명령 송신)

load_dotenv() # .env 파일 로드 (Gemini API 키 등)

# Firebase 설정 (키 파일 경로 및 DB URL 수정 필요)
FIREBASE_KEY = "path/to/firebase_key.json"
FIREBASE_URL = "https://your-project.firebaseio.com/"

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
            # 수신된 JSON 데이터 파싱 후 시그널 전송
            data = json.loads(msg.payload.decode())
            self.msg_signal.emit(data)
        except: pass
    
    # [기능] 로봇 제어 명령 전송
    def send_command(self, cmd_data):
        try:
            payload = json.dumps(cmd_data)
            self.client.publish(TOPIC_PUB, payload)
        except Exception as e:
            print(f"Send Error: {e}")

# ==========================================================
# 워커 클래스 2: AI 로그 분석 (Gemini)
# ==========================================================
class AIAnalysisWorker(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, logs):
        super().__init__()
        self.logs = logs

    def run(self):
        try:
            # 로그 데이터를 문자열로 변환
            log_str = json.dumps(self.logs, indent=2, ensure_ascii=False)
            prompt = f"로봇 로그 분석:\n{log_str}\n\n1. 작업 내용\n2. 안정성 평가\n3. 조언\n요약해서 알려줘."

            # Gemini API 호출
            api_key = os.getenv("GMS_KEY")
            url = f"https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"

            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ]
            }

            headers = {"Content-Type": "application/json"}
            response = requests.post(url, headers=headers, data=json.dumps(payload))

            if response.status_code != 200:
                self.result_signal.emit(f"API Error: {response.status_code} - {response.text}")
                return

            data = response.json()
            gemini_text = data["candidates"][0]["content"]["parts"][0]["text"]
            self.result_signal.emit(gemini_text)

        except Exception as e:
            self.result_signal.emit(f"Error: {str(e)}")

# ==========================================================
# 메인 GUI 클래스
# ==========================================================
class JetTankGUI(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. Firebase 초기화
        self.init_firebase()
        
        # 2. MQTT 워커 시작
        self.mqtt = MqttWorker()
        self.mqtt.msg_signal.connect(self.handle_data)
        self.mqtt.start()
        
        # 3. 로그 버퍼 (최근 100개 저장)
        self.recent_logs = deque(maxlen=100)

        # 4. UI 구성
        self.initUI()
        
        # 5. 키보드 입력을 받기 위해 포커스 설정
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def init_firebase(self):
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(FIREBASE_KEY)
                firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_URL})
            self.db_ref = db.reference('robot_logs')
        except: 
            # 키 파일이 없어도 앱이 죽지 않도록 예외 처리
            # print("Firebase Init Failed (Check Key Path)")
            self.db_ref = None

    def initUI(self):
        self.setWindowTitle("JetTank AI Control Center (WASD to Drive)")
        self.resize(1100, 700)
        self.setStyleSheet("background-color:#2b2b2b; color:#e0e0e0; font-family:Arial;")

        layout = QHBoxLayout()
        
        # [왼쪽 패널] 상태 모니터링 및 제어
        left = QWidget(); lv = QVBoxLayout(); left.setLayout(lv)
        
        # 1. Navigation Status (주행 상태)
        gn = QGroupBox("🚀 Navigation"); gnl = QVBoxLayout()
        self.lbl_nav = QLabel("STOPPED")
        self.lbl_nav.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_nav.setStyleSheet("font-size:20px; font-weight:bold; color:#777;")
        self.bar_nav = QProgressBar()
        gnl.addWidget(self.lbl_nav); gnl.addWidget(self.bar_nav)
        gn.setLayout(gnl)

        # 2. Remote Control Panel (원격 제어)
        gc = QGroupBox("🎮 Remote Control (WASD)"); gcl = QGridLayout()
        self.btn_w = QPushButton("▲"); self.btn_w.clicked.connect(lambda: self.pub_cmd(0.3, 0.3))
        self.btn_a = QPushButton("◀"); self.btn_a.clicked.connect(lambda: self.pub_cmd(-0.2, 0.2))
        self.btn_s = QPushButton("▼"); self.btn_s.clicked.connect(lambda: self.pub_cmd(-0.3, -0.3))
        self.btn_d = QPushButton("▶"); self.btn_d.clicked.connect(lambda: self.pub_cmd(0.2, -0.2))
        self.btn_stop = QPushButton("STOP (Space)"); self.btn_stop.clicked.connect(lambda: self.pub_cmd(0.0, 0.0))
        
        # 버튼 스타일링
        for btn in [self.btn_w, self.btn_a, self.btn_s, self.btn_d, self.btn_stop]:
            btn.setStyleSheet("font-size:16px; font-weight:bold; padding:10px; background-color:#444;")
        self.btn_stop.setStyleSheet("background-color:#d32f2f; color:white; font-weight:bold;")

        # 그리드 배치
        gcl.addWidget(self.btn_w, 0, 1)
        gcl.addWidget(self.btn_a, 1, 0)
        gcl.addWidget(self.btn_stop, 1, 1)
        gcl.addWidget(self.btn_d, 1, 2)
        gcl.addWidget(self.btn_s, 2, 1)
        gc.setLayout(gcl)

        # 3. Arm Joints (로봇 팔 - 수신 전용)
        ga = QGroupBox("🦾 Arm Joints"); gal = QVBoxLayout()
        self.lbl_j2 = QLabel("Joint 2: 0°")
        self.sl_j2 = QSlider(Qt.Orientation.Horizontal); self.sl_j2.setRange(0,180); self.sl_j2.setEnabled(False)
        self.lbl_j3 = QLabel("Joint 3: 0°")
        self.sl_j3 = QSlider(Qt.Orientation.Horizontal); self.sl_j3.setRange(0,180); self.sl_j3.setEnabled(False)
        gal.addWidget(self.lbl_j2); gal.addWidget(self.sl_j2)
        gal.addWidget(self.lbl_j3); gal.addWidget(self.sl_j3)
        ga.setLayout(gal)

        lv.addWidget(gn); lv.addWidget(gc); lv.addWidget(ga); lv.addStretch()

        # [오른쪽 패널] 로그 및 AI 분석
        right = QWidget(); rv = QVBoxLayout(); right.setLayout(rv)
        
        # AI Feedback 영역
        gai = QGroupBox("🧠 AI Feedback")
        self.ai_view = QTextEdit(); self.ai_view.setReadOnly(True)
        self.btn_ai = QPushButton("✨ Analyze Logs")
        self.btn_ai.clicked.connect(self.run_ai)
        self.btn_ai.setStyleSheet("background-color:#0078d7; padding:10px; font-weight:bold;")
        rv.addWidget(gai); rv.addWidget(self.ai_view); rv.addWidget(self.btn_ai)
        
        # 실시간 로그 영역
        glog = QGroupBox("📜 Realtime Logs")
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True)
        # 로그 폰트 조정
        font = QFont("Consolas", 10)
        self.log_view.setFont(font)
        rv.addWidget(glog); rv.addWidget(self.log_view)

        # 패널 나누기
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left); splitter.addWidget(right); splitter.setSizes([450, 650])
        layout.addWidget(splitter)
        self.setLayout(layout)

    # ---------------------------------------------------------
    # [이벤트 핸들러] 키보드 제어
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
        """MQTT로 주행 명령 전송"""
        cmd = {"type": "drive", "left": left, "right": right}
        self.mqtt.send_command(cmd)

    # ---------------------------------------------------------
    # [데이터 핸들러] 수신된 로그 처리
    # ---------------------------------------------------------
    @pyqtSlot(dict)
    def handle_data(self, data):
        # 1. Firebase 저장
        if self.db_ref:
            try:
                data['ts'] = datetime.datetime.now().isoformat()
                self.db_ref.push(data)
            except: pass
        
        # 2. AI 분석용 버퍼 저장
        self.recent_logs.append(data)
        if len(self.recent_logs) > 20: self.recent_logs.popleft()

        # 3. GUI 업데이트 및 로그 출력
        dtype = data.get("type")
        
        if dtype == "nav":
            st = data.get("status", "stopped")
            tgt = data.get("target", "Manual")
            
            # 모터 상세 값 (없으면 0.0)
            l_val = data.get("val_l", 0.0)
            r_val = data.get("val_r", 0.0)

            # UI 상태바
            self.lbl_nav.setText(f"{st.upper()} ({tgt})")
            self.bar_nav.setValue(data.get("progress", 0))
            
            # 색상 변경
            color = "#4caf50" if st == "moving" else "#777"
            self.lbl_nav.setStyleSheet(f"font-size:20px; font-weight:bold; color:{color};")
            
            # 상세 로그 출력
            if st == "moving":
                self.log(f"🚗 [Nav] Moving | L:{l_val:.2f} R:{r_val:.2f}")
            else:
                # 멈춤 로그는 너무 자주 찍히지 않도록 조절 가능하지만 여기선 다 출력
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
            # 로봇 내부 print 메시지 (색상 감지, 목표 발견 등)
            msg = data.get("msg", "")
            self.log(f"🤖 [System] {msg}")

    def run_ai(self):
        """AI 분석 요청"""
        self.ai_view.setText("🔍 Analysing logs via Gemini...")
        self.worker = AIAnalysisWorker(self.recent_logs)
        self.worker.result_signal.connect(lambda s: self.ai_view.setText(s))
        self.worker.start()

    def log(self, msg):
        """로그 창에 텍스트 추가"""
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_view.append(f"[{ts}] {msg}")
        # 스크롤 자동 내리기
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = JetTankGUI()
    gui.show()
    sys.exit(app.exec())
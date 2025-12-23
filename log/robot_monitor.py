# 파일명: robot_monitor.py
import json
import functools
import paho.mqtt.client as mqtt

# [설정] PC(GUI) IP 주소 (사용자가 입력한 값 유지)
BROKER_IP = "70.12.107.93"

class RobotMonitor:
    def __init__(self):
        self.client = mqtt.Client()
        
        # [디버깅] 연결 상태를 확인하기 위한 콜백 함수 연결
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish

        print(f">>> [Monitor] Connecting to Broker: {BROKER_IP}...")
        try:
            # 5초간 연결 시도
            self.client.connect(BROKER_IP, 1883, 5)
            self.client.loop_start()
        except Exception as e:
            print(f">>> [Monitor] ❌ Socket Connection Error: {e}")
            print("    (PC 방화벽 해제 및 IP 주소가 정확한지 확인하세요)")

    # --- 연결 성공/실패 시 호출됨 ---
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f">>> [Monitor] ✅ MQTT Connected Successfully! (IP: {BROKER_IP})")
        else:
            print(f">>> [Monitor] ❌ MQTT Connection Failed! Return Code: {rc}")

    # --- 연결 끊김 시 호출됨 ---
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f">>> [Monitor] ⚠️ Disconnected unexpectedly. Code: {rc}")

    # --- 메시지 전송 성공 시 호출됨 ---
    def on_publish(self, client, userdata, mid):
        # 메시지가 브로커로 잘 날아갔을 때 찍힘
        # 너무 시끄러우면 주석 처리 가능
        print(f">>> [Monitor] 📤 Data sent (Message ID: {mid})")

    def _send(self, data):
        """데이터 전송 (GUI 및 Firebase용)"""
        try:
            json_str = json.dumps(data)
            # 보내려는 데이터 미리보기
            # print(f">>> [Monitor] Sending: {json_str}") 
            self.client.publish("ssafy_agv_robotpal/data", json_str)
        except Exception as e:
            print(f">>> [Monitor] ❌ Send Error: {e}")

    # ---------------------------------------------------------
    # [1] 주행 추적 (Robot 클래스용)
    # ---------------------------------------------------------
    def track_nav(self, status_name):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                speed = args[1] if len(args) > 1 else 0.0
                if status_name == "stopped": speed = 0.0
                
                payload = {
                    "type": "nav",
                    "status": status_name,
                    "progress": int(abs(speed) * 100),
                    "target": "Manual"
                }
                self._send(payload)
                return result
            return wrapper
        return decorator

    # ---------------------------------------------------------
    # [2] 단일 서보/그리퍼 추적
    # ---------------------------------------------------------
    def track_servo(self):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                try:
                    srv_id = args[0]
                    angle = args[1]
                    # ID 1번을 그리퍼로 가정
                    if srv_id == 1:
                        status = "holding" if angle < 40 else "released"
                        self._send({"type": "grasp", "status": status, "angle": angle})
                    # 일반 관절 로그
                    self._send({"type": "joint", "id": srv_id, "angle": angle})
                except: pass
                return result
            return wrapper
        return decorator

    # ---------------------------------------------------------
    # [3] IK 좌표 추적
    # ---------------------------------------------------------
    def track_ik(self):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                angles = func(*args, **kwargs)
                if angles and isinstance(angles, list) and len(angles) >= 2:
                    ang2 = int(angles[0] + 90)
                    ang3 = int(angles[1])
                    self._send({"type": "joint", "id": 2, "angle": ang2})
                    self._send({"type": "joint", "id": 3, "angle": ang3})
                    self._send({"type": "log", "msg": f"IK Move: ({ang2}, {ang3})"})
                return angles
            return wrapper
        return decorator

    # ---------------------------------------------------------
    # [4] 비전 결과 추적
    # ---------------------------------------------------------
    def track_vision(self, vtype):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                res = func(*args, **kwargs)
                if res:
                    payload = {"type": vtype}
                    if vtype == "color":
                        payload["color_name"] = res[0]
                        payload["rgb_hex"] = res[1]
                    elif vtype == "ocr":
                        payload["text"] = res[0]
                        payload["confidence"] = res[1]
                    self._send(payload)
                return res
            return wrapper
        return decorator

# 전역 인스턴스
monitor = RobotMonitor()
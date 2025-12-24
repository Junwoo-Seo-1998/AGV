# 파일명: robot_monitor.py
import json
import functools
import paho.mqtt.client as mqtt

# [중요] PC의 IP 주소를 입력하세요 (로컬 테스트 시 127.0.0.1)
BROKER_IP = "127.0.0.1" 
# BROKER_IP = "192.168.0.X" 

class RobotMonitor:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        self.client.on_message = self.on_message
        
        # 외부 제어 콜백 함수 저장용
        self.command_callback = None

        print(f">>> [Monitor] Connecting to Broker: {BROKER_IP}...")
        try:
            self.client.connect(BROKER_IP, 1883, 5)
            self.client.loop_start()
        except Exception as e:
            print(f">>> [Monitor] ❌ Socket Connection Error: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f">>> [Monitor] ✅ MQTT Connected! (IP: {BROKER_IP})")
            # GUI 명령 수신을 위한 구독
            client.subscribe("ssafy_agv_robotpal/command")
        else:
            print(f">>> [Monitor] ❌ Connection Failed: {rc}")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0: print(f">>> [Monitor] ⚠️ Disconnected: {rc}")

    def on_publish(self, client, userdata, mid):
        pass

    def on_message(self, client, userdata, msg):
        """GUI로부터 명령 수신 시 호출"""
        try:
            payload = json.loads(msg.payload.decode())
            if self.command_callback:
                self.command_callback(payload)
        except Exception as e:
            print(f">>> [Monitor] Message Error: {e}")

    def _send(self, data):
        """GUI로 데이터 전송"""
        try:
            self.client.publish("ssafy_agv_robotpal/data", json.dumps(data))
        except: pass

    def set_callback(self, func):
        """외부에서 명령 처리 함수 등록"""
        self.command_callback = func

    # ----------------------------------------------------------------
    # [트래킹 데코레이터]
    # ----------------------------------------------------------------
    
    def track_nav(self, status_name):
        """주행 상태(이동/정지) 추적"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                # args[0]은 self, args[1]은 보통 speed
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

    def track_ik(self):
        """[복구됨] IK(역운동학) 제어 추적"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                try:
                    # xyInput(x, y) 호출 시 좌표 로깅
                    x = args[1]
                    y = args[2]
                    self._send({"type": "log", "msg": f"IK Move: ({x}, {y})"})
                except: pass
                return result
            return wrapper
        return decorator

    def track_servo(self):
        """[복구됨] 개별 서보 모터 제어 추적"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # servoAngleCtrl(id, angle, ...)
                result = func(*args, **kwargs)
                try:
                    sid = args[1]
                    ang = args[2]
                    self._send({"type": "joint", "id": sid, "angle": int(ang)})
                except: pass
                return result
            return wrapper
        return decorator


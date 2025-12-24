# 파일명: robot_monitor.py
import json
import functools
import paho.mqtt.client as mqtt

# BROKER_IP = "70.12.107.93" # PC IP 확인 필수
BROKER_IP = "127.0.0.1"

class RobotMonitor:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        self.client.on_message = self.on_message # [추가] 메시지 수신 핸들러
        
        # [추가] 외부에서 등록할 콜백 함수 (로봇 제어용)
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
            # [추가] GUI 명령 토픽 구독
            client.subscribe("ssafy_agv_robotpal/command")
        else:
            print(f">>> [Monitor] ❌ Connection Failed: {rc}")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0: print(f">>> [Monitor] ⚠️ Disconnected: {rc}")

    def on_publish(self, client, userdata, mid):
        pass

    # [추가] 메시지 수신 시 호출
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            # 콜백함수가 등록되어 있다면 호출 (로봇 제어)
            if self.command_callback:
                self.command_callback(payload)
        except Exception as e:
            print(f">>> [Monitor] Message Error: {e}")

    def _send(self, data):
        try:
            self.client.publish("ssafy_agv_robotpal/data", json.dumps(data))
        except: pass

    # [추가] 콜백 등록 메서드
    def set_callback(self, func):
        self.command_callback = func

    # (이하 track_nav, track_servo 등의 데코레이터는 기존 유지)
    def track_nav(self, status_name):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                speed = args[1] if len(args) > 1 else 0.0
                if status_name == "stopped": speed = 0.0
                payload = {"type": "nav", "status": status_name, "progress": int(abs(speed) * 100), "target": "Manual"}
                self._send(payload)
                return result
            return wrapper
        return decorator

monitor = RobotMonitor()
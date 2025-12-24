# 파일명: auto_logger.py
import sys
import functools # [추가] 데코레이터용

print(">>> [AutoLogger] System Hooking Initiated...")

# =========================================================
# 1. 라이브러리 가져오기
# =========================================================
try:
    from jetbot import Robot
    print("[AutoLogger] Library found: jetbot.Robot")
except ImportError:
    try:
        from jetbot import Robot
        print("[AutoLogger] Local file found: robot.py")
    except ImportError:
        print("[AutoLogger] ❌ Error: 'Robot' 클래스를 찾을 수 없습니다.")
        sys.exit()

try:
    from SCSCtrl import TTLServo
    print("[AutoLogger] Library found: SCSCtrl.TTLServo")
except ImportError:
    TTLServo = None

try:
    from .robot_monitor import monitor
except ImportError:
    print("[AutoLogger] ❌ Error: 'robot_monitor.py' 파일이 없습니다.")
    sys.exit()

# =========================================================
# 2. 기본 Robot 클래스 후킹 (기존 로직 유지)
# =========================================================
print(">>> [AutoLogger] Injecting Hooks into Robot Class...")

if hasattr(Robot, 'forward'):
    Robot.forward = monitor.track_nav("moving")(Robot.forward)
if hasattr(Robot, 'backward'):
    Robot.backward = monitor.track_nav("moving")(Robot.backward)
if hasattr(Robot, 'left'):
    Robot.left = monitor.track_nav("turning")(Robot.left)
if hasattr(Robot, 'right'):
    Robot.right = monitor.track_nav("turning")(Robot.right)
if hasattr(Robot, 'stop'):
    Robot.stop = monitor.track_nav("stopped")(Robot.stop)

if TTLServo:
    if hasattr(TTLServo, 'xyInput'):
        TTLServo.xyInput = monitor.track_ik()(TTLServo.xyInput)
    if hasattr(TTLServo, 'servoAngleCtrl'):
        TTLServo.servoAngleCtrl = monitor.track_servo()(TTLServo.servoAngleCtrl)

# =========================================================
# 3. [신규 기능] AGVHardware 전용 후킹 함수
# =========================================================
def hook_agv_drive(agv_class):
    
    # 1. __init__ 후킹: 인스턴스가 생성될 때 "제어권"을 확보합니다.
    original_init = agv_class.__init__

    @functools.wraps(original_init)
    def init_wrapper(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        print(f">>> [AutoLogger] 🎮 Remote Control Ready for {self.__class__.__name__}")
        
        # 이 내부 함수는 'self' (생성된 로봇 객체)에 접근할 수 있습니다.
        def on_remote_command(data):
            if data.get("type") == "drive":
                l = float(data.get("left", 0.0))
                r = float(data.get("right", 0.0))
                # 로봇의 모터 제어 (drive 메서드 호출)
                # 주의: 무한 루프 방지를 위해 monitor에 로그를 보내지 않는 순수 모터 제어를 하거나
                # track_nav 데코레이터가 이미 로그를 보내므로 그냥 호출해도 됩니다.
                self.drive(l, r)
                
        # 모니터에게 "명령이 오면 이 함수를 실행해"라고 등록
        monitor.set_callback(on_remote_command)

    agv_class.__init__ = init_wrapper

    # 2. drive 후킹 (로그 전송용 - 이전 답변 내용 유지)
    original_drive = agv_class.drive
    @functools.wraps(original_drive)
    def drive_wrapper(self, left, right):
        result = original_drive(self, left, right)
        try:
            speed = max(abs(left), abs(right))
            status = "moving" if speed > 0.05 else "stopped"
            monitor._send({"type": "nav", "status": status, "progress": int(speed * 100)})
        except: pass
        return result
        
    agv_class.drive = drive_wrapper
    print(">>> [AutoLogger] ✅ Custom drive hook applied!")

print(">>> [AutoLogger] Ready to hook.")
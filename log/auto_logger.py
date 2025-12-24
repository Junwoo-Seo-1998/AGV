# 파일명: auto_logger.py
import io
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
# [신규 기능] Print 가로채기 데코레이터
# =========================================================
def make_verbose(func):
    """
    함수 실행 중 발생하는 print 출력을 가로채서
    MQTT 로그로 전송하고, 원래 화면에도 출력하는 데코레이터
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 1. 표준 출력(stdout) 가로채기 준비
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured
        
        try:
            # 2. 원래 함수 실행 (이때 print는 captured에 저장됨)
            result = func(*args, **kwargs)
        except Exception as e:
            sys.stdout = original_stdout # 에러 시 복구
            print(f"Error in {func.__name__}: {e}")
            raise e
        finally:
            # 3. 표준 출력 원상복구 (무조건 실행)
            sys.stdout = original_stdout
            
        # 4. 가로챈 내용 처리
        output = captured.getvalue()
        if output:
            # 원래 화면(콘솔)에도 출력 (줄바꿈 방지)
            print(output, end='') 
            
            # MQTT로 전송 (앞뒤 공백 제거)
            clean_msg = output.strip()
            if clean_msg:
                # "🎨 색상 감지: Red" 같은 메시지가 GUI로 전송됨
                monitor._send({"type": "log", "msg": clean_msg})
                
        return result
    return wrapper
# =========================================================
# 3. [신규 기능] AGVHardware 전용 후킹 함수
# =========================================================
# 파일명: log/auto_logger.py 의 hook_agv_drive 함수 수정

def hook_agv_drive(agv_class):
    
    # 1. __init__ 후킹 (원격 제어 연결) - 기존과 동일
    original_init = agv_class.__init__

    @functools.wraps(original_init)
    def init_wrapper(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        print(f">>> [AutoLogger] 🎮 Remote Control Ready for {self.__class__.__name__}")
        
        def on_remote_command(data):
            if data.get("type") == "drive":
                l = float(data.get("left", 0.0))
                r = float(data.get("right", 0.0))
                self.drive(l, r)
        
        monitor.set_callback(on_remote_command)

    agv_class.__init__ = init_wrapper

    # 2. drive 후킹 (로그 전송) - [수정됨: 상세 속도값 전송]
    original_drive = agv_class.drive
    @functools.wraps(original_drive)
    def drive_wrapper(self, left, right):
        result = original_drive(self, left, right)
        try:
            # 절대값 중 큰 것을 대표 속도로 사용
            speed = max(abs(left), abs(right))
            status = "moving" if speed > 0.05 else "stopped"
            
            # [수정 포인트] type='nav' 메시지에 왼쪽(l), 오른쪽(r) 상세 값을 포함시킴
            monitor._send({
                "type": "nav", 
                "status": status, 
                "progress": int(speed * 100),
                "val_l": float(left),
                "val_r": float(right)
            })
        except: pass
        return result
        
    agv_class.drive = drive_wrapper
    print(">>> [AutoLogger] ✅ Custom drive hook applied (Detailed Logs)!")

print(">>> [AutoLogger] Ready to hook.")
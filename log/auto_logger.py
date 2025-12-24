# 파일명: auto_logger.py
import sys
import io
import functools
import time

print(">>> [AutoLogger] System Hooking Initiated...")

# =========================================================
# 1. 라이브러리 및 모듈 가져오기
# =========================================================
try:
    from jetbot import Robot
    print("[AutoLogger] Library found: jetbot.Robot")
except ImportError:
    try:
        from robot import Robot
        print("[AutoLogger] Local file found: robot.py")
    except ImportError:
        print("[AutoLogger] ❌ Error: 'Robot' 클래스를 찾을 수 없습니다.")
        sys.exit()

TTLServo = None
try:
    from SCSCtrl import TTLServo
    print("[AutoLogger] Library found: SCSCtrl.TTLServo")
except ImportError:
    print("[AutoLogger] ⚠️ Warning: TTLServo 모듈(SCSCtrl)을 찾을 수 없습니다. (서보 제어 로그 불가)")

try:
    from log import monitor
except ImportError:
    print("[AutoLogger] ❌ Error: 'robot_monitor.py' 파일이 없습니다.")
    sys.exit()

# =========================================================
# 2. [기능] Print 감청 데코레이터
# =========================================================
def make_verbose(func):
    # 이미 감청 장치가 달려있다면 원본 그대로 반환 (중복 방지)
    if getattr(func, '_is_verbose_hooked', False):
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured
        
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            sys.stdout = original_stdout
            print(f"Error in {func.__name__}: {e}")
            raise e
        finally:
            sys.stdout = original_stdout
            
        output = captured.getvalue()
        if output:
            print(output, end='') 
            clean_msg = output.strip()
            if clean_msg:
                monitor._send({"type": "log", "msg": clean_msg})
        return result
    
    # 플래그 설정
    wrapper._is_verbose_hooked = True
    return wrapper

# =========================================================
# 3. 기본 Robot 클래스 후킹 (중복 방지 추가)
# =========================================================
def safe_hook(cls, method_name, decorator_factory, status_name=None):
    """안전하게 후킹하는 헬퍼 함수"""
    if not hasattr(cls, method_name): return
    
    original_method = getattr(cls, method_name)
    # 이미 후킹된 메서드인지 확인 (속성 체크)
    if getattr(original_method, '_is_nav_hooked', False):
        return

    print(f">>> [AutoLogger] Hooking {cls.__name__}.{method_name}...")
    if status_name:
        wrapped_method = decorator_factory(status_name)(original_method)
    else:
        wrapped_method = decorator_factory()(original_method)
    
    # 후킹 표시
    wrapped_method._is_nav_hooked = True
    setattr(cls, method_name, wrapped_method)

print(">>> [AutoLogger] Injecting Hooks into Robot Class...")

# 안전한 후킹 적용
safe_hook(Robot, 'forward', monitor.track_nav, "moving")
safe_hook(Robot, 'backward', monitor.track_nav, "moving")
safe_hook(Robot, 'left', monitor.track_nav, "turning")
safe_hook(Robot, 'right', monitor.track_nav, "turning")
safe_hook(Robot, 'stop', monitor.track_nav, "stopped")

# =========================================================
# 4. 서보 모터(TTLServo) 후킹
# =========================================================
if TTLServo:
    print(">>> [AutoLogger] Injecting Hooks into TTLServo...")
    safe_hook(TTLServo, 'xyInput', monitor.track_ik)
    safe_hook(TTLServo, 'servoAngleCtrl', monitor.track_servo)

# =========================================================
# 5. AGVHardware 전용 후킹
# =========================================================
def hook_agv_drive(agv_class):
    # 클래스 단위 중복 체크 (또는 메서드 단위)
    if getattr(agv_class.drive, '_is_nav_hooked', False):
        print(f">>> [AutoLogger] ⚠️ {agv_class.__name__} is already hooked. Skipping.")
        return

    print(f">>> [AutoLogger] Hooking custom drive method for {agv_class.__name__}...")
    
    # (1) 초기화 후킹
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

    # (2) 주행 함수 후킹
    original_drive = agv_class.drive
    @functools.wraps(original_drive)
    def drive_wrapper(self, left, right):
        result = original_drive(self, left, right)
        try:
            speed = max(abs(left), abs(right))
            status = "moving" if speed > 0.05 else "stopped"
            monitor._send({
                "type": "nav", 
                "status": status, 
                "progress": int(speed * 100),
                "val_l": float(left),
                "val_r": float(right)
            })
        except: pass
        return result
    
    # 중복 방지 플래그 설정
    drive_wrapper._is_nav_hooked = True
    agv_class.drive = drive_wrapper
    print(">>> [AutoLogger] ✅ Custom drive hook applied (Detailed Logs & Remote)!")

print(">>> [AutoLogger] Ready.")
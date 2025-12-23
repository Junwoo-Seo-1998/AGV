# 파일명: auto_logger.py
import sys

print(">>> [AutoLogger] System Hooking Initiated...")

# =========================================================
# 1. 라이브러리 가져오기 (Import)
# =========================================================
# 사용자의 환경(Jetbot 패키지 설치 여부)에 따라 유연하게 로드합니다.

# [Robot 로드]
try:
    # 1순위: jetbot 패키지로 설치된 경우
    from jetbot import Robot
    print("[AutoLogger] Library found: jetbot.Robot")
except ImportError:
    try:
        # 2순위: 로컬 파일(robot.py)로 존재하는 경우
        from robot import Robot
        print("[AutoLogger] Local file found: robot.py")
    except ImportError:
        print("[AutoLogger] ❌ Error: 'Robot' 클래스를 찾을 수 없습니다.")
        sys.exit()

# [TTLServo 로드] (관절 제어용)
TTLServo = None
try:
    from SCSCtrl import TTLServo
    print("[AutoLogger] Library found: SCSCtrl.TTLServo")
except ImportError:
    try:
        import TTLServo
        print("[AutoLogger] Local file found: TTLServo.py")
    except ImportError:
        print("[AutoLogger] ⚠️ Warning: TTLServo 모듈을 찾을 수 없습니다. (관절 추적 불가)")

# [Monitor 로드] (우리가 만든 모니터링 도구)
try:
    from .robot_monitor import monitor
except ImportError:
    print("[AutoLogger] ❌ Error: 'robot_monitor.py' 파일이 없습니다.")
    sys.exit()


# =========================================================
# 2. 후킹(Hooking) 적용
# =========================================================
# Robot 클래스는 SingletonConfigurable이므로,
# 클래스 자체의 메서드를 바꿔치기하면 이미 생성된 인스턴스에도 적용됩니다.

print(">>> [AutoLogger] Injecting Hooks into Robot Class...")

# 주행 함수 (Robot 클래스의 메서드) 후킹
# monitor.track_nav 데코레이터가 원본 함수를 감싸서 로그 전송 기능을 추가합니다.
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


# 관절 제어 함수 (TTLServo 모듈의 함수) 후킹
if TTLServo:
    print(">>> [AutoLogger] Injecting Hooks into TTLServo...")
    
    # IK 제어 함수
    if hasattr(TTLServo, 'xyInput'):
        TTLServo.xyInput = monitor.track_ik()(TTLServo.xyInput)
    
    # 단일 서보 제어 함수
    if hasattr(TTLServo, 'servoAngleCtrl'):
        TTLServo.servoAngleCtrl = monitor.track_servo()(TTLServo.servoAngleCtrl)

print(">>> [AutoLogger] ✅ All Hooks Applied Successfully!")
print(">>> [AutoLogger] Now running your main code...")
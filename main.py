import torch
import time
from torchvision.models import resnet18


# 경로 설정 코드 삭제! 그냥 import 하면 됩니다.
from module.hardware import AGVHardware
from module.driving_logic import LineTrackingBrain
from module.mission_manager import MissionManager
from SCSCtrl import TTLServo

# 1. 모델 로드
model = resnet18(pretrained=False)
model.fc = torch.nn.Linear(512, 2)
model.load_state_dict(torch.load('best_steering_model_xy_test.pth'))
device = torch.device('cuda')
model = model.to(device).eval().half()

# 2. 시스템 초기화
agv = AGVHardware()
brain = LineTrackingBrain(model, device)
manager = MissionManager(agv, brain)

# 타겟 설정
manager.context.target_plate = "187고1604"

TTLServo.servoAngleCtrl(1, 0, 1, 500)
TTLServo.servoAngleCtrl(2, 0, 1, 500)
TTLServo.servoAngleCtrl(3, 0, 1, 500)
TTLServo.servoAngleCtrl(4, 100, 1, 500)
TTLServo.servoAngleCtrl(5, 25, 1, 500)
# 3. 실행
try:
    print("🏁 AGV 출발!")
    manager.set_state("FIND_TARGET")
    
    while True:
        manager.update()
        time.sleep(0.001)

except KeyboardInterrupt:
    print("\n🛑 사용자 강제 종료 요청")

except Exception as e:
    print(f"\n❌ 오류 발생: {e}")

finally:
    # 에러가 나든, 멈추든 무조건 실행되는 구간
    if 'agv' in locals():
        agv.close()  # 카메라와 모터 모두 끄기
    print("✅ 시스템 안전 종료 (카메라 해제됨)")
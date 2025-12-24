import torch
import time
from torchvision.models import resnet18

# 경로 설정 코드 삭제! 그냥 import 하면 됩니다.
from module.hardware import AGVHardware
from module.driving_logic import LineTrackingBrain
from module.mission_manager import MissionManager

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

# 3. 실행
try:
    print("🏁 AGV 출발!")
    manager.set_state("TRACKING")
    
    while True:
        manager.update()
        time.sleep(0.001)

except KeyboardInterrupt:
    agv.stop()
    print("🛑 정지 완료")
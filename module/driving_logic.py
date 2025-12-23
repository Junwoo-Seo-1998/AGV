import torch
import torchvision.transforms as transforms
import PIL.Image
import numpy as np
from jetbot import bgr8_to_jpeg # 디스플레이용

class LineTrackingBrain:
    def __init__(self, model, device):
        self.model = model
        self.device = device
        
        # 제공해주신 전처리 상수
        self.mean = torch.Tensor([0.485, 0.456, 0.406]).to(device).half()
        self.std = torch.Tensor([0.229, 0.224, 0.225]).to(device).half()
        
        # PID 제어용 이전 값 기억
        self.angle = 0.0
        self.angle_last = 0.0

    def preprocess(self, image):
        image = PIL.Image.fromarray(image)
        image = transforms.functional.to_tensor(image).to(self.device).half()
        image.sub_(self.mean[:, None, None]).div_(self.std[:, None, None])
        return image[None, ...]

    def calculate(self, image, context):
        """
        Input: 카메라 이미지, Context(설정값)
        Output: left_motor_value, right_motor_value
        """
        # 1. 모델 추론 (제공 코드 로직)
        xy = self.model(self.preprocess(image)).detach().float().cpu().numpy().flatten()
        x = xy[0]
        y = (0.5 - xy[1]) / 2.0
        
        # Context에 현재 상태 업데이트 (디버깅용)
        context.current_x = x
        context.current_y = y
        context.processed_image = bgr8_to_jpeg(image)

        # 2. 조향각 계산
        self.angle = np.arctan2(x, y)
        
        # 3. PID 제어 계산 (Context에 있는 게인 값 사용)
        pid = (self.angle * context.steering_gain) + \
              ((self.angle - self.angle_last) * context.steering_dgain)
        self.angle_last = self.angle

        steering_output = pid + context.steering_bias
        
        # 4. 모터 출력 계산
        left_motor = max(min(context.speed_gain + steering_output, 1.0), 0.0)
        right_motor = max(min(context.speed_gain - steering_output, 1.0), 0.0)
        
        return left_motor, right_motor
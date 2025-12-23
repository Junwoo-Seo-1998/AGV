class BaseState:
    def process(self, context):
        """
        로직 수행 후 '다음 상태의 이름(String)'을 반환.
        상태를 유지하려면 None 반환.
        """
        raise NotImplementedError
import logging
class CustomLogger(logging.Logger):
    def __init__(self, name, log_file=None):
        super().__init__(name)
        self.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # 콘솔 핸들러 설정
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        self.addHandler(console_handler)

        # 파일 핸들러 설정
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.addHandler(file_handler)
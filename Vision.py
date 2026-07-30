import cv2
import threading
import time


class Vision:
    def __init__(self):
        self.camera = None
        self.running = False
        self.frame = None
        self.capture_thread = None
        self.frame_lock = threading.Lock()

    def start_camera(self):
        if self.running:
            return True

        self.camera = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)

        if not self.camera.isOpened():
            self.camera.release()
            self.camera = None
            return False

        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        return True

    def update_frame(self):
        if not self.running or self.camera is None:
            return

        success, frame = self.camera.read()

        if success:
            self.frame = frame
        return success

    def get_frame(self):
        with self.frame_lock:
            if self.frame is None:
                return None

            return self.frame.copy()

    def stop_camera(self):
        if self.camera is not None:
            self.camera.release()
            self.camera = None

        self.running = False
        if self.capture_thread is not None:
            self.capture_thread.join()

    def is_running(self):
        return self.running

    def _capture_loop(self):
        while self.running:
            success, frame = self.camera.read()

            if success:
                with self.frame_lock:
                    self.frame = frame
            time.sleep(0.001)

    def capture_image(self, filename):
        frame = self.get_frame()

        if frame is None:
            return False

        cv2.imwrite(filename, frame)
        return True

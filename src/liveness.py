from dataclasses import dataclass

import cv2
import numpy as np

from .config import (
    LAPLACIAN_SHARPNESS_THRESHOLD,
    MIN_CLOSED_EYE_FRAMES,
    MIN_OPEN_EYE_FRAMES,
    REQUIRED_BLINKS,
)


@dataclass
class LivenessState:
    live: bool
    spoof_suspected: bool
    message: str
    blink_count: int
    eye_count: int
    sharpness: float


class BlinkLivenessDetector:
    def __init__(self, eye_cascade: cv2.CascadeClassifier):
        self.eye_cascade = eye_cascade
        self.required_blinks = REQUIRED_BLINKS
        self.reset()

    def reset(self) -> None:
        self.state = "await_open"
        self.blink_count = 0
        self.open_eye_frames = 0
        self.closed_eye_frames = 0
        self.last_sharpness = 0.0

    def update(self, face_gray: np.ndarray) -> LivenessState:
        eyes = self.eye_cascade.detectMultiScale(
            face_gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(20, 20),
        )
        eye_count = len(eyes)
        eyes_visible = eye_count >= 1
        sharpness = float(cv2.Laplacian(face_gray, cv2.CV_64F).var())
        self.last_sharpness = sharpness

        if self.state == "await_open":
            if eyes_visible:
                self.open_eye_frames += 1
            else:
                self.open_eye_frames = 0
            if self.open_eye_frames >= MIN_OPEN_EYE_FRAMES:
                self.state = "await_closed"
                self.open_eye_frames = 0

        elif self.state == "await_closed":
            if not eyes_visible:
                self.closed_eye_frames += 1
            else:
                self.closed_eye_frames = 0
            if self.closed_eye_frames >= MIN_CLOSED_EYE_FRAMES:
                self.state = "await_reopen"
                self.open_eye_frames = 0

        elif self.state == "await_reopen":
            if eyes_visible:
                self.open_eye_frames += 1
                if self.open_eye_frames >= MIN_OPEN_EYE_FRAMES:
                    self.blink_count += 1
                    self.state = "await_closed"
                    self.open_eye_frames = 0
                    self.closed_eye_frames = 0
            else:
                self.open_eye_frames = 0

        live = self.blink_count >= self.required_blinks and sharpness >= LAPLACIAN_SHARPNESS_THRESHOLD
        spoof_suspected = self.blink_count < self.required_blinks and sharpness >= LAPLACIAN_SHARPNESS_THRESHOLD

        if live:
            message = "Liveness confirmed. Proceeding with recognition..."
        elif sharpness < LAPLACIAN_SHARPNESS_THRESHOLD:
            message = "Hold still and improve lighting for anti-spoofing."
        else:
            message = f"Blink naturally to confirm liveness ({self.blink_count}/{self.required_blinks})."

        return LivenessState(
            live=live,
            spoof_suspected=spoof_suspected,
            message=message,
            blink_count=self.blink_count,
            eye_count=eye_count,
            sharpness=sharpness,
        )

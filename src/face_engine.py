import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import (
    CAMERA_INDEX,
    CAPTURE_SAMPLES,
    DATASET_DIR,
    FACE_SIZE,
    LIVENESS_TIMEOUT_SECONDS,
    MODEL_PATH,
    RECOGNITION_THRESHOLD,
    staff_id_storage_key,
    WINDOW_NAME_ACCESS,
    WINDOW_NAME_CAPTURE,
)
from .database import DatabaseManager
from .liveness import BlinkLivenessDetector


class FaceRecognitionError(RuntimeError):
    """Raised when the face recognition pipeline cannot continue."""


class FaceEngine:
    def __init__(self, database: DatabaseManager):
        self.database = database
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
        )
        if self.face_cascade.empty():
            raise FaceRecognitionError("Could not load face cascade classifier.")
        if self.eye_cascade.empty():
            raise FaceRecognitionError("Could not load eye cascade classifier.")
        if not hasattr(cv2, "face"):
            raise FaceRecognitionError(
                "OpenCV face module is unavailable. Install opencv-contrib-python."
            )
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.liveness_detector = BlinkLivenessDetector(self.eye_cascade)
        self.model_loaded = False
        if MODEL_PATH.exists():
            self.load_model()

    def _dataset_path_for_staff_id(self, staff_id: str) -> Path:
        return DATASET_DIR / staff_id_storage_key(staff_id)

    def _dataset_image_path(self, staff_id: str, image_number: int) -> Path:
        dataset_path = self._dataset_path_for_staff_id(staff_id)
        safe_staff_id = staff_id_storage_key(staff_id)
        return dataset_path / f"{safe_staff_id}_{image_number:03d}.png"

    def _preprocess_face(self, gray_frame: np.ndarray, face_rect: tuple[int, int, int, int]) -> np.ndarray:
        x, y, w, h = face_rect
        face_roi = gray_frame[y : y + h, x : x + w]
        equalized = cv2.equalizeHist(face_roi)
        resized = cv2.resize(equalized, FACE_SIZE)
        return resized

    def _detect_primary_face(self, gray_frame: np.ndarray) -> tuple[int, int, int, int] | None:
        faces = self.face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(100, 100),
        )
        if len(faces) == 0:
            return None
        return max(faces, key=lambda rect: rect[2] * rect[3])

    def load_model(self) -> None:
        if not MODEL_PATH.exists():
            raise FaceRecognitionError("No trained LBPH model found. Train the model first.")
        self.recognizer.read(str(MODEL_PATH))
        self.model_loaded = True

    def capture_dataset(self, user: dict[str, Any], sample_count: int = CAPTURE_SAMPLES) -> dict[str, Any]:
        camera = cv2.VideoCapture(CAMERA_INDEX)
        if not camera.isOpened():
            raise FaceRecognitionError("Camera could not be opened for dataset capture.")

        dataset_path = self._dataset_path_for_staff_id(user["staff_id"])
        dataset_path.mkdir(parents=True, exist_ok=True)

        captured = 0
        frame_skip = 0

        try:
            while captured < sample_count:
                ok, frame = camera.read()
                if not ok:
                    continue

                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                face_rect = self._detect_primary_face(gray)

                if face_rect is not None:
                    x, y, w, h = face_rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (40, 180, 40), 2)
                    frame_skip += 1
                    if frame_skip % 3 == 0:
                        processed_face = self._preprocess_face(gray, face_rect)
                        image_path = self._dataset_image_path(user["staff_id"], captured + 1)
                        saved = cv2.imwrite(str(image_path), processed_face)
                        if not saved:
                            raise FaceRecognitionError(
                                f"Failed to save dataset image to {image_path}."
                            )
                        captured += 1

                cv2.putText(
                    frame,
                    f"Capturing face samples for {user['full_name']}: {captured}/{sample_count}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (30, 255, 30),
                    2,
                )
                cv2.putText(
                    frame,
                    "Look straight at the camera. Press Q to cancel.",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 220, 255),
                    2,
                )
                cv2.imshow(WINDOW_NAME_CAPTURE, frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
        finally:
            camera.release()
            cv2.destroyAllWindows()

        self.database.update_face_samples(user["id"], captured)
        return {
            "captured": captured,
            "dataset_path": str(dataset_path),
        }

    def train_model(self) -> dict[str, Any]:
        faces: list[np.ndarray] = []
        labels: list[int] = []
        users_trained: set[int] = set()

        for user in self.database.list_users():
            dataset_path = self._dataset_path_for_staff_id(user["staff_id"])
            if not dataset_path.exists():
                continue

            for image_path in sorted(dataset_path.glob("*.png")):
                image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
                if image is None:
                    continue
                faces.append(cv2.resize(image, FACE_SIZE))
                labels.append(int(user["id"]))
                users_trained.add(int(user["id"]))

        if not faces:
            raise FaceRecognitionError("No dataset images found. Capture faces before training.")

        self.recognizer.train(faces, np.array(labels))
        self.recognizer.write(str(MODEL_PATH))
        self.model_loaded = True

        return {
            "images_used": len(faces),
            "users_trained": len(users_trained),
            "model_path": str(MODEL_PATH),
        }

    def _confidence_score(self, lbph_distance: float) -> float:
        score = max(0.0, min(100.0, 100.0 - lbph_distance))
        return round(score, 2)

    def recognize_with_liveness(
        self,
        access_point: str = "Face Recognition Gate",
        persist_log: bool = True,
    ) -> dict[str, Any]:
        if not self.model_loaded:
            self.load_model()

        camera = cv2.VideoCapture(CAMERA_INDEX)
        if not camera.isOpened():
            raise FaceRecognitionError("Camera could not be opened for face access.")

        start_time = time.time()
        self.liveness_detector.reset()
        result: dict[str, Any] = {
            "status": "DENIED",
            "name": "Unknown",
            "staff_id": None,
            "confidence": 0.0,
            "distance": None,
            "message": "Face not recognized.",
            "spoof_detected": False,
            "user_id": None,
        }

        try:
            while True:
                ok, frame = camera.read()
                if not ok:
                    continue

                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                face_rect = self._detect_primary_face(gray)

                if face_rect is not None:
                    x, y, w, h = face_rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 220, 50), 2)
                    face_image = self._preprocess_face(gray, face_rect)
                    liveness_state = self.liveness_detector.update(face_image)

                    cv2.putText(
                        frame,
                        liveness_state.message,
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 220, 255),
                        2,
                    )
                    cv2.putText(
                        frame,
                        f"Blinks: {liveness_state.blink_count}/{self.liveness_detector.required_blinks}  "
                        f"Eyes: {liveness_state.eye_count}  Sharpness: {liveness_state.sharpness:.1f}",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (255, 255, 255),
                        2,
                    )

                    if liveness_state.live:
                        predicted_label, lbph_distance = self.recognizer.predict(face_image)
                        confidence = self._confidence_score(lbph_distance)
                        user = self.database.get_user_by_id(int(predicted_label))

                        if user and lbph_distance <= RECOGNITION_THRESHOLD:
                            result = {
                                "status": "GRANTED",
                                "name": user["full_name"],
                                "staff_id": user["staff_id"],
                                "confidence": confidence,
                                "distance": round(float(lbph_distance), 2),
                                "message": f"Access granted to {user['full_name']}.",
                                "spoof_detected": False,
                                "user_id": user["id"],
                            }
                        else:
                            result = {
                                "status": "DENIED",
                                "name": "Unknown",
                                "staff_id": None,
                                "confidence": confidence,
                                "distance": round(float(lbph_distance), 2),
                                "message": "Face not enrolled or confidence below threshold.",
                                "spoof_detected": False,
                                "user_id": None,
                            }
                        break

                if time.time() - start_time > LIVENESS_TIMEOUT_SECONDS:
                    result = {
                        "status": "DENIED",
                        "name": "Unknown",
                        "staff_id": None,
                        "confidence": 0.0,
                        "distance": None,
                        "message": "Anti-spoofing check failed. No live blink detected in time.",
                        "spoof_detected": True,
                        "user_id": None,
                    }
                    break

                cv2.imshow(WINDOW_NAME_ACCESS, frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    result["message"] = "Face recognition cancelled by operator."
                    break
        finally:
            camera.release()
            cv2.destroyAllWindows()

        if persist_log:
            self.database.log_access(
                user_id=result.get("user_id"),
                access_point=access_point,
                method="FACE_LBPH",
                status=result["status"],
                confidence=result.get("confidence"),
                spoof_detected=bool(result.get("spoof_detected")),
                message=result["message"],
            )
        return result

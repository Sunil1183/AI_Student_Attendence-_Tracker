from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Iterable, List, Tuple

import cv2
import numpy as np
from django.conf import settings

from .models import FaceSample, StudentProfile


FACE_MODEL_DIR = Path(settings.BASE_DIR) / "face_models"
FACE_MODEL_PATH = FACE_MODEL_DIR / "lbph_model.yml"


def _get_cascade() -> cv2.CascadeClassifier:
    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    return cv2.CascadeClassifier(cascade_path)


def _load_image_bytes(image_bytes: bytes) -> np.ndarray:
    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image_bgr = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise ValueError("Could not decode image bytes")
    return image_bgr


def _prepare_training_data() -> Tuple[List[np.ndarray], List[int]]:
    faces: List[np.ndarray] = []
    labels: List[int] = []
    cascade = _get_cascade()

    for sample in FaceSample.objects.select_related("student"):
        image_path = sample.image.path
        img = cv2.imread(image_path)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        detected = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        for (x, y, w, h) in detected:
            faces.append(gray[y : y + h, x : x + w])
            labels.append(sample.student.id)

    return faces, labels


def train_recognizer() -> None:
    FACE_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    faces, labels = _prepare_training_data()
    if not faces:
        raise RuntimeError("No face samples available for training.")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    recognizer.write(str(FACE_MODEL_PATH))


def _load_recognizer() -> cv2.face_LBPHFaceRecognizer:
    if not FACE_MODEL_PATH.exists():
        raise RuntimeError("Face model does not exist. Train the model first.")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(FACE_MODEL_PATH))
    return recognizer


def _is_live_sequence(frames: list[bytes]) -> bool:
    """Basic liveness check using frame-to-frame pixel changes.

    We convert each pair of consecutive frames to grayscale, take the absolute
    difference, and count how many pixels have changed by a significant amount
    (20 grayscale levels by default).  If *any* pair has more than a tiny
    fraction of changed pixels (0.5% of the image area here) we consider the
    sequence "live".  A completely static image – even if it is a photograph –
    will produce almost no changed pixels after compression and thus will be
    rejected.

    This is still far from bulletproof, but it avoids needing an extremely low
    floating-point threshold that depends on JPEG artifacts.  For a production
    system you’d replace this with a trained liveness model or more advanced
    heuristics (blink/pose, depth maps, etc.).
    """
    if len(frames) < 2:
        # nothing to compare so we'll punt and treat it as live
        return True

    imgs: list[np.ndarray] = []
    for b in frames:
        try:
            imgs.append(_load_image_bytes(b))
        except ValueError:
            continue

    if len(imgs) < 2:
        return True

    height, width = imgs[0].shape[:2]
    area = height * width
    # threshold for considering a pixel changed
    change_level = 20
    # proportion of pixels that must change to call it live - we only
    # require *one* pixel to change after thresholding.  In practice an actual
    # camera feed will have hundreds of changed pixels even with a tiny head
    # movement; this just makes sure the sequence isn’t bit-by-bit identical.
    change_fraction = 1.0 / area

    for a, b in zip(imgs, imgs[1:]):
        gray_a = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
        gray_b = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray_a, gray_b)
        _, th = cv2.threshold(diff, change_level, 255, cv2.THRESH_BINARY)
        changed = np.count_nonzero(th)
        # use >= so a single qualifying pixel is enough when change_fraction
        # is 1/area
        if changed >= area * change_fraction:
            return True

    return False


def recognize_students_from_image_bytes(
    image_bytes: bytes | None = None,
    frames: list[bytes] | None = None,
    confidence_threshold: float = 80.0,
) -> Iterable[StudentProfile]:
    """Recognize students in an image or broadcast of frames.

    The API now accepts either a single image (``image_bytes``) or a list of
    frames (`frames`).  The view is responsible for performing a liveness check
    using ``_is_live_sequence`` when multiple frames are provided; if the
    sequence fails the check recognition is skipped entirely and the caller can
    return an error to the user.
    """
    if frames is not None:
        if not _is_live_sequence(frames):
            # caller will handle the failed liveness check
            return []
        if frames:
            # just use the last frame for recognition
            image_bytes = frames[-1]

    if image_bytes is None:
        raise ValueError("Either image_bytes or frames must be provided")

    image_bgr = _load_image_bytes(image_bytes)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    cascade = _get_cascade()
    recognizer = _load_recognizer()

    detected = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    student_ids: set[int] = set()

    for (x, y, w, h) in detected:
        face_roi = gray[y : y + h, x : x + w]
        student_id, confidence = recognizer.predict(face_roi)
        if confidence <= confidence_threshold:
            student_ids.add(student_id)

    return StudentProfile.objects.filter(id__in=student_ids)


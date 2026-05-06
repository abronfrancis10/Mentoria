from __future__ import annotations

import math
import os
import queue
import threading
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

from app.services.question_generation_service import generate_question

logger = logging.getLogger(__name__)


running = True
audio_queue: "queue.Queue[Any]" = queue.Queue(maxsize=16)
text_queue: "queue.Queue[str]" = queue.Queue(maxsize=32)
_whisper_model: Any = None
_whisper_model_lock = threading.Lock()


def _load_whisper_model_once(model_name: str = "base") -> Any:
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    with _whisper_model_lock:
        if _whisper_model is None:
            import whisper  # type: ignore

            _whisper_model = whisper.load_model(model_name)
    return _whisper_model


def _safe_import_cv2_np() -> tuple[Any | None, Any | None]:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        return cv2, np
    except Exception:
        return None, None


def _default_model_path(env_var: str, fallback_filename: str) -> str:
    configured = os.getenv(env_var, "").strip()
    if configured and Path(configured).is_file():
        return str(Path(configured).resolve())

    # Default to repository-local model assets when env vars are not provided.
    local_default = Path(__file__).resolve().parents[1] / "models" / fallback_filename
    if local_default.is_file():
        return str(local_default)
    return configured


@dataclass
class MonitorConfig:
    warning_time: float = 3.0
    count_time: float = 5.0
    calibration_time: float = 3.0
    head_tilt_threshold: float = 12.0
    emotion_delay: float = 3.0
    face_landmarker_model_path: str = field(
        default_factory=lambda: _default_model_path(
            "MEDIAPIPE_FACE_LANDMARKER_MODEL", "face_landmarker.task"
        )
    )
    pose_landmarker_model_path: str = field(
        default_factory=lambda: _default_model_path(
            "MEDIAPIPE_POSE_LANDMARKER_MODEL", "pose_landmarker_lite.task"
        )
    )


class AIInterviewMonitor:
    def __init__(self, config: MonitorConfig | None = None) -> None:
        self.config = config or MonitorConfig()
        self._states: dict[str, dict[str, Any]] = {}
        self._face_mesh = None
        self._pose = None
        self._deepface = None
        self._haar = None
        self._mediapipe_mode = ""

    def _state(self, interview_id: str) -> dict[str, Any]:
        now = time.time()
        if interview_id not in self._states:
            self._states[interview_id] = {
                "score": 100,
                "slouch_count": 0,
                "tilt_count": 0,
                "eye_contact_count": 0,
                "multi_face_count": 0,
                "face_not_clear_count": 0,
                "emotion_stats": {
                    "happy": 0,
                    "neutral": 0,
                    "sad": 0,
                    "angry": 0,
                    "surprise": 0,
                    "fear": 0,
                    "disgust": 0,
                },
                "slouch_start": None,
                "tilt_start": None,
                "eye_away_start": None,
                "multi_face_start": None,
                "face_not_clear_start": None,
                "slouch_counted": False,
                "tilt_counted": False,
                "eye_counted": False,
                "multi_face_counted": False,
                "face_not_clear_counted": False,
                "last_emotion_time": 0.0,
                "emotion_text": "unknown",
                "neutral_streak": 0,
                "baseline_neck": None,
                "calibration_start": now,
                "total_frames": 0,
                "clear_face_frames": 0,
                "attention_drop_instances": 0,
                "attention_in_drop": False,
            }
        return self._states[interview_id]

    @staticmethod
    def _point(landmarks: list[Any], idx: int, w: int, h: int) -> tuple[int, int]:
        return int(landmarks[idx].x * w), int(landmarks[idx].y * h)

    @staticmethod
    def _head_tilt(left_eye: tuple[int, int], right_eye: tuple[int, int]) -> float:
        dx = right_eye[0] - left_eye[0]
        dy = right_eye[1] - left_eye[1]
        return math.degrees(math.atan2(dy, dx))

    @staticmethod
    def _blendshape_scores(blendshape_categories: Any) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for category in blendshape_categories or []:
            name = str(
                getattr(category, "category_name", "")
                or getattr(category, "display_name", "")
            ).strip()
            if not name:
                continue
            score = float(getattr(category, "score", 0.0) or 0.0)
            if score > scores.get(name, 0.0):
                scores[name] = score
        return scores

    @staticmethod
    def _best_score(scores: Dict[str, float], *names: str) -> float:
        return max((float(scores.get(name, 0.0)) for name in names), default=0.0)

    @staticmethod
    def _emotion_from_blendshapes(scores: Dict[str, float]) -> str:
        smile = AIInterviewMonitor._best_score(
            scores, "mouthSmileLeft", "mouthSmileRight"
        )
        frown = AIInterviewMonitor._best_score(
            scores, "mouthFrownLeft", "mouthFrownRight"
        )
        eye_wide = AIInterviewMonitor._best_score(scores, "eyeWideLeft", "eyeWideRight")
        jaw_open = AIInterviewMonitor._best_score(scores, "jawOpen", "mouthOpen")
        brow_down = AIInterviewMonitor._best_score(
            scores, "browDownLeft", "browDownRight"
        )
        brow_inner_up = AIInterviewMonitor._best_score(scores, "browInnerUp")
        nose_sneer = AIInterviewMonitor._best_score(
            scores, "noseSneerLeft", "noseSneerRight"
        )

        if smile >= 0.38 and frown < 0.3:
            return "happy"
        if eye_wide >= 0.35 and jaw_open >= 0.22:
            return "surprise"
        if brow_down >= 0.32 and frown >= 0.2:
            return "angry"
        if eye_wide >= 0.32 and brow_inner_up >= 0.28 and jaw_open >= 0.12:
            return "fear"
        if nose_sneer >= 0.28:
            return "disgust"
        if frown >= 0.3 and smile < 0.22:
            return "sad"
        return "neutral"

    @staticmethod
    def _gaze_ratio(
        landmarks: list[Any],
        left_idx: int,
        right_idx: int,
        iris_idx: int,
        w: int,
        h: int,
    ) -> float:
        left = AIInterviewMonitor._point(landmarks, left_idx, w, h)
        right = AIInterviewMonitor._point(landmarks, right_idx, w, h)
        iris = AIInterviewMonitor._point(landmarks, iris_idx, w, h)
        width = right[0] - left[0]
        if width == 0:
            return 0.5
        return (iris[0] - left[0]) / width

    def _append_emotion_warning(
        self, emotion_text: str, state: dict[str, Any], warnings: list[str]
    ) -> None:
        emotion = (emotion_text or "").lower().strip()
        if emotion == "neutral":
            state["neutral_streak"] = int(state.get("neutral_streak", 0)) + 1
        else:
            state["neutral_streak"] = 0

        if emotion in {"angry", "fear", "disgust"}:
            warnings.append("Maintain a calm, confident expression")
        elif emotion == "sad":
            warnings.append("Try to keep a more positive expression")
        elif emotion == "surprise":
            warnings.append("Keep your expression steady and composed")

    def _ensure_deepface(self) -> tuple[bool, str]:
        if self._deepface is not None:
            return True, ""
        try:
            from deepface import DeepFace  # type: ignore

            self._deepface = DeepFace
            return True, ""
        except Exception as exc:
            return False, str(exc)[:300]

    def _ensure_mediapipe_models(self) -> tuple[bool, str]:
        if self._face_mesh is not None and self._pose is not None:
            return True, ""
        try:
            import mediapipe as mp  # type: ignore

            # Prefer MediaPipe Tasks (modern) over Solutions (legacy) for blendshapes support
            use_tasks = False
            if (
                self.config.face_landmarker_model_path
                and Path(self.config.face_landmarker_model_path).is_file()
                and self.config.pose_landmarker_model_path
                and Path(self.config.pose_landmarker_model_path).is_file()
            ):
                try:
                    from mediapipe.tasks.python import vision  # type: ignore
                    from mediapipe.tasks.python.core.base_options import BaseOptions  # type: ignore
                    use_tasks = True
                except ImportError:
                    use_tasks = False

            if use_tasks:
                try:
                    from mediapipe.tasks.python import vision
                    from mediapipe.tasks.python.core.base_options import BaseOptions
                    
                    face_options = vision.FaceLandmarkerOptions(
                        base_options=BaseOptions(
                            model_asset_path=self.config.face_landmarker_model_path
                        ),
                        running_mode=vision.RunningMode.IMAGE,
                        num_faces=3,
                        output_face_blendshapes=True,
                        output_facial_transformation_matrixes=False,
                    )
                    pose_options = vision.PoseLandmarkerOptions(
                        base_options=BaseOptions(
                            model_asset_path=self.config.pose_landmarker_model_path
                        ),
                        running_mode=vision.RunningMode.IMAGE,
                        output_segmentation_masks=False,
                    )

                    self._face_mesh = vision.FaceLandmarker.create_from_options(face_options)
                    self._pose = vision.PoseLandmarker.create_from_options(pose_options)
                    self._mediapipe_mode = "tasks"
                    return True, ""
                except Exception as task_exc:
                    logger.warning(f"MediaPipe Tasks failed, falling back to Solutions: {task_exc}")

            if hasattr(mp, "solutions"):
                self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                    refine_landmarks=True,
                    max_num_faces=3,
                )
                self._pose = mp.solutions.pose.Pose(
                    model_complexity=1,
                    smooth_landmarks=True,
                )
                self._mediapipe_mode = "solutions"
                return True, ""

            return (
                False,
                "MediaPipe components unavailable."
            )
        except Exception as exc:
            return False, str(exc)[:300]

    @staticmethod
    def _track_condition(
        state: Dict[str, Any],
        now: float,
        active: bool,
        start_key: str,
        counted_key: str,
        count_key: str,
        count_time: float,
    ) -> None:
        if active:
            if state[start_key] is None:
                state[start_key] = now
            duration = now - float(state[start_key])
            if duration >= count_time and not bool(state[counted_key]):
                state[count_key] += 1
                state[counted_key] = True
        else:
            state[start_key] = None
            state[counted_key] = False

    def _fallback_face_warnings(
        self, frame: Any, warnings: list[str]
    ) -> tuple[int, Dict[str, bool]]:
        cv2, _ = _safe_import_cv2_np()
        flags = {
            "slouch": False,
            "tilt": False,
            "eye_away": False,
            "multi_face": False,
            "face_not_clear": False,
        }
        if cv2 is None:
            return 0, flags

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self._haar is None:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._haar = cv2.CascadeClassifier(cascade_path)

        faces = self._haar.detectMultiScale(
            gray, scaleFactor=1.15, minNeighbors=4, minSize=(60, 60)
        )
        face_count = int(len(faces))
        if face_count == 0:
            warnings.append("Face not clear")
            flags["face_not_clear"] = True
        elif face_count > 1:
            warnings.append("Multiple persons detected")
            flags["multi_face"] = True

        if face_count > 0:
            _, y, _, h_box = faces[0]
            center_y = y + (h_box / 2.0)
            if center_y > frame.shape[0] * 0.62:
                warnings.append("Sit straight, don't slouch")
                flags["slouch"] = True
        return face_count, flags

    def _update_score(self, state: Dict[str, Any]) -> int:
        score = 100
        score -= int(state["slouch_count"]) * 5
        score -= int(state["tilt_count"]) * 4
        score -= int(state["eye_contact_count"]) * 5
        score -= int(state["multi_face_count"]) * 6
        score -= int(state["face_not_clear_count"]) * 6
        state["score"] = max(score, 0)
        if state["score"] < 70 and not bool(state.get("attention_in_drop")):
            state["attention_drop_instances"] = (
                int(state.get("attention_drop_instances", 0)) + 1
            )
            state["attention_in_drop"] = True
        elif state["score"] >= 70:
            state["attention_in_drop"] = False
        return int(state["score"])

    @staticmethod
    def _attention_feedback(score: int, counts: Dict[str, int]) -> Dict[str, Any]:
        if score >= 85:
            headline = "Strong on-camera presence overall."
        elif score >= 70:
            headline = "Good focus, with a few attention issues to improve."
        elif score >= 50:
            headline = "Attention consistency needs improvement."
        else:
            headline = "Frequent attention issues reduced interview presence."

        details = []
        if counts.get("slouch_count", 0) > 0:
            details.append("Maintain upright posture consistently during answers.")
        if counts.get("tilt_count", 0) > 0:
            details.append("Keep your head aligned with the camera.")
        if counts.get("eye_contact_count", 0) > 0:
            details.append("Improve eye contact to appear more confident.")
        if counts.get("face_not_clear_count", 0) > 0:
            details.append("Ensure your face stays well-framed and clearly visible.")
        if counts.get("multi_face_count", 0) > 0:
            details.append("Avoid background movement or other faces in frame.")
        if not details:
            details.append("No major attention issues detected.")

        return {"headline": headline, "details": details}

    @staticmethod
    def _emotion_feedback(emotion_stats: Dict[str, int]) -> Dict[str, Any]:
        total = sum(int(v) for v in emotion_stats.values())
        if total <= 0:
            return {
                "distribution": {},
                "headline": "No emotion samples available yet.",
                "details": ["Keep camera framing steady to improve analysis quality."],
            }

        distribution = {
            emotion: round((count / total) * 100.0, 1)
            for emotion, count in emotion_stats.items()
            if count > 0
        }
        positive = distribution.get("happy", 0.0) + distribution.get("neutral", 0.0)
        if positive >= 75:
            headline = "Expression remained professional and interview-appropriate."
        elif positive >= 55:
            headline = (
                "Expression was generally stable, with occasional negative signals."
            )
        else:
            headline = "Expression patterns suggest elevated stress or low engagement."

        details = []
        if distribution.get("sad", 0.0) > 20.0:
            details.append("Try adding more energy and vocal variety while speaking.")
        if (
            distribution.get("angry", 0.0) > 10.0
            or distribution.get("fear", 0.0) > 10.0
        ):
            details.append(
                "Practice slow breathing before answers to reduce tension cues."
            )
        if distribution.get("neutral", 0.0) > 80.0:
            details.append("A slight smile at key moments can improve engagement.")
        if not details:
            details.append("Emotion signals stayed within a healthy interview range.")

        return {
            "distribution": distribution,
            "headline": headline,
            "details": details,
        }

    def get_report(self, interview_id: str) -> Dict[str, Any]:
        state = self._state(interview_id)
        score = self._update_score(state)
        issue_counts = {
            "slouch_count": int(state["slouch_count"]),
            "tilt_count": int(state["tilt_count"]),
            "eye_contact_count": int(state["eye_contact_count"]),
            "multi_face_count": int(state["multi_face_count"]),
            "face_not_clear_count": int(state["face_not_clear_count"]),
        }
        emotion_stats = dict(state.get("emotion_stats", {}))
        total_emotions = sum(int(v) for v in emotion_stats.values())
        positive_emotions = int(emotion_stats.get("happy", 0)) + int(
            emotion_stats.get("neutral", 0)
        )
        emotion_score_percent = (
            round((positive_emotions / total_emotions) * 100.0, 2)
            if total_emotions > 0
            else 0.0
        )
        emotion_distribution = {
            emotion: round((int(count) / total_emotions) * 100.0, 2)
            for emotion, count in emotion_stats.items()
            if total_emotions > 0 and int(count) > 0
        }
        dominant_emotion = "unknown"
        if total_emotions > 0:
            dominant_emotion = max(
                emotion_stats, key=lambda key: int(emotion_stats.get(key, 0))
            )
        total_frames = int(state.get("total_frames", 0))
        clear_face_frames = int(state.get("clear_face_frames", 0))
        average_face_visibility_score = (
            round((clear_face_frames / total_frames) * 100.0, 2)
            if total_frames > 0
            else 0.0
        )

        return {
            "final_attention_score": score,
            "emotion_score_percent": emotion_score_percent,
            "issue_counts": issue_counts,
            "attention_feedback": self._attention_feedback(score, issue_counts),
            "emotion_feedback": self._emotion_feedback(emotion_stats),
            "emotion_distribution": emotion_distribution,
            "dominant_emotion": dominant_emotion,
            "attention_drop_instances": int(state.get("attention_drop_instances", 0)),
            "average_face_visibility_score": average_face_visibility_score,
        }

    def analyze_frame_bytes(
        self, frame_bytes: bytes, interview_id: str, sample_emotion: bool = True
    ) -> dict[str, Any]:
        cv2, np = _safe_import_cv2_np()
        if cv2 is None or np is None:
            return {
                "emotion_label": "unknown",
                "emotion_score": 6.0,
                "face_count": 0,
                "head_tilt_angle": 0.0,
                "warnings": [],
                "vision_available": False,
                "deepface_available": False,
                "mediapipe_available": False,
                "deepface_error": "opencv unavailable",
                "mediapipe_error": "opencv unavailable",
            }

        np_frame = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(np_frame, cv2.IMREAD_COLOR)
        if frame is None:
            return {
                "emotion_label": "unknown",
                "emotion_score": 6.0,
                "face_count": 0,
                "head_tilt_angle": 0.0,
                "warnings": ["Invalid frame"],
                "vision_available": False,
                "deepface_available": False,
                "mediapipe_available": False,
                "deepface_error": "",
                "mediapipe_error": "",
            }

        now = time.time()
        state = self._state(interview_id)
        warnings: list[str] = []
        head_tilt_angle = 0.0
        face_count = 0
        flags = {
            "slouch": False,
            "tilt": False,
            "eye_away": False,
            "multi_face": False,
            "face_not_clear": False,
        }

        deepface_available, deepface_error = self._ensure_deepface()
        mediapipe_available, mediapipe_error = self._ensure_mediapipe_models()

        emotion_text = state.get("emotion_text", "unknown")
        emotion_source = "state_cache"
        should_sample_emotion = sample_emotion and (
            now - float(state["last_emotion_time"]) > self.config.emotion_delay
        )
        emotion_sampled = False
        # Prefer MediaPipe for live analysis; use DeepFace only when MediaPipe is unavailable.
        if deepface_available and should_sample_emotion and not mediapipe_available:
            try:
                result = self._deepface.analyze(
                    frame,
                    actions=["emotion"],
                    enforce_detection=False,
                    detector_backend="opencv",
                    silent=True,
                )
                emotion_text = (
                    result[0]["dominant_emotion"]
                    if isinstance(result, list)
                    else result["dominant_emotion"]
                )
                if emotion_text in state["emotion_stats"]:
                    state["emotion_stats"][emotion_text] += 1
                state["emotion_text"] = emotion_text
                state["last_emotion_time"] = now
                emotion_source = "deepface"
                emotion_sampled = True
            except Exception as exc:
                deepface_available = False
                deepface_error = str(exc)[:300]

        if mediapipe_available:
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = frame.shape[:2]

                if self._mediapipe_mode == "tasks":
                    import mediapipe as mp  # type: ignore

                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    face_result = self._face_mesh.detect(mp_image)
                    pose_result = self._pose.detect(mp_image)

                    face_landmarks_list = face_result.face_landmarks or []
                    if not face_landmarks_list:
                        warnings.append("Face not clear")
                        flags["face_not_clear"] = True
                    else:
                        face_count = len(face_landmarks_list)
                        if face_count > 1:
                            warnings.append("Multiple persons detected")
                            flags["multi_face"] = True

                        landmarks = face_landmarks_list[0]
                        if should_sample_emotion:
                            blendshape_lists = face_result.face_blendshapes or []
                            if blendshape_lists:
                                shape_scores = self._blendshape_scores(
                                    blendshape_lists[0]
                                )
                                mp_emotion = self._emotion_from_blendshapes(
                                    shape_scores
                                )
                                if mp_emotion in state["emotion_stats"]:
                                    state["emotion_stats"][mp_emotion] += 1
                                state["emotion_text"] = mp_emotion
                                state["last_emotion_time"] = now
                                emotion_text = mp_emotion
                                emotion_source = "mediapipe_blendshape"
                                emotion_sampled = True

                        left_eye = self._point(landmarks, 33, w, h)
                        right_eye = self._point(landmarks, 263, w, h)
                        head_tilt_angle = self._head_tilt(left_eye, right_eye)
                        if abs(head_tilt_angle) > self.config.head_tilt_threshold:
                            warnings.append("Keep head straight")
                            flags["tilt"] = True

                        if len(landmarks) > 473:
                            lg = self._gaze_ratio(landmarks, 33, 133, 468, w, h)
                            rg = self._gaze_ratio(landmarks, 362, 263, 473, w, h)
                            gaze = (lg + rg) / 2.0
                            if gaze < 0.35 or gaze > 0.65:
                                warnings.append("Maintain eye contact")
                                flags["eye_away"] = True

                        pose_landmarks_list = pose_result.pose_landmarks or []
                        if pose_landmarks_list:
                            pl = pose_landmarks_list[0]
                            ls = self._point(pl, 11, w, h)
                            rs = self._point(pl, 12, w, h)
                            le = self._point(pl, 7, w, h)
                            re = self._point(pl, 8, w, h)
                            shoulder_y = (ls[1] + rs[1]) // 2
                            ear_y = (le[1] + re[1]) // 2
                            neck = ear_y - shoulder_y

                            if state["baseline_neck"] is None:
                                if (
                                    now - float(state["calibration_start"])
                                    >= self.config.calibration_time
                                ):
                                    state["baseline_neck"] = neck
                            elif neck > float(state["baseline_neck"]) + 15:
                                warnings.append("Sit straight, don't slouch")
                                flags["slouch"] = True
                else:
                    mesh_results = self._face_mesh.process(rgb)
                    pose_results = self._pose.process(rgb)

                    if not mesh_results.multi_face_landmarks:
                        warnings.append("Face not clear")
                        flags["face_not_clear"] = True
                    else:
                        face_count = len(mesh_results.multi_face_landmarks)
                        if face_count > 1:
                            warnings.append("Multiple persons detected")
                            flags["multi_face"] = True

                        landmarks = mesh_results.multi_face_landmarks[0].landmark
                        left_eye = self._point(landmarks, 33, w, h)
                        right_eye = self._point(landmarks, 263, w, h)
                        head_tilt_angle = self._head_tilt(left_eye, right_eye)
                        if abs(head_tilt_angle) > self.config.head_tilt_threshold:
                            warnings.append("Keep head straight")
                            flags["tilt"] = True

                        lg = self._gaze_ratio(landmarks, 33, 133, 468, w, h)
                        rg = self._gaze_ratio(landmarks, 362, 263, 473, w, h)
                        gaze = (lg + rg) / 2.0
                        if gaze < 0.35 or gaze > 0.65:
                            warnings.append("Maintain eye contact")
                            flags["eye_away"] = True

                        if pose_results.pose_landmarks:
                            pl = pose_results.pose_landmarks.landmark
                            ls = self._point(pl, 11, w, h)
                            rs = self._point(pl, 12, w, h)
                            le = self._point(pl, 7, w, h)
                            re = self._point(pl, 8, w, h)
                            shoulder_y = (ls[1] + rs[1]) // 2
                            ear_y = (le[1] + re[1]) // 2
                            neck = ear_y - shoulder_y

                            if state["baseline_neck"] is None:
                                if (
                                    now - float(state["calibration_start"])
                                    >= self.config.calibration_time
                                ):
                                    state["baseline_neck"] = neck
                            elif neck > float(state["baseline_neck"]) + 15:
                                warnings.append("Sit straight, don't slouch")
                                flags["slouch"] = True
            except Exception as exc:
                mediapipe_available = False
                mediapipe_error = str(exc)[:300]
                face_count, fallback_flags = self._fallback_face_warnings(
                    frame, warnings
                )
                for key, value in fallback_flags.items():
                    flags[key] = flags[key] or value
        else:
            face_count, fallback_flags = self._fallback_face_warnings(frame, warnings)
            for key, value in fallback_flags.items():
                flags[key] = flags[key] or value

        if (
            should_sample_emotion
            and not emotion_sampled
            and deepface_available
            and face_count > 0
        ):
            try:
                result = self._deepface.analyze(
                    frame,
                    actions=["emotion"],
                    enforce_detection=False,
                    detector_backend="opencv",
                    silent=True,
                )
                emotion_text = (
                    result[0]["dominant_emotion"]
                    if isinstance(result, list)
                    else result["dominant_emotion"]
                )
                if emotion_text in state["emotion_stats"]:
                    state["emotion_stats"][emotion_text] += 1
                state["emotion_text"] = emotion_text
                state["last_emotion_time"] = now
                emotion_source = "deepface_fallback"
                emotion_sampled = True
            except Exception as exc:
                deepface_available = False
                deepface_error = str(exc)[:300]

        if should_sample_emotion and emotion_text in {"", "unknown"} and face_count > 0:
            state["emotion_stats"]["neutral"] += 1
            state["emotion_text"] = "neutral"
            state["last_emotion_time"] = now
            emotion_text = "neutral"
            emotion_source = "face_fallback"

        emotion_score = 6.0
        if emotion_text in {"happy", "neutral"}:
            emotion_score = 9.0
        elif emotion_text == "surprise":
            emotion_score = 7.0
        elif emotion_text in {"sad", "angry", "fear", "disgust"}:
            emotion_score = 3.0

        self._append_emotion_warning(emotion_text, state, warnings)

        self._track_condition(
            state,
            now,
            flags["slouch"],
            "slouch_start",
            "slouch_counted",
            "slouch_count",
            self.config.count_time,
        )
        self._track_condition(
            state,
            now,
            flags["tilt"],
            "tilt_start",
            "tilt_counted",
            "tilt_count",
            self.config.count_time,
        )
        self._track_condition(
            state,
            now,
            flags["eye_away"],
            "eye_away_start",
            "eye_counted",
            "eye_contact_count",
            self.config.count_time,
        )
        self._track_condition(
            state,
            now,
            flags["multi_face"],
            "multi_face_start",
            "multi_face_counted",
            "multi_face_count",
            self.config.count_time,
        )
        self._track_condition(
            state,
            now,
            flags["face_not_clear"],
            "face_not_clear_start",
            "face_not_clear_counted",
            "face_not_clear_count",
            self.config.count_time,
        )

        state["total_frames"] = int(state.get("total_frames", 0)) + 1
        if not flags["face_not_clear"]:
            state["clear_face_frames"] = int(state.get("clear_face_frames", 0)) + 1

        score = self._update_score(state)
        return {
            "emotion_label": emotion_text or "unknown",
            "emotion_score": round(float(emotion_score), 2),
            "face_count": int(face_count),
            "head_tilt_angle": round(float(head_tilt_angle), 2),
            "warnings": list(dict.fromkeys(warnings)),
            "monitor_counts": {
                "score": score,
                "slouch_count": int(state["slouch_count"]),
                "tilt_count": int(state["tilt_count"]),
                "eye_contact_count": int(state["eye_contact_count"]),
                "multi_face_count": int(state["multi_face_count"]),
                "face_not_clear_count": int(state["face_not_clear_count"]),
            },
            "vision_available": bool(deepface_available or mediapipe_available),
            "deepface_available": bool(deepface_available),
            "mediapipe_available": bool(mediapipe_available),
            "deepface_error": deepface_error,
            "mediapipe_error": mediapipe_error,
            "emotion_source": emotion_source,
        }


@dataclass
class LiveInterviewConfig:
    camera_index: int = 0
    interview_id: str = "live-interview"
    audio_sample_rate: int = 16000
    audio_chunk_seconds: float = 3.0
    whisper_model_name: str = "base"
    language: str = "en"
    deepface_every_n_frames: int = 5
    window_title: str = "Mentoria Live Interview"
    prefetch_questions: int = 1


class LiveInterviewRuntime:
    def __init__(
        self,
        role: str,
        difficulty: str,
        resume_text: str,
        config: LiveInterviewConfig | None = None,
    ) -> None:
        self.monitor = monitor
        self.config = config or LiveInterviewConfig()
        self.role = role
        self.difficulty = difficulty
        self.resume_text = resume_text
        self.current_question = ""
        self.latest_transcript = ""
        self._analysis_cache: Dict[str, Any] = {}
        self._audio_error = ""
        self._transcription_error = ""
        self._mic_thread: threading.Thread | None = None
        self._transcribe_thread: threading.Thread | None = None

    @staticmethod
    def _clear_queue(target: "queue.Queue[Any]") -> None:
        while True:
            try:
                target.get_nowait()
            except queue.Empty:
                break

    @staticmethod
    def _push_queue_non_blocking(target: "queue.Queue[Any]", item: Any) -> None:
        try:
            target.put(item, timeout=0.1)
            return
        except queue.Full:
            pass

        try:
            target.get_nowait()
        except queue.Empty:
            return

        try:
            target.put_nowait(item)
        except queue.Full:
            pass

    def _microphone_capture_worker(self) -> None:
        global running

        try:
            import sounddevice as sd  # type: ignore
        except Exception as exc:
            self._audio_error = f"Microphone dependency unavailable: {exc}"
            running = False
            return

        frames = max(
            1, int(self.config.audio_sample_rate * self.config.audio_chunk_seconds)
        )
        while running:
            try:
                audio_chunk = sd.rec(
                    frames,
                    samplerate=self.config.audio_sample_rate,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()
                if not running:
                    break
                self._push_queue_non_blocking(audio_queue, audio_chunk)
            except Exception as exc:
                self._audio_error = str(exc)[:300]
                time.sleep(0.1)

    def _transcription_worker(self) -> None:
        global running

        try:
            import numpy as np  # type: ignore

            whisper_model = _load_whisper_model_once(self.config.whisper_model_name)
        except Exception as exc:
            self._transcription_error = f"Whisper unavailable: {exc}"
            running = False
            return

        while running or not audio_queue.empty():
            try:
                audio_chunk = audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                mono = np.squeeze(audio_chunk).astype(np.float32)
                if mono.size == 0:
                    continue

                transcript_result = whisper_model.transcribe(
                    mono,
                    fp16=False,
                    language=self.config.language,
                )
                transcript = str(transcript_result.get("text", "")).strip()
                if transcript:
                    self._push_queue_non_blocking(text_queue, transcript)
            except Exception as exc:
                self._transcription_error = str(exc)[:300]
            finally:
                try:
                    audio_queue.task_done()
                except Exception:
                    pass

    def _prepare_questions_before_video_loop(self) -> None:
        # Question generation happens before video capture to avoid blocking frame processing.
        self.current_question = generate_question(
            self.role, self.difficulty, self.resume_text
        )
        for _ in range(max(0, self.config.prefetch_questions - 1)):
            _ = generate_question(self.role, self.difficulty, self.resume_text)

    def _start_audio_threads(self) -> None:
        self._clear_queue(audio_queue)
        self._clear_queue(text_queue)

        self._mic_thread = threading.Thread(
            target=self._microphone_capture_worker,
            name="microphone-capture-thread",
            daemon=True,
        )
        self._transcribe_thread = threading.Thread(
            target=self._transcription_worker,
            name="whisper-transcription-thread",
            daemon=True,
        )
        self._mic_thread.start()
        self._transcribe_thread.start()

    def _stop_audio_threads(self) -> None:
        global running

        running = False
        if self._mic_thread and self._mic_thread.is_alive():
            self._mic_thread.join(timeout=2.0)
        if self._transcribe_thread and self._transcribe_thread.is_alive():
            self._transcribe_thread.join(timeout=4.0)

    def _drain_transcript_queue(self) -> None:
        while True:
            try:
                self.latest_transcript = str(text_queue.get_nowait()).strip()
            except queue.Empty:
                break

    def run(self) -> None:
        global running

        cv2, _ = _safe_import_cv2_np()
        if cv2 is None:
            raise RuntimeError(
                "OpenCV is not available. Cannot start live interview runtime."
            )

        self._prepare_questions_before_video_loop()
        _load_whisper_model_once(self.config.whisper_model_name)

        cap = cv2.VideoCapture(self.config.camera_index)
        if not cap.isOpened():
            raise RuntimeError(
                f"Unable to open camera index {self.config.camera_index}."
            )

        running = True
        self._start_audio_threads()
        frame_count = 0

        try:
            while running:
                ok, frame = cap.read()
                if not ok:
                    break

                frame_count += 1
                should_sample_emotion = (
                    frame_count % max(1, self.config.deepface_every_n_frames)
                ) == 0

                ok_encode, encoded = cv2.imencode(".jpg", frame)
                if ok_encode:
                    self._analysis_cache = self.monitor.analyze_frame_bytes(
                        encoded.tobytes(),
                        self.config.interview_id,
                        sample_emotion=should_sample_emotion,
                    )

                self._drain_transcript_queue()
                emotion = str(self._analysis_cache.get("emotion_label", "unknown"))
                warnings = self._analysis_cache.get("warnings") or []
                warning_line = str(warnings[0]) if warnings else "No active warning"

                cv2.putText(
                    frame,
                    f"Question: {self.current_question}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Emotion: {emotion}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Warning: {warning_line}",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )
                cv2.putText(
                    frame,
                    f"Transcript: {self.latest_transcript}",
                    (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2,
                )

                cv2.imshow(self.config.window_title, frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    running = False
                    break
        finally:
            self._stop_audio_threads()
            cap.release()
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass


monitor = AIInterviewMonitor()

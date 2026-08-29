import base64
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .schemas import AssistedAttachment, EvidenceAnalysis, EvidenceObservation

MAX_EVIDENCE_FILES = 6
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_VIDEO_SECONDS = 120.0
MAX_VIDEO_FRAMES = 6
MAX_FRAME_WIDTH = 1280


@dataclass
class PreparedEvidence:
    images: list[dict[str, str]] = field(default_factory=list)
    evidence_items: list[dict] = field(default_factory=list)
    analysis: EvidenceAnalysis = field(default_factory=EvidenceAnalysis)


class EvidenceService:
    def __init__(self, ffmpeg: str | None = None, ffprobe: str | None = None):
        self.ffmpeg = shutil.which("ffmpeg") if ffmpeg is None else ffmpeg
        self.ffprobe = shutil.which("ffprobe") if ffprobe is None else ffprobe

    def prepare(self, attachments: list[AssistedAttachment]) -> PreparedEvidence:
        prepared = PreparedEvidence()
        image_bytes = 0
        for attachment in attachments[:MAX_EVIDENCE_FILES]:
            if attachment.content_type.startswith("image/"):
                item, images, warnings = self._prepare_image(attachment, image_bytes)
                if item:
                    prepared.evidence_items.append(item)
                for image in images:
                    image_bytes += image.get("size_bytes", 0)
                    prepared.images.append({"name": image["name"], "data_url": image["data_url"]})
                prepared.analysis.warnings.extend(warnings)
                if item:
                    prepared.analysis.analysed_sources.append(attachment.name)
            elif attachment.content_type.startswith("video/"):
                item, images, observations, warnings = self._prepare_video(attachment)
                if item:
                    prepared.evidence_items.append(item)
                    prepared.analysis.analysed_sources.append(attachment.name)
                prepared.images.extend(images)
                prepared.analysis.observations.extend(observations)
                prepared.analysis.warnings.extend(warnings)
            else:
                prepared.analysis.warnings.append(f"{attachment.name}: unsupported evidence type for analysis")
        return prepared

    def _decode(self, attachment: AssistedAttachment) -> bytes:
        if not attachment.data_base64:
            raise ValueError("evidence data was not supplied for analysis")
        return base64.b64decode(attachment.data_base64, validate=True)

    def _prepare_image(self, attachment: AssistedAttachment, current_bytes: int):
        try:
            raw = self._decode(attachment)
        except Exception:
            return None, [], [f"{attachment.name}: invalid image encoding"]
        if current_bytes + len(raw) > MAX_IMAGE_BYTES:
            return None, [], ["Some image evidence was omitted because the analysis image limit is 12 MB"]
        data_url = f"data:{attachment.content_type};base64,{attachment.data_base64}"
        item = {"name": attachment.name, "content_type": attachment.content_type, "size_bytes": len(raw), "kind": "image"}
        return item, [{"name": attachment.name, "data_url": data_url, "size_bytes": len(raw)}], []

    def _prepare_video(self, attachment: AssistedAttachment):
        try:
            raw = self._decode(attachment)
        except Exception:
            return None, [], [], [f"{attachment.name}: invalid video encoding"]
        if len(raw) > MAX_VIDEO_BYTES:
            return None, [], [], [f"{attachment.name}: video exceeds the {MAX_VIDEO_BYTES // (1024 * 1024)} MB analysis limit"]
        if not self.ffmpeg or not self.ffprobe:
            return {"name": attachment.name, "content_type": attachment.content_type, "size_bytes": len(raw), "kind": "video"}, [], [], [f"{attachment.name}: video analysis is unavailable because ffmpeg/ffprobe are not installed"]
        suffix = self._suffix_for(attachment.content_type)
        with tempfile.TemporaryDirectory(prefix="devhub-evidence-") as temp_dir:
            src = Path(temp_dir) / f"source{suffix}"
            src.write_bytes(raw)
            try:
                duration, width, height = self._probe(src)
            except Exception:
                return None, [], [], [f"{attachment.name}: malformed or unsupported video"]
            analysed_duration = min(duration, MAX_VIDEO_SECONDS)
            frame_count = min(MAX_VIDEO_FRAMES, max(2, int(analysed_duration // 12) + 2))
            timestamps = self._timestamps(analysed_duration, frame_count)
            images: list[dict[str, str]] = []
            observations: list[EvidenceObservation] = []
            for index, second in enumerate(timestamps):
                frame = Path(temp_dir) / f"frame-{index}.jpg"
                if self._extract_frame(src, frame, second):
                    encoded = base64.b64encode(frame.read_bytes()).decode("ascii")
                    images.append({"name": f"{attachment.name} @ {self._format_time(second)}", "data_url": f"data:image/jpeg;base64,{encoded}"})
                    observations.append(EvidenceObservation(source=attachment.name, timestamp=self._format_time(second), observation="Representative frame extracted for multimodal analysis.", confidence="High", evidence_type="direct"))
            warnings: list[str] = []
            if duration > MAX_VIDEO_SECONDS:
                warnings.append(f"{attachment.name}: only the first {int(MAX_VIDEO_SECONDS)} seconds were analysed")
            if not images:
                warnings.append(f"{attachment.name}: no usable video frames could be extracted")
            item = {"name": attachment.name, "content_type": attachment.content_type, "size_bytes": len(raw), "kind": "video", "duration_seconds": round(duration, 2), "analysed_duration_seconds": round(analysed_duration, 2), "width": width, "height": height, "extracted_frames": len(images)}
            return item, images, observations, warnings

    def _probe(self, path: Path) -> tuple[float, int | None, int | None]:
        result = subprocess.run([self.ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "default=noprint_wrappers=1", str(path)], capture_output=True, text=True, timeout=15, check=True)
        values: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        duration = float(values.get("duration") or 0)
        if duration <= 0:
            raise ValueError("duration unavailable")
        return duration, int(values["width"]) if values.get("width") else None, int(values["height"]) if values.get("height") else None

    def _extract_frame(self, src: Path, dest: Path, second: float) -> bool:
        try:
            subprocess.run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{second:.3f}", "-i", str(src), "-frames:v", "1", "-vf", f"scale='min({MAX_FRAME_WIDTH},iw)':-2", "-q:v", "3", "-y", str(dest)], capture_output=True, timeout=20, check=True)
            return dest.exists() and dest.stat().st_size > 0
        except Exception:
            return False

    @staticmethod
    def _timestamps(duration: float, count: int) -> list[float]:
        if count <= 1:
            return [0.0]
        if duration <= 0:
            return [0.0]
        end = max(0.0, duration - 0.1)
        return [round(end * index / (count - 1), 3) for index in range(count)]

    @staticmethod
    def _format_time(second: float) -> str:
        total = max(0, int(round(second)))
        return f"{total // 60:02d}:{total % 60:02d}"

    @staticmethod
    def _suffix_for(content_type: str) -> str:
        return {"video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm"}.get(content_type, ".video")


def provider_capabilities(provider: str) -> dict[str, bool]:
    provider = (provider or "").strip().lower()
    if provider in {"openai", "openai-compatible"}:
        return {"text": True, "images": True, "multiple_images": True, "direct_video": False, "video_frames": True, "structured_output": True}
    return {"text": True, "images": False, "multiple_images": False, "direct_video": False, "video_frames": False, "structured_output": False}

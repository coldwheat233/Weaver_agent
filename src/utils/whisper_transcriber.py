"""语音转写 —— 本地 Whisper 封装"""

from pathlib import Path
from src.utils.logging_config import logger


class WhisperTranscriber:
    """本地语音转文本（懒加载 Whisper 模型）"""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    @property
    def model(self):
        if self._model is None:
            import whisper
            logger.info(f"Loading Whisper model: {self.model_size}")
            self._model = whisper.load_model(self.model_size)
        return self._model

    def transcribe(self, audio_path: str | Path) -> dict:
        """转写音频文件，返回 {text, language, segments}"""
        result = self.model.transcribe(str(audio_path))
        return {
            "text": result.get("text", ""),
            "language": result.get("language", ""),
            "segments": result.get("segments", []),
        }

    def transcribe_text_only(self, audio_path: str | Path) -> str:
        """仅返回转写文本"""
        result = self.transcribe(audio_path)
        return result["text"]

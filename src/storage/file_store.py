"""文件存储 I/O —— 图片、音频、导出的读写"""

from pathlib import Path
from src.utils.config import get_settings

settings = get_settings()


class FileStore:
    def __init__(self):
        self.assets_dir = settings.assets_dir
        self.exports_dir = settings.exports_dir

    def save_image(self, data: bytes, filename: str) -> str:
        """保存图片，返回相对路径"""
        path = self.assets_dir / "images" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path.relative_to(Path.cwd()))

    def save_audio(self, data: bytes, filename: str) -> str:
        """保存音频，返回相对路径"""
        path = self.assets_dir / "audio" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path.relative_to(Path.cwd()))

    def save_design_markdown(self, content: str, title: str, date_str: str) -> Path:
        """保存设计文档 Markdown"""
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:80]
        filename = f"design_{date_str}_{safe_title}.md"
        path = self.exports_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def get_asset_path(self, relative_path: str) -> Path:
        return Path(relative_path)

/**
 * Idea Weaver — Capture Overlay Frontend
 * 剪贴板 · 麦克风 · API 调用 · 动效
 */
const API_BASE = window.WEAVER_API_URL || 'http://localhost:8765';

class CaptureApp {
  constructor() {
    this.textArea = document.getElementById('idea-input');
    this.attachmentsEl = document.getElementById('attachments');
    this.recordingBar = document.getElementById('recording-bar');
    this.recordingTime = document.getElementById('recording-time');
    this.submitBtn = document.getElementById('submit-btn');
    this.overlay = document.getElementById('overlay');

    this.pastedFiles = [];
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.recordingSeconds = 0;
    this.recordingTimer = null;

    this.init();
  }

  init() {
    this.textArea.focus();

    document.addEventListener('paste', (e) => this.handlePaste(e));

    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'Enter') this.submit();
      if (e.key === 'Escape') this.dismiss();
    });

    this.textArea.addEventListener('input', () => this.updateSubmitState());
    this.submitBtn.addEventListener('click', () => this.submit());
  }

  async handlePaste(e) {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const blob = item.getAsFile();
        const dataUrl = await this.blobToDataUrl(blob);
        this.pastedFiles.push({
          name: `clipboard-${Date.now()}.png`,
          dataUrl,
          blob,
        });
        this.renderThumbnails();
      }
    }
  }

  async toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      await this.startRecording();
    }
  }

  async startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.audioChunks.push(e.data);
      };

      this.mediaRecorder.onstop = async () => {
        const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.pastedFiles.push({
          name: `recording-${Date.now()}.webm`,
          blob,
        });
        this.renderThumbnails();
        stream.getTracks().forEach((t) => t.stop());
      };

      this.mediaRecorder.start();
      this.isRecording = true;
      this.recordingBar.classList.remove('hidden');
      this.recordingSeconds = 0;
      this.updateRecordingTime();
      this.recordingTimer = setInterval(() => {
        this.recordingSeconds++;
        this.updateRecordingTime();
      }, 1000);
    } catch (err) {
      console.error('Mic access denied:', err);
    }
  }

  stopRecording() {
    this.mediaRecorder?.stop();
    this.isRecording = false;
    this.recordingBar.classList.add('hidden');
    clearInterval(this.recordingTimer);
    this.recordingTimer = null;
  }

  updateRecordingTime() {
    const m = Math.floor(this.recordingSeconds / 60);
    const s = this.recordingSeconds % 60;
    this.recordingTime.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  updateSubmitState() {
    const hasContent = this.textArea.value.trim().length > 0;
    const hasFiles = this.pastedFiles.length > 0;
    this.submitBtn.disabled = !hasContent && !hasFiles;
  }

  async submit() {
    const text = this.textArea.value.trim();
    if (!text && this.pastedFiles.length === 0) return;

    this.submitBtn.disabled = true;
    this.submitBtn.classList.add('loading');
    this.submitBtn.querySelector('.btn-text').textContent = '捕捉中';

    try {
      // 上传文件
      for (const file of this.pastedFiles) {
        const formData = new FormData();
        formData.append('file', file.blob, file.name);
        await fetch(`${API_BASE}/api/assets/upload`, {
          method: 'POST',
          body: formData,
        });
      }

      // 提交想法
      const formData = new FormData();
      formData.append('content', text || '(图片/语音输入)');
      formData.append('source_type', text ? 'text' : 'image');

      const resp = await fetch(`${API_BASE}/api/ideas`, {
        method: 'POST',
        body: formData,
      });

      if (resp.ok) {
        this.showSuccess();
      } else {
        this.showError();
      }
    } catch (err) {
      console.error('Submit failed:', err);
      this.showError();
    }
  }

  showSuccess() {
    this.submitBtn.querySelector('.btn-text').textContent = '✓ 已捕捉';
    this.submitBtn.classList.remove('loading');
    this.submitBtn.style.background = 'var(--color-success)';
    setTimeout(() => this.dismiss(), 800);
  }

  showError() {
    this.submitBtn.querySelector('.btn-text').textContent = '重试';
    this.submitBtn.classList.remove('loading');
    this.submitBtn.disabled = false;
    this.submitBtn.style.background = 'var(--color-danger)';
    setTimeout(() => {
      this.submitBtn.style.background = '';
      this.updateSubmitState();
    }, 1500);
  }

  dismiss() {
    this.overlay.classList.remove('visible');
    setTimeout(() => window.close(), 250);
  }

  reset() {
    this.textArea.value = '';
    this.pastedFiles = [];
    this.renderThumbnails();
    this.updateSubmitState();
  }

  renderThumbnails() {
    this.attachmentsEl.innerHTML = this.pastedFiles.map((f, i) => {
      const isImage = f.dataUrl && f.dataUrl.startsWith('data:image');
      return `
        <div class="attachment-thumb ${isImage ? '' : 'audio'}">
          ${isImage
            ? `<img src="${f.dataUrl}" alt="${f.name}">`
            : `<span>🎵</span>`}
          <button class="remove-attachment" data-index="${i}">×</button>
        </div>`;
    }).join('');

    this.attachmentsEl.querySelectorAll('.remove-attachment').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(e.target.dataset.index);
        this.pastedFiles.splice(idx, 1);
        this.renderThumbnails();
        this.updateSubmitState();
      });
    });

    this.updateSubmitState();
  }

  blobToDataUrl(blob) {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.readAsDataURL(blob);
    });
  }
}

document.addEventListener('DOMContentLoaded', () => new CaptureApp());

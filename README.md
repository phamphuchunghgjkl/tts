# XTTS v2 — Vietnamese Voice Cloning (Minimal)

Minimal project **only** using **Coqui TTS (XTTS v2)** with a simple Streamlit UI for offline Vietnamese TTS with voice cloning.

> ⚠️ Lần đầu chạy sẽ tải model ~1.5GB vào `~/.local/share/tts`. Sau đó chạy **offline** (không cần mạng).

## 1) Cài đặt
### Bước 1 — Cài PyTorch GPU (khớp CUDA của máy)
Ví dụ CUDA 11.8:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```
> Nếu không có GPU, có thể dùng bản CPU (sẽ chậm hơn):
```bash
pip install torch torchvision torchaudio
```

### Bước 2 — Cài Coqui TTS và Streamlit + ffmpeg
```bash
pip install TTS==0.22.0 streamlit==1.37.1
# ffmpeg để đọc/ghi audio (không bắt buộc nhưng nên có)
# Windows: choco install ffmpeg
# Ubuntu/Debian: sudo apt-get install ffmpeg
```

## 2) Chạy UI
```bash
streamlit run app.py
```
- Upload **mẫu giọng** của bạn (WAV/FLAC/MP3, khoảng **30–60s**, càng sạch càng tốt).
- Nhập văn bản (tiếng Việt), nhấn **Tạo giọng nói** để xuất file WAV.
- File sẽ được lưu tại `outputs/xtts_output.wav` và có nút tải xuống ngay trên UI.

## 3) Mẹo nâng chất lượng
- Ghi âm trong phòng yên tĩnh, mic ổn định; tránh tiếng quạt/echo.
- Đọc tự nhiên, đủ dấu tiếng Việt; 30–60s là đủ cho demo.
- Có thể chuẩn hoá âm lượng (optional).

## 4) Lưu ý đạo đức & pháp lý
- Chỉ clone **giọng của chính bạn** hoặc khi có **sự đồng ý** của chủ sở hữu giọng nói.

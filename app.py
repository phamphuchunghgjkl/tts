import streamlit as st
from pathlib import Path
import json
import uuid
import datetime
import os
import tempfile

st.set_page_config(page_title="XTTS v2 — TTS Offline", page_icon="🗣️", layout="wide")

# theme 
st.markdown(
    """
    <style>
    .stApp { background-color: #ffffff; }
    .history-row { border: 1px solid #eee; border-radius: 10px; padding: 0.75rem 1rem; margin-bottom: 0.75rem; background: #fff; }
    .history-title { font-weight: 600; }
    .small { font-size: 0.75rem; color: #666; }
    </style>
    """,
    unsafe_allow_html=True,
)

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_CACHE_ROOT = PROJECT_ROOT.parent / "xtts_model_cache"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
HISTORY_FILE = OUTPUT_DIR / "history.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_CACHE_ROOT.mkdir(parents=True, exist_ok=True)


# lich su
def load_history() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(items: list):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def add_history_item(text: str, lang: str, voice_path: str, output_path: str):
    items = load_history()
    item = {
        "id": str(uuid.uuid4()),
        "text": text,
        "lang": lang,
        "voice_path": voice_path,       
        "output_path": output_path,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    items.insert(0, item)  
    save_history(items)


# load model 
@st.cache_resource(show_spinner=True)
def load_model():
    os.environ["COQUI_TTS_HOME"] = str(MODEL_CACHE_ROOT)
    from TTS.api import TTS
    return TTS("tts_models/multilingual/multi-dataset/xtts_v2")

def pick_device(opt: str):
    if opt == "auto":
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"
    return opt

# edit
if "edit_item" not in st.session_state:
    st.session_state.edit_item = None


def set_edit_item(item: dict):
    st.session_state.edit_item = item


# ui
st.title("XTTS v2 — TTS Offline + Lịch sử bản thu âm")

tab_make, tab_history = st.tabs(["Tạo bản thu âm", "Lịch sử"])

# tab 1: tao ban thu am 

with tab_make:
    with st.expander("Hướng dẫn nhanh", expanded=False):
        st.markdown(
            """
            1. **Tải mẫu giọng** của bạn (WAV/FLAC/MP3, ~30–60s).
            2. Nhập **văn bản tiếng Việt** cần đọc.
            3. Nhấn **Tạo giọng nói** → nhận file WAV và được lưu vào **Lịch sử**.
            """
        )

    # nếu đang edit từ lịch sử thì đổ dữ liệu vào form
    defaults = st.session_state.edit_item or {}
    default_text = defaults.get("text", "Xin chào, đây là giọng nói được clone bằng XTTS v2.")
    default_lang = defaults.get("lang", "vi")

    ref = st.file_uploader(
        "Tải mẫu giọng của bạn (WAV/FLAC/MP3)", type=["wav", "flac", "mp3"]
    )
    text = st.text_area("Nhập văn bản", default_text, height=140)

    col1, col2 = st.columns(2)
    with col1:
        lang = st.selectbox(
            "Ngôn ngữ",
            ["vi", "en", "ja", "ko", "fr", "de", "es"],
            index=["vi", "en", "ja", "ko", "fr", "de", "es"].index(default_lang)
            if default_lang in ["vi", "en", "ja", "ko", "fr", "de", "es"]
            else 0,
        )
    with col2:
        device_opt = st.selectbox("Thiết bị", ["auto", "cuda", "cpu"], index=0)

    btn = st.button("🎙️ Tạo giọng nói", type="primary")

    if btn:
        if not ref:
            st.warning("Vui lòng tải lên một mẫu giọng (30–60s, càng sạch càng tốt).")
        elif not text.strip():
            st.warning("Vui lòng nhập văn bản.")
        else:
            device = pick_device(device_opt)
            st.info(f"⏳ Đang tải model (nếu cần) và tổng hợp trên **{device.upper()}**...")

            # lưu file mẫu giọng vào outputs/voices/ để lịch sử còn dùng lại
            voices_dir = OUTPUT_DIR / "voices"
            voices_dir.mkdir(parents=True, exist_ok=True)
            voice_ext = ref.name.split(".")[-1].lower()
            voice_path = voices_dir / f"voice_{uuid.uuid4().hex}.{voice_ext}"
            with open(voice_path, "wb") as vf:
                vf.write(ref.getbuffer())

            # synth
            tts = load_model()
            out_path = OUTPUT_DIR / f"xtts_output_{uuid.uuid4().hex}.wav"

            tts.tts_to_file(
                text=text,
                speaker_wav=str(voice_path),
                language=lang,
                file_path=str(out_path),
                split_sentences=True,
            )

            # lưu vào lịch sử
            add_history_item(
                text=text,
                lang=lang,
                voice_path=str(voice_path),
                output_path=str(out_path),
            )

            # hiển thị
            audio_bytes = open(out_path, "rb").read()
            st.success(f"✅ Hoàn tất! Đã lưu: {out_path.name} và ghi vào lịch sử.")
            st.audio(audio_bytes, format="audio/wav")
            st.download_button(
                "⬇️ Tải file WAV", data=audio_bytes, file_name=out_path.name
            )

            # sau khi tạo xong thì bỏ trạng thái edit
            st.session_state.edit_item = None

# tab 2: lich su
with tab_history:
    st.subheader("📜 Các bản thu âm đã tạo")
    items = load_history()
    if not items:
        st.info("Chưa có bản thu âm nào. Hãy sang tab **Tạo bản thu âm** để tạo.")
    else:
        # hiển thị từng bản
        for item in items:
            with st.container():
                st.markdown('<div class="history-row">', unsafe_allow_html=True)

                c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
                with c1:
                    st.markdown(
                        f"<div class='history-title'>{item['text'][:80]}{'...' if len(item['text'])>80 else ''}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div class='small'>ID: {item['id']} • Lang: {item['lang']} • {item['created_at']}</div>",
                        unsafe_allow_html=True,
                    )

                # nghe lại
                with c2:
                    out_path = Path(item["output_path"])
                    if out_path.exists():
                        audio_bytes = out_path.read_bytes()
                        st.audio(audio_bytes, format="audio/wav")
                    else:
                        st.warning("⚠️ File âm thanh đã bị xoá trên đĩa.")

                # nút sửa (nạp lên tab 1)
                with c3:
                    if st.button("✏️ Sửa", key=f"edit_{item['id']}"):
                        set_edit_item(item)
                        # chuyển sang tab 1 bằng cách hiển thị thông báo
                        st.info("Quay lại tab 'Tạo bản thu âm' để sửa.")
                # nút xoá
                with c4:
                    if st.button("🗑️ Xoá", key=f"del_{item['id']}"):
                        # xoá file output
                        if Path(item["output_path"]).exists():
                            try:
                                Path(item["output_path"]).unlink()
                            except Exception:
                                pass
                        # xoá file voice nếu muốn
                        if Path(item["voice_path"]).exists():
                            try:
                                Path(item["voice_path"]).unlink()
                            except Exception:
                                pass
                        # xoá khỏi history
                        new_items = [x for x in items if x["id"] != item["id"]]
                        save_history(new_items)
                        st.experimental_rerun()

                # nút download riêng
                if Path(item["output_path"]).exists():
                    st.download_button(
                        "⬇️ Tải",
                        data=Path(item["output_path"]).read_bytes(),
                        file_name=Path(item["output_path"]).name,
                        key=f"dl_{item['id']}",
                    )

                st.markdown("</div>", unsafe_allow_html=True)
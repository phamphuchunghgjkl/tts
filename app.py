import streamlit as st
from pathlib import Path
import uuid
import os
import yaml 
import streamlit_authenticator as stauth 
from streamlit_authenticator.utilities.hasher import Hasher
from yaml.loader import SafeLoader 
import database as db 

# Khởi tạo database
db.init_db()

# Helper to trigger a rerun in a way that's compatible across Streamlit versions
def do_rerun():
    try:
        # Preferred public API when available
        st.experimental_rerun()
    except Exception:
        try:
            # Fallback to internal request if present
            from streamlit.runtime.scriptrunner import script_request_rerun

            script_request_rerun()
        except Exception:
            # Final fallback: stop execution and rely on next user action
            st.stop()

st.set_page_config(page_title="XTTS v2", page_icon="🗣️", layout="wide")

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
# HISTORY_FILE = OUTPUT_DIR 

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_CACHE_ROOT.mkdir(parents=True, exist_ok=True)


# --- PHẦN XÁC THỰC ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookies']['cookie_name'],
    config['cookies']['key'],
    config['cookies']['cookie_expiry_days'],
)

# Load users from MySQL into the authenticator's in-memory credentials so login works
try:
    model = authenticator.authentication_controller.authentication_model
    users = db.list_users()
    for u in users:
        uname = u.get('username')
        if not uname:
            continue
        # normalise key (authenticator uses lowercase keys)
        uname_key = uname.lower().strip()
        if uname_key in model.credentials.get('usernames', {}):
            continue
        pw = u.get('password') or ''
        first_name = u.get('first_name') or uname_key
        last_name = u.get('last_name') or uname_key
        email = u.get('email') or f"{uname_key}@example.com"
        # If password in DB looks like a hash, insert it directly; otherwise register to hash it.
        if Hasher.is_hash(pw):
            model.credentials['usernames'][uname_key] = {
                'email': email,
                'logged_in': False,
                'first_name': first_name,
                'last_name': last_name,
                'password': pw,
            }
        else:
            # _register_credentials will hash the password and persist to model.credentials
            model._register_credentials(uname_key, first_name, last_name, pw, email, "", None)
except Exception:
    pass

# - Tab 1: login form 
# - Tab 2: register form 
name = st.session_state.get('name')
authentication_status = st.session_state.get('authentication_status')
username = st.session_state.get('username')

if not authentication_status:
    login_tab, signup_tab = st.tabs(["Đăng nhập", "Đăng ký"])

    with login_tab:
        # Render login form
        authenticator.login('main')

    with signup_tab:
        # registration form
        with st.form(key='simple_register'):
            reg_name = st.text_input('Họ & Tên')
            reg_username = st.text_input('Tên đăng nhập')
            reg_password = st.text_input('Mật khẩu', type='password')
            reg_password_repeat = st.text_input('Nhập lại mật khẩu', type='password')
            submitted = st.form_submit_button('Đăng ký')

        if submitted:
            if not reg_name or not reg_username or not reg_password:
                st.error('Vui lòng nhập đầy đủ Họ & Tên, Tên đăng nhập và Mật khẩu.')
            elif reg_password != reg_password_repeat:
                st.error('Mật khẩu không khớp. Vui lòng thử lại.')
            else:
                try:
                    # Parse full name into first and last name.
                    parts = reg_name.strip().split()
                    if len(parts) == 0:
                        first_name = reg_username
                        last_name = reg_username
                    elif len(parts) == 1:
                        first_name = parts[0]
                        last_name = parts[0]
                    else:
                        first_name = parts[0]
                        last_name = " ".join(parts[1:])

                    # Normalize username (the controller lowercases usernames on login)
                    username_key = reg_username.lower().strip()

                    # Construct a dummy but valid email from username since the library
                    # requires an email field. Use example.com to avoid accidental delivery.
                    reg_email = f"{username_key}@example.com"

                    model = authenticator.authentication_controller.authentication_model

                    # Check DB first to avoid conflicts across restarts
                    existing = db.get_user(username_key)
                    if existing:
                        st.error('Tên đăng nhập đã tồn tại (trong DB). Vui lòng chọn tên khác.')
                    elif username_key in model.credentials.get('usernames', {}):
                        st.error('Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác.')
                    else:
                        # Register in the authenticator model (it will hash the password)
                        model._register_credentials(username_key, first_name, last_name,
                                                    reg_password, reg_email, "", None)

                        # Retrieve the hashed password produced by the model and persist to DB
                        pw_hash = model.credentials['usernames'][username_key].get('password')
                        if not pw_hash:
                            st.warning('Đã tạo user nhưng không lấy được hash mật khẩu để lưu DB.')
                        else:
                            saved = db.add_user(username_key, pw_hash, first_name, last_name, reg_email)
                            if not saved:
                                st.warning('Đã tạo user trong bộ nhớ nhưng không lưu vào DB.')

                        st.success('Đăng ký thành công! Vui lòng đăng nhập (sử dụng tên đăng nhập viết thường).')
                except Exception as e:
                    st.error(f'Lỗi khi đăng ký: {e}')

    # Sau khi hiển thị các form, cập nhật lại trạng thái từ session_state
    name = st.session_state.get('name')
    authentication_status = st.session_state.get('authentication_status')
    username = st.session_state.get('username')

if authentication_status == False:
    st.error('Tên đăng nhập/Mật khẩu không đúng')
elif authentication_status == None:
    st.warning('Vui lòng nhập tên đăng nhập và mật khẩu')
# --- end authentication ---

#hien ui sau khi dang nhap 
if authentication_status:
    
    # ---- Sidebar ----
    with st.sidebar:
        st.title(f"Chào mừng, {name}!")
        authenticator.logout('Đăng xuất', 'main')
    # ---- Sidebar ----
    
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
    if "edit_item_id" not in st.session_state:
        st.session_state.edit_item_id = None

    def set_edit_item(item_id: str):
        st.session_state.edit_item_id = item_id

    # ui
    st.title("XTTS v2 — Text to Speech ️")
    # (needed so the "Sửa" button can jump back to the create view).
    if 'active_tab' not in st.session_state:
        st.session_state['active_tab'] = "Tạo bản thu âm"
    active_tab = st.radio(
        "",
        ["Tạo bản thu âm", "Lịch sử"],
        index=0 if st.session_state.get('active_tab') == "Tạo bản thu âm" else 1,
        horizontal=True,
    )

    # tab 1: tao ban thu am
    if active_tab == "Tạo bản thu âm":
        # keep the active_tab in session_state so other handlers can change it
        st.session_state['active_tab'] = "Tạo bản thu âm"
        with st.expander("Hướng dẫn nhanh", expanded=False):
            st.markdown(
                """
                1. **Tải mẫu giọng** của bạn (WAV/FLAC/MP3, ~30–60s).
                2. Nhập **văn bản tiếng Việt** cần đọc.
                3. Nhấn **Tạo giọng nói** → nhận file WAV và được lưu vào **Lịch sử**.
                """
            )

        # nếu đang edit từ lịch sử thì đổ dữ liệu vào form
        default_text = "Xin chào, đây là giọng nói được clone bằng XTTS v2."
        default_lang = "vi"
        
        if st.session_state.edit_item_id:
            item_to_edit = db.get_history_item(st.session_state.edit_item_id)
            if item_to_edit:
                default_text = item_to_edit.get("text", default_text)
                default_lang = item_to_edit.get("lang", default_lang)
                st.info(f"Đang sửa mục: {item_to_edit['text'][:50]}...")


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

        btn = st.button("Tạo giọng nói", type="primary")

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
                # Dùng username từ st.session_state
                db.add_history_item(
                    username=username, 
                    text=text,
                    lang=lang,
                    voice_path=str(voice_path),
                    output_path=str(out_path),
                )
                # hiển thị
                audio_bytes = open(out_path, "rb").read()
                st.success(f"Đã lưu: {out_path.name} và ghi vào lịch sử.")
                st.audio(audio_bytes, format="audio/wav")
                st.download_button(
                    "Tải file WAV", data=audio_bytes, file_name=out_path.name
                )
                # sau khi tạo xong thì bỏ trạng thái edit
                st.session_state.edit_item_id = None

    # tab 2: lich su
    if active_tab == "Lịch sử":
        st.subheader(f"Lịch sử của {name}")
        # Tải lịch sử cho user hiện tại 
        items = db.load_history(username) 
        
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
                            st.warning("File âm thanh đã bị xoá.")

                    # nút sửa (nạp lên tab 1)
                    with c3:
                        if st.button("Sửa", key=f"edit_{item['id']}"):
                            # set edit id and switch to the create tab
                            set_edit_item(item['id'])
                            st.session_state['active_tab'] = "Tạo bản thu âm"
                            st.info("Đã tải dữ liệu. Đã chuyển sang tab 'Tạo bản thu âm' để sửa.")
                            do_rerun()
                            
                    # nút xoá
                    with c4:
                        if st.button("Xoá", key=f"del_{item['id']}"):
                            # Xoá khỏi DB và xoá file vật lý (ĐÃ THAY ĐỔI)
                            deleted = db.delete_history_item(username, item['id'])
                            if deleted:
                                st.success("Đã xoá mục lịch sử.")
                            else:
                                st.error("Không thể xoá mục. Vui lòng thử lại.")
                            do_rerun()

                    # nút download riêng
                    if Path(item["output_path"]).exists():
                        st.download_button(
                            "Tải",
                            data=Path(item["output_path"]).read_bytes(),
                            file_name=Path(item["output_path"]).name,
                            key=f"dl_{item['id']}",
                        )

                    st.markdown("</div>", unsafe_allow_html=True)

import streamlit_authenticator as stauth
import sys

print("--- Công cụ tạo mật khẩu Hash ---")

# Yêu cầu người dùng nhập mật khẩu
password = input("Nhập mật khẩu bạn muốn hash (ví dụ: 123456): ")

if not password:
    print("Lỗi: Mật khẩu không được để trống.")
    sys.exit()

try:
    # --- THAY ĐỔI 1: Sửa .generate([password]) thành .hash(password) ---
    hashed_password = stauth.Hasher().hash(password)
    # -----------------------------------------------------------------
    
    print("\n✅ Thành công!")
    print("Mật khẩu đã hash của bạn là (hãy copy toàn bộ dòng này):")
    
    # --- THAY ĐỔI 2: Bỏ [0] vì kết quả là string, không phải list ---
    print(f"\n{hashed_password}\n")
    # -------------------------------------------------------------
    
    print("Bây giờ, hãy dán chuỗi hash này vào mục 'password' của user trong file config.yaml")

except Exception as e:
    print(f"\nĐã xảy ra lỗi: {e}")
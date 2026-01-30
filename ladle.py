import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
from io import BytesIO
import os
import time
from math import pi, tan, radians

# ==========================================
# 1. 全局配置：改名字
# ==========================================
st.set_page_config(
    page_title="杨杨杨的铁水包设计平台", 
    layout="wide", 
    page_icon="🏭"
)

# --- 字体加载 (防乱码) ---
@st.cache_resource
def configure_fonts():
    font_files = ["SimHei.ttf", "simhei.ttf"] 
    found_font = None
    for f in font_files:
        if os.path.exists(f):
            found_font = f
            break
    
    if found_font:
        fm.fontManager.addfont(found_font)
        prop = fm.FontProperties(fname=found_font)
        return prop.get_name(), True
    else:
        return ["Microsoft YaHei", "SimHei", "sans-serif"], False

font_family, is_font_success = configure_fonts()
plt.rcParams['font.sans-serif'] = font_family
plt.rcParams['axes.unicode_minus'] = False

# ==========================================
# 2. 登录模块
# ==========================================
USERS = {
    "admin": "888888",
    "user1": "123456",
    "client": "vip2026"
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

def login_page():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("## 🔐 杨杨杨的铁水包设计平台")
        
        if is_font_success:
            st.success("✅ 系统就绪")
        else:
            st.warning("⚠️ 字体缺失，请上传 SimHei.ttf")
            
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submit = st.form_submit_button("登 录", type="primary", use_container_width=True)
            
            if submit:
                if username in USERS and USERS[username] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_name = username
                    st.success("登录成功！")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("账号或密码错误")

if not st.session_state.logged_in:
    login_page()
    st.stop()

# ==========================================
# 3. 侧边栏与状态
# ==========================================
with st.sidebar:
    st.title("🏭 参数设定")
    st.write(f"当前用户: **{st.session_state.user_name}**")
    if st.button("退出登录"):
        st.session_state.logged_in = False
        st.rerun()
    st.markdown("---")

    if 'aspect_ratio' not in st.session_state:
        st.session_state.aspect_ratio = 1.05

    def update_from_slider(): st.session_state.aspect_ratio = st.session_state.slider_val
    def update_from_input(): st.session_state.aspect_ratio = st.session_state.input_val

    st.subheader("1. 容量设定")
    input_volume = st.number_input("目标有效容积 (m³)", 0.1, 50.0, 4.5, 0.1)
    input_density = st.number_input("介质密度 (t/m³)", 1.0, 10.0, 7.0, 0.1)

    st.subheader("2. 形状控制 (D/H)")
    st.slider("粗调比例", 0.5, 2.5, key='slider_val', value=st.session_state.aspect_ratio, on_change=update_from_slider)
    st.number_input("精调数值", 0.5, 2.5, key='input_val', value=st.session_state.aspect_ratio, step=0.01, on_change=update_from_input)
    
    st.subheader("3. 结构细节 (mm)")
    input_freeboard = st.number_input("净空高度 (液面到顶)", value=300, step=50)
    input_angle = st.number_input("侧壁倾角 (°)", value=5.0, step=0.5)
    input_wall_thick = st.number_input("侧壁总厚度", value=160, step=10)
    input_bottom_thick = st.number_input("底部总厚度", value=230, step=10)

# ==========================================
# 4. 计算逻辑
# ==========================================
def solve_ladle(target_vol, density, t_wall, t_bot, freeboard, angle, ar):
    tw, tb, hf = t_wall/1000, t_bot/1000, freeboard/1000
    tan_a = tan(radians(angle))

    def get_capacity(h):
        h_liq = h - tb - hf
        if h_liq <= 0: return 0
        r_out_top = (ar * h) / 2
        r_out_bot = r_out_top - h * tan_a
        if r_out_bot <= 0: return 0
        
        r_in_top = (r_out_top - hf * tan_a) - tw
        r_in_bot = (r_out_bot + tb * tan_a) - tw
        if r_in_bot <= 0: return 0
        
        return (1/3) * pi * h_liq * (r_in_bot**2 + r_in_top**2 + r_in_bot*r_in_top)

    low, high = 0.1, 10.0
    for _ in range(50):
        mid = (low + high) / 2
        if get_capacity(mid) < target_vol: low = mid
        else: high = mid
            
    H_mm = high * 1000
    D_top = H_mm * ar
    D_bot = D_top - 2 * H_mm * tan_a
    h_liq = H_mm - t_bot - freeboard
    
    return {
        "H": H_mm, "Dt": D_top, "Db": D_bot, "hl": h_liq,
        "cap": target_vol * density, "vol": target_vol
    }

res = solve_ladle(input_volume, input_density, input_wall_thick, input_bottom_thick, input_freeboard, input_angle, st.session_state.aspect_ratio)

# ==========================================
# 5. 主界面显示
# ==========================================
st.title("🏭 杨杨杨的铁水包设计平台")
st.markdown("---")

c1, c2 = st.columns([1, 1.5])

with c1:
    st.subheader("📊 关键指标")
    k1, k2 = st.columns(2)
    k1.metric("总高度 H", f"{res['H']:.0f} mm")
    k2.metric("上口外径", f"{res['Dt']:.0f} mm")
    k3, k4 = st.columns(2)
    k3.metric("计算载重", f"{res['cap']:.2f} t")
    k4.metric("液面深度", f"{res['hl']:.0f} mm")
    
    st.markdown("#### 📥 导出数据")
    df = pd.DataFrame([
        ["总高度 H", f"{res['H']:.0f}", "mm"],
        ["上口外径", f"{res['Dt']:.0f}", "mm"],
        ["下底外径", f"{res['Db']:.0f}", "mm"],
        ["有效容积", f"{res['vol']:.2f}", "m³"],
        ["计算载重", f"{res['cap']:.2f}", "t"],
        ["侧壁厚度", f"{input_wall_thick}", "mm"],
        ["底部厚度", f"{input_bottom_thick}", "mm"],
        ["侧壁倾角", f"{input_angle}", "°"],
    ], columns=["项目", "数值", "单位"])
    
    st.dataframe(df, hide_index=True, use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("下载参数表 (CSV)", csv, "ladle_design.csv", "text/csv", use_container_width=True)

with c2:
    st.subheader("📐 设计图纸")
    H, Dt, Db = res['H'], res['Dt'], res['Db']
    hf = input_freeboard
    
    fig, ax = plt.subplots(figsize=(8, 7))
    
    # 炉壳
    x = [-Db/2, Db/2, Dt/2, -Dt/2]
    y = [0, 0, H, H]
    ax.add_patch(patches.Polygon(list(zip(x, y)), closed=True, fc='#F3F4F6', ec='#333', lw=3))
    
    # 铁水
    tan_a = tan(radians(input_angle))
    tw, tb = input_wall_thick, input_bottom_thick
    h_l = H - tb - hf
    rb = (Db/2) + tb*tan_a - tw
    rt = (Dt/2) - hf*tan_a - tw
    lx = [-rb, rb, rt, -rt]
    ly = [tb, tb, tb+h_l, tb+h_l]
    
    if rb > 0:
        ax.add_patch(patches.Polygon(list(zip(lx, ly)), closed=True, fc='#F59E0B', alpha=0.6))
        # 标注
        ax.plot([-Dt/2-200, -Dt/2-200], [0, H], 'k-', lw=1)
        ax.text(-Dt/2-250, H/2, f"H={H:.0f}", va='center', ha='right')
        ax.annotate("", xy=(-Dt/2, H+100), xytext=(Dt/2, H+100), arrowprops=dict(arrowstyle='<->'))
        ax.text(0, H+150, f"Ф{Dt:.0f}", ha='center', va='bottom')
        
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(f"铁水包结构图 (V={input_volume}m³)", y=0.05)
    st.pyplot(fig)
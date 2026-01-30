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
# 1. 全局配置
# ==========================================
st.set_page_config(
    page_title="杨博的智能铁水包设计系统", 
    layout="wide", 
    page_icon="🏭"
)

# --- 字体加载 ---
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
        st.markdown("## 🔐 杨博的智能铁水包设计系统")
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
# 3. 侧边栏设定
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
    # 默认密度 2.8
    input_density = st.number_input("介质密度 (t/m³)", 1.0, 10.0, 2.8, 0.1)

    st.subheader("2. 形状控制 (D/H)")
    st.slider("粗调比例", 0.5, 2.5, key='slider_val', value=st.session_state.aspect_ratio, on_change=update_from_slider)
    st.number_input("精调数值", 0.5, 2.5, key='input_val', value=st.session_state.aspect_ratio, step=0.01, on_change=update_from_input)
    
    st.subheader("3. 结构细节 (mm)")
    # 默认净空 150
    input_freeboard = st.number_input("净空高度 (液面到顶)", value=150, step=50)
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
    
    # 修改点：耳轴高度改为 70%
    trunnion_h = H_mm * 0.70

    return {
        "H": H_mm, "Dt": D_top, "Db": D_bot, "hl": h_liq,
        "cap": target_vol * density, "vol": target_vol,
        "z_trunnion": trunnion_h
    }

res = solve_ladle(input_volume, input_density, input_wall_thick, input_bottom_thick, input_freeboard, input_angle, st.session_state.aspect_ratio)

# ==========================================
# 5. 主界面显示
# ==========================================
st.title("🏭 杨博的智能铁水包设计系统")
st.markdown("---")

c1, c2 = st.columns([1, 1.5])

with c1:
    st.subheader("📊 关键指标")
    k1, k2 = st.columns(2)
    k1.metric("总高度 H", f"{res['H']:.0f} mm")
    k2.metric("上口外径", f"{res['Dt']:.0f} mm")
    k3, k4 = st.columns(2)
    k3.metric("计算载重", f"{res['cap']:.2f} t")
    k4.metric("耳轴建议高度", f"{res['z_trunnion']:.0f} mm")
    
    st.markdown("#### 📥 导出数据")
    df = pd.DataFrame([
        ["总高度 H", f"{res['H']:.0f}", "mm"],
        ["上口外径", f"{res['Dt']:.0f}", "mm"],
        ["下底外径", f"{res['Db']:.0f}", "mm"],
        ["有效容积", f"{res['vol']:.2f}", "m³"],
        ["计算载重", f"{res['cap']:.2f}", "t"],
        ["有效容深度", f"{res['hl']:.0f}", "mm"],
        ["耳轴高度 (EL)", f"{res['z_trunnion']:.0f}", "mm"],
        ["侧壁厚度", f"{input_wall_thick}", "mm"],
        ["底部厚度", f"{input_bottom_thick}", "mm"],
        ["侧壁倾角", f"{input_angle}", "°"],
        ["净空高度", f"{input_freeboard}", "mm"],
    ], columns=["项目", "数值", "单位"])
    
    st.dataframe(df, hide_index=True, use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("下载参数表 (CSV)", csv, "ladle_design.csv", "text/csv", use_container_width=True)

with c2:
    st.subheader("📐 设计图纸")
    H, Dt, Db = res['H'], res['Dt'], res['Db']
    hf = input_freeboard
    tw, tb = input_wall_thick, input_bottom_thick
    z_trunnion = res['z_trunnion']
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # --- 几何计算 ---
    tan_a = tan(radians(input_angle))
    out_x = [-Db/2, Db/2, Dt/2, -Dt/2]
    out_y = [0, 0, H, H]
    r_in_b = (Db/2) + tb*tan_a - tw
    r_in_t = (Dt/2) - tw
    in_x = [-r_in_b, r_in_b, r_in_t, -r_in_t]
    in_y = [tb, tb, H, H]
    h_l = H - tb - hf
    r_liq_t = (Dt/2) - hf*tan_a - tw
    liq_x = [-r_in_b, r_in_b, r_liq_t, -r_liq_t]
    liq_y = [tb, tb, tb+h_l, tb+h_l]

    # --- 绘图图层 ---
    # 1. 保温层 (黄色)
    ax.add_patch(patches.Polygon(list(zip(out_x, out_y)), closed=True, fc='#FFEC8B', ec='black', lw=2, label='保温/耐材'))
    # 2. 内腔 (白色)
    ax.add_patch(patches.Polygon(list(zip(in_x, in_y)), closed=True, fc='white', ec='black', lw=1))
    # 3. 铁水 (红色)
    if r_in_b > 0 and h_l > 0:
        ax.add_patch(patches.Polygon(list(zip(liq_x, liq_y)), closed=True, fc='#D32F2F', alpha=0.9, label='铁水'))

    # --- 专业标注 ---
    # 移除中心线代码 (按要求)
    # ax.plot([0, 0], [-400, H+400], 'k-.', lw=1, alpha=0.5) 
    
    bbox_style = dict(boxstyle='square,pad=0.2', fc='white', ec='none', alpha=0.9)
    arrow_style = dict(arrowstyle='<|-|>', lw=1.5, color='black')
    ext_line_style = dict(color='black', lw=0.5)

    # 1. 总高 & 外径
    ax.annotate("", xy=(-Dt/2 - 250, 0), xytext=(-Dt/2 - 250, H), arrowprops=arrow_style)
    ax.text(-Dt/2 - 300, H/2, f"H={H:.0f}", ha='right', va='center', fontweight='bold')
    ax.plot([-Dt/2, -Dt/2-250], [0, 0], **ext_line_style)
    ax.plot([-Dt/2, -Dt/2-250], [H, H], **ext_line_style)

    ax.annotate("", xy=(-Dt/2, H+250), xytext=(Dt/2, H+250), arrowprops=arrow_style)
    ax.text(0, H+300, f"Ф{Dt:.0f}", ha='center', va='bottom', fontweight='bold', bbox=bbox_style)
    ax.plot([-Dt/2, -Dt/2], [H, H+250], **ext_line_style)
    ax.plot([Dt/2, Dt/2], [H, H+250], **ext_line_style)

    # 2. 链式对齐标注 (右侧) --- 完美对齐
    dim_x = Dt/2 + 300 # 统一标注线位置
    
    # (1) 底厚
    ax.annotate("", xy=(dim_x, 0), xytext=(dim_x, tb), arrowprops=arrow_style)
    ax.text(dim_x + 50, tb/2, f"底厚 {tb:.0f}", va='center', ha='left', fontsize=10)
    ax.plot([Dt/2, dim_x], [0, 0], **ext_line_style)
    ax.plot([Db/2, dim_x], [tb, tb], **ext_line_style)
    
    # (2) 有效容深度
    ax.annotate("", xy=(dim_x, tb), xytext=(dim_x, tb+h_l), arrowprops=arrow_style)
    ax.text(dim_x + 50, tb + h_l/2, f"有效容深度 {h_l:.0f}", va='center', ha='left', fontsize=10, fontweight='bold', color='#D32F2F')
    ax.plot([r_liq_t, dim_x], [tb+h_l, tb+h_l], **ext_line_style)
    
    # (3) 净空
    ax.annotate("", xy=(dim_x, tb+h_l), xytext=(dim_x, H), arrowprops=arrow_style)
    ax.text(dim_x + 50, tb+h_l + hf/2, f"净空 {hf:.0f}", va='center', ha='left', fontsize=10, color='blue')
    ax.plot([Dt/2, dim_x], [H, H], **ext_line_style)

    # 3. 耳轴位置标注 (Trunnion) - 蓝色十字
    ax.plot(0, z_trunnion, marker='$\oplus$', markersize=15, color='blue') # 耳轴符号
    ax.annotate(f"耳轴中心 H={z_trunnion:.0f}", xy=(0, z_trunnion), xytext=(-Dt/3, z_trunnion), 
                arrowprops=dict(arrowstyle='->', color='blue'), color='blue', fontweight='bold', bbox=bbox_style)

    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(f"铁水包总装图 (V={input_volume}m³)", y=-0.1, fontsize=14, fontweight='bold')
    st.pyplot(fig)
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
    tan_a = tan(radians(input_angle))
    
    fig, ax = plt.subplots(figsize=(10, 8)) # 加大画布以便标注
    
    # --- 几何计算 ---
    # 外形点
    out_x = [-Db/2, Db/2, Dt/2, -Dt/2]
    out_y = [0, 0, H, H]
    # 内腔点（内衬表面）
    r_in_b = (Db/2) + tb*tan_a - tw
    r_in_t = (Dt/2) - tw
    in_x = [-r_in_b, r_in_b, r_in_t, -r_in_t]
    in_y = [tb, tb, H, H]
    # 铁水点
    h_l = H - tb - hf
    r_liq_t = (Dt/2) - hf*tan_a - tw
    liq_x = [-r_in_b, r_in_b, r_liq_t, -r_liq_t]
    liq_y = [tb, tb, tb+h_l, tb+h_l]

    # --- 绘图图层 ---
    # 1. 保温/耐材层 (黄色背景) - 画整个外形，填充黄色
    ax.add_patch(patches.Polygon(list(zip(out_x, out_y)), closed=True, fc='#FFEC8B', ec='black', lw=2, label='保温/耐材'))
    # 2. 内腔空区 (白色遮罩) - 将内腔填充白色，盖住黄色
    ax.add_patch(patches.Polygon(list(zip(in_x, in_y)), closed=True, fc='white', ec='black', lw=1))
    # 3. 铁水层 (红色填充)
    if r_in_b > 0 and h_l > 0:
        ax.add_patch(patches.Polygon(list(zip(liq_x, liq_y)), closed=True, fc='#D32F2F', alpha=0.9, label='铁水'))

    # --- 专业标注 (整齐好看) ---
    # 中心线
    ax.plot([0, 0], [-400, H+400], 'k-.', lw=1, alpha=0.5)
    
    # 样式定义
    bbox_style = dict(boxstyle='square,pad=0.2', fc='white', ec='none', alpha=0.9)
    arrow_style = dict(arrowstyle='<|-|>', lw=1.5, color='black')
    ext_line_style = dict(color='black', lw=0.5)

    # 1. 总高度 H
    ax.annotate("", xy=(-Dt/2 - 250, 0), xytext=(-Dt/2 - 250, H), arrowprops=arrow_style)
    ax.text(-Dt/2 - 300, H/2, f"H={H:.0f}", ha='right', va='center', fontweight='bold')
    ax.plot([-Dt/2, -Dt/2-250], [0, 0], **ext_line_style) # 延长线
    ax.plot([-Dt/2, -Dt/2-250], [H, H], **ext_line_style)

    # 2. 上口外径 Dt
    ax.annotate("", xy=(-Dt/2, H+250), xytext=(Dt/2, H+250), arrowprops=arrow_style)
    ax.text(0, H+300, f"Ф{Dt:.0f}", ha='center', va='bottom', fontweight='bold', bbox=bbox_style)
    ax.plot([-Dt/2, -Dt/2], [H, H+250], **ext_line_style)
    ax.plot([Dt/2, Dt/2], [H, H+250], **ext_line_style)

    # 3. 下底外径 Db
    ax.annotate("", xy=(-Db/2, -250), xytext=(Db/2, -250), arrowprops=arrow_style)
    ax.text(0, -300, f"Ф{Db:.0f}", ha='center', va='top', fontweight='bold', bbox=bbox_style)
    ax.plot([-Db/2, -Db/2], [0, -250], **ext_line_style)
    ax.plot([Db/2, Db/2], [0, -250], **ext_line_style)

    # 4. 液面与净空
    if h_l > 0:
        # 液面线
        ax.plot([-r_liq_t*1.3, r_liq_t*1.3], [tb+h_l, tb+h_l], 'r--', lw=1.5)
        ax.text(r_liq_t*1.4, tb+h_l, "液面 ▼", color='red', va='center', fontweight='bold')
        # 液深标注
        ax.annotate("", xy=(0, tb), xytext=(0, tb+h_l), arrowprops=dict(arrowstyle='<->', color='red', lw=2))
        ax.text(0, tb + h_l/2, f"液深 {h_l:.0f}", ha='center', color='white', fontweight='bold', bbox=dict(fc='#D32F2F', ec='none', alpha=0.8))
        # 净空标注
        ax.annotate("", xy=(r_liq_t, tb+h_l), xytext=(r_liq_t, H), arrowprops=dict(arrowstyle='<->', color='blue', lw=1.5))
        ax.text(r_liq_t+30, H - hf/2, f"净空 {hf:.0f}", color='blue', va='center', bbox=bbox_style)

    # 5. 厚度引出标注
    ax.annotate(f"壁厚 {tw}", xy=(Dt/2, H*0.7), xytext=(Dt/2+350, H*0.7), arrowprops=dict(arrowstyle='->'), va='center', bbox=bbox_style)
    ax.annotate(f"底厚 {tb}", xy=(Db/4, tb/2), xytext=(Db/2+350, tb/2), arrowprops=dict(arrowstyle='->'), va='center', bbox=bbox_style)

    # 图表设置
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(f"铁水包总装结构图 (有效容积 V={input_volume}m³)", y=-0.1, fontsize=14, fontweight='bold')
    # 图例优化
    legend = ax.legend(loc='upper right', frameon=True, fancybox=True, framealpha=0.9, shadow=True)
    for text in legend.get_texts():
        text.set_fontweight('bold')

    st.pyplot(fig)
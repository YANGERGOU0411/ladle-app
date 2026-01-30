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
# 1. 基础配置与字体设置
# ==========================================
st.set_page_config(
    page_title="智能铁水包设计系统", 
    layout="wide", 
    page_icon="🏭"
)

# --- 字体加载逻辑 (防乱码) ---
@st.cache_resource
def configure_fonts():
    # 优先加载目录下的 SimHei.ttf
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
        # 云端或无文件时的备选
        return ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "sans-serif"], False

font_family, is_font_success = configure_fonts()
plt.rcParams['font.sans-serif'] = font_family
plt.rcParams['axes.unicode_minus'] = False

# ==========================================
# 2. 登录验证模块
# ==========================================
# 预设账号密码
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
        st.title("🔐 智能铁水包设计系统")
        
        if is_font_success:
            st.success("✅ 系统字体加载正常")
        else:
            st.warning("⚠️ 未检测到 SimHei.ttf，图纸中文可能显示异常。")
            
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

# 如果未登录，显示登录页并停止执行
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ==========================================
# 3. 侧边栏：输入控制区
# ==========================================
with st.sidebar:
    st.title("🏭 参数设定")
    st.write(f"当前用户: **{st.session_state.user_name}**")
    
    if st.button("退出登录"):
        st.session_state.logged_in = False
        st.rerun()
    st.markdown("---")

    # --- 状态同步逻辑 (滑块与输入框联动) ---
    if 'aspect_ratio' not in st.session_state:
        st.session_state.aspect_ratio = 1.05

    def update_from_slider():
        st.session_state.aspect_ratio = st.session_state.slider_val
    def update_from_input():
        st.session_state.aspect_ratio = st.session_state.input_val

    st.subheader("1. 容量与介质")
    input_volume = st.number_input("目标有效容积 (m³)", min_value=0.1, value=4.5, step=0.1)
    input_density = st.number_input("介质密度 (t/m³)", min_value=1.0, value=7.0, step=0.1)

    st.subheader("2. 形状控制")
    st.markdown("**径高比 (直径/高度)**")
    # 联动组件
    st.slider("粗调比例", 0.5, 2.5, key='slider_val', value=st.session_state.aspect_ratio, on_change=update_from_slider)
    st.number_input("精调数值", 0.5, 2.5, key='input_val', value=st.session_state.aspect_ratio, step=0.01, on_change=update_from_input)
    
    st.subheader("3. 结构细节 (mm)")
    input_freeboard = st.number_input("净空高度 (液面到顶)", value=300, step=50)
    input_angle = st.number_input("侧壁倾角 (°)", value=5.0, step=0.5)
    input_wall_thick = st.number_input("侧壁总厚度", value=160, step=10)
    input_bottom_thick = st.number_input("底部总厚度", value=230, step=10)

# ==========================================
# 4. 核心计算引擎
# ==========================================
def solve_ladle_geometry(target_vol, density, t_wall, t_bot, freeboard, angle, ar):
    # 单位转换 mm -> m
    tw = t_wall / 1000.0
    tb = t_bot / 1000.0
    hf = freeboard / 1000.0
    tan_a = tan(radians(angle))

    # 定义求解函数：已知高度 H，计算有效容积
    def get_capacity(h_total):
        # 扣除底部和净空，得到液体高度
        h_liq = h_total - tb - hf
        if h_liq <= 0: return 0
        
        # 外壳尺寸
        r_out_top = (ar * h_total) / 2
        r_out_bot = r_out_top - h_total * tan_a
        if r_out_bot <= 0: return 0 # 锥度过大
        
        # 内衬尺寸 (液体部分)
        # 液面处的内半径
        z_liq_top = h_total - hf 
        r_in_top = (r_out_top - hf * tan_a) - tw
        
        # 底部处的内半径
        z_liq_bot = tb
        r_in_bot = (r_out_bot + tb * tan_a) - tw
        
        if r_in_bot <= 0: return 0
        
        # 圆台体积公式
        vol = (1.0/3.0) * pi * h_liq * (r_in_bot**2 + r_in_top**2 + r_in_bot*r_in_top)
        return vol

    # 二分法求解 H
    low, high = 0.1, 10.0
    for _ in range(50):
        mid = (low + high) / 2
        if get_capacity(mid) < target_vol:
            low = mid
        else:
            high = mid
            
    H = high
    H_mm = H * 1000
    
    # 计算最终几何参数
    D_top_out = H * ar
    D_bot_out = D_top_out - 2 * H * tan_a
    
    h_liquid = H - tb - hf
    capacity_ton = target_vol * density
    
    # 结果字典
    return {
        "H_total": H_mm,
        "D_top_out": D_top_out * 1000, # m -> mm
        "D_bot_out": D_bot_out * 1000,
        "h_liquid": h_liquid * 1000,
        "vol_real": target_vol,
        "cap_ton": capacity_ton,
        "trunnion_h": H_mm * 0.65, # 耳轴高度估算
        "params": (t_wall, t_bot, freeboard, angle, ar)
    }

# 执行计算
res = solve_ladle_geometry(
    input_volume, input_density, 
    input_wall_thick, input_bottom_thick, input_freeboard, 
    input_angle, st.session_state.aspect_ratio
)

# ==========================================
# 5. 主界面：显示与绘图
# ==========================================
st.title("🏭 智能铁水包设计报告")
st.markdown("---")

col_res, col_plot = st.columns([1, 1.5])

with col_res:
    st.subheader("📊 设计指标")
    
    # 关键数据卡片
    k1, k2 = st.columns(2)
    k1.metric("总高度 H", f"{res['H_total']:.0f} mm")
    k2.metric("上口外径", f"{res['D_top_out']:.0f} mm")
    
    k3, k4 = st.columns(2)
    k3.metric("计算载重", f"{res['cap_ton']:.2f} t")
    k4.metric("有效容积", f"{res['vol_real']:.2f} m³")
    
    st.markdown("#### 📏 详细规格表")
    
    # 构造表格数据
    spec_data = [
        {"类别": "几何尺寸", "项目": "总高度 (H)", "数值": f"{res['H_total']:.0f}", "单位": "mm"},
        {"类别": "几何尺寸", "项目": "上口外径", "数值": f"{res['D_top_out']:.0f}", "单位": "mm"},
        {"类别": "几何尺寸", "项目": "下底外径", "数值": f"{res['D_bot_out']:.0f}", "单位": "mm"},
        {"类别": "结构参数", "项目": "侧壁倾角", "数值": f"{input_angle:.1f}", "单位": "°"},
        {"类别": "结构参数", "项目": "侧壁厚度", "数值": f"{input_wall_thick}", "单位": "mm"},
        {"类别": "结构参数", "项目": "底部厚度", "数值": f"{input_bottom_thick}", "单位": "mm"},
        {"类别": "工艺参数", "项目": "净空高度", "数值": f"{input_freeboard}", "单位": "mm"},
        {"类别": "工艺参数", "项目": "液面深度", "数值": f"{res['h_liquid']:.0f}", "单位": "mm"},
        {"类别": "设计指标", "项目": "径高比", "数值": f"{st.session_state.aspect_ratio:.2f}", "单位": "-"},
    ]
    
    df_spec = pd.DataFrame(spec_data)
    st.dataframe(
        df_spec, 
        hide_index=True, 
        use_container_width=True,
        column_order=["类别", "项目", "数值", "单位"]
    )
    
    # 导出按钮
    csv = df_spec.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下载规格书 (CSV)",
        data=csv,
        file_name=f"Ladle_Design_{input_volume}m3.csv",
        mime="text/csv",
        use_container_width=True
    )

with col_plot:
    st.subheader("📐 结构设计图")
    
    H = res['H_total']
    Dt = res['D_top_out']
    Db = res['D_bot_out']
    tw = input_wall_thick
    tb = input_bottom_thick
    hf = input_freeboard
    
    fig, ax = plt.subplots(figsize=(8, 7))
    
    # 1. 画外壳 (梯形)
    shell_x = [-Db/2, Db/2, Dt/2, -Dt/2]
    shell_y = [0, 0, H, H]
    poly_shell = patches.Polygon(list(zip(shell_x, shell_y)), closed=True, fc='#F3F4F6', ec='#374151', lw=3, label='外壳')
    ax.add_patch(poly_shell)
    
    # 2. 画内衬/液体区域
    # 计算内部液面的上宽和下宽
    # 利用相似三角形原理或角度
    tan_a = tan(radians(input_angle))
    
    # 液体底部 (z = tb)
    r_liq_bot = (Db/2) + tb * tan_a - tw
    # 液体顶部 (z = H - hf)
    r_liq_top = (Dt/2) - hf * tan_a - tw
    
    h_liq = H - tb - hf
    
    liq_x = [-r_liq_bot, r_liq_bot, r_liq_top, -r_liq_top]
    liq_y = [tb, tb, tb+h_liq, tb+h_liq]
    
    if r_liq_bot > 0:
        poly_liq = patches.Polygon(list(zip(liq_x, liq_y)), closed=True, fc='#F59E0B', alpha=0.6, label='铁水/渣')
        ax.add_patch(poly_liq)
        
        # 标注液面
        ax.plot([-r_liq_top*1.2, r_liq_top*1.2], [tb+h_liq, tb+h_liq], 'r--', lw=1)
        ax.text(r_liq_top + 100, tb+h_liq, f"液面 ▼", color='red', va='center')
        
        # 标注液深
        ax.annotate("", xy=(0, tb), xytext=(0, tb+h_liq), arrowprops=dict(arrowstyle='<->', color='red'))
        ax.text(0, tb + h_liq/2, f"液深 {h_liq:.0f}", ha='center', color='red', fontweight='bold')

    # 3. 标注尺寸
    # 总高
    ax.annotate("", xy=(-Dt/2 - 200, 0), xytext=(-Dt/2 - 200, H), arrowprops=dict(arrowstyle='<->'))
    ax.text(-Dt/2 - 300, H/2, f"H={H:.0f}", ha='right', va='center')
    
    # 外径
    ax.annotate("", xy=(-Dt/2, H+150), xytext=(Dt/2, H+150), arrowprops=dict(arrowstyle='<->'))
    ax.text(0, H+200, f"Ф{Dt:.0f}", ha='center', va='bottom')
    
    # 净空
    ax.annotate("", xy=(r_liq_top, tb+h_liq), xytext=(r_liq_top, H), arrowprops=dict(arrowstyle='<->', color='blue'))
    ax.text(r_liq_top + 50, H - hf/2, f"净空 {hf:.0f}", color='blue', va='center')

    # 耳轴示意
    tr_h = res['trunnion_h']
    ax.plot([-Dt/2*1.1, Dt/2*1.1], [tr_h, tr_h], color='blue', ls='-.', alpha=0.5)
    ax.text(Dt/2*1.15, tr_h, "耳轴中心", color='blue', va='center', fontsize=9)

    ax.set_aspect('equal')
    ax.axis('off') # 隐藏坐标轴
    ax.set_title(f"设计图纸 (V={input_volume}m³)", fontsize=14)
    ax.legend(loc='lower right')
    
    st.pyplot(fig)
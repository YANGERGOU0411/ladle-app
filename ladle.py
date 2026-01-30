import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
from io import BytesIO 
import os
import time

# --- 页面配置 ---
st.set_page_config(page_title="智能铁水包设计平台", layout="wide", page_icon="🔒")

# --- 0. 预设账号密码库 (你可以自己修改这里) ---
# 格式： "用户名": "密码"
USERS = {
    "admin": "888888",     # 管理员
    "user1": "123456",     # 同事A
    "client": "vip2026"    # 客户
}

# --- 初始化登录状态 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

# --- 登录函数 ---
def login_page():
    st.title("🔐 铁水包设计系统 - 用户登录")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.info("请输入授权账号和密码进入系统")
        username_input = st.text_input("用户名")
        password_input = st.text_input("密码", type="password")
        
        login_btn = st.button("登 录", type="primary", use_container_width=True)

        if login_btn:
            if username_input in USERS and USERS[username_input] == password_input:
                st.session_state.logged_in = True
                st.session_state.user_name = username_input
                st.success("登录成功！正在跳转...")
                time.sleep(0.5)
                st.rerun() # 刷新页面进入系统
            else:
                st.error("用户名或密码错误！")

# ==========================================
#  如果不处于登录状态，只显示登录页，不执行后面代码
# ==========================================
if not st.session_state.logged_in:
    login_page()
    st.stop() # 停止执行后续代码

# ==========================================
#  以下是登录成功后才显示的【主程序】
# ==========================================

# --- 侧边栏显示用户信息 ---
with st.sidebar:
    st.write(f"👤 当前用户: **{st.session_state.user_name}**")
    if st.button("退出登录"):
        st.session_state.logged_in = False
        st.rerun()
    st.markdown("---")

# --- 解决字体 ---
try:
    if os.path.exists("SimHei.ttf"):
        fm.fontManager.addfont("SimHei.ttf")
        plt.rcParams['font.sans-serif'] = ['SimHei']
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
except:
    pass
plt.rcParams['axes.unicode_minus'] = False

# --- 状态同步 ---
if 'aspect_ratio' not in st.session_state:
    st.session_state.aspect_ratio = 1.01

def update_slider():
    st.session_state.aspect_ratio = st.session_state.slider_val

def update_input():
    st.session_state.aspect_ratio = st.session_state.input_val

# --- 核心计算函数 ---
def solve_ladle_geometry(target_vol_m3, density, t_wall_mm, t_bottom_mm, freeboard_mm, angle_degree, aspect_ratio):
    t_w = t_wall_mm / 1000.0
    t_b = t_bottom_mm / 1000.0
    h_f = freeboard_mm / 1000.0
    tan_a = np.tan(np.deg2rad(angle_degree))

    def calculate_capacity_by_H(h_guess):
        R_out_top = (aspect_ratio / 2) * h_guess
        R_out_bot = R_out_top - h_guess * tan_a
        if R_out_bot <= 0: return 0
        h_liquid = h_guess - t_b - h_f
        if h_liquid <= 0: return 0
        z_liq_bot = t_b
        z_liq_top = t_b + h_liquid
        R_out_at_liq_bot = R_out_bot + z_liq_bot * tan_a
        r_in_liq_bot = R_out_at_liq_bot - t_w
        R_out_at_liq_top = R_out_bot + z_liq_top * tan_a
        r_in_liq_top = R_out_at_liq_top - t_w
        if r_in_liq_bot <= 0 or r_in_liq_top <= 0: return 0 
        vol = (1.0/3.0) * np.pi * h_liquid * (r_in_liq_bot**2 + r_in_liq_top**2 + r_in_liq_bot*r_in_liq_top)
        return vol

    low, high = 0.5, 15.0
    for _ in range(100):
        mid = (low + high) / 2
        vol_calc = calculate_capacity_by_H(mid)
        if vol_calc < target_vol_m3: low = mid 
        else: high = mid 
            
    best_H = (low + high) / 2
    H = best_H
    H_mm = H * 1000
    R_out_top = (aspect_ratio / 2) * H
    R_out_bot = R_out_top - H * tan_a
    h_liquid_m = H - t_b - h_f
    h_liquid_mm = h_liquid_m * 1000
    z_liq_top = t_b + h_liquid_m
    r_in_bot = (R_out_bot + t_b * tan_a) - t_w
    r_in_top_rim = R_out_top - t_w
    r_surf = (R_out_bot + z_liq_top * tan_a) - t_w
    capacity_ton = target_vol_m3 * density

    return {
        "volume_m3": target_vol_m3,
        "density": density,
        "capacity_ton": round(capacity_ton, 2),
        "H_total": round(H_mm, 0),
        "Dia_top_out": round(R_out_top * 2 * 1000, 0),
        "Dia_bot_out": round(R_out_bot * 2 * 1000, 0),
        "h_liquid": round(h_liquid_mm, 0),
        "dia_liquid_surf": round(r_surf * 2 * 1000, 0),
        "r_in_bot": r_in_bot * 1000,
        "r_in_top": r_in_top_rim * 1000,
        "r_surf": r_surf * 1000,
        "h_trunnion": round(0.707 * H_mm, 0),
        "wall_thickness": t_wall_mm,
        "bottom_thickness": t_bottom_mm,
        "freeboard": freeboard_mm,
        "shell_angle": angle_degree,
        "aspect_ratio": aspect_ratio
    }

# --- 绘图函数 ---
def plot_ladle_diagram(params):
    H = params['H_total']
    D_top = params['Dia_top_out']
    R_top = D_top / 2
    D_bot = params['Dia_bot_out']
    R_bot = D_bot / 2
    
    fig, ax = plt.subplots(figsize=(12, 10))
    shell_x = [0, R_bot, R_top, 0]
    shell_y = [0, 0, H, H]
    ax.add_patch(patches.Polygon(xy=list(zip(shell_x, shell_y)), closed=True, fill=False, edgecolor='black', linewidth=2.5))
    ax.add_patch(patches.Polygon(xy=list(zip([-x for x in shell_x], shell_y)), closed=True, fill=False, edgecolor='black', linewidth=2.5))
    t_b = params['bottom_thickness']
    r_in_bot = params['r_in_bot']
    r_in_top = params['r_in_top']
    inner_x = [0, r_in_bot, r_in_top, 0]
    inner_y = [t_b, t_b, H, H]
    ax.add_patch(patches.Polygon(xy=list(zip(inner_x, inner_y)), closed=True, facecolor='#E0E0E0', edgecolor='gray', hatch='///'))
    ax.add_patch(patches.Polygon(xy=list(zip([-x for x in inner_x], inner_y)), closed=True, facecolor='#E0E0E0', edgecolor='gray', hatch='///'))
    h_liq = params['h_liquid']
    level_y = t_b + h_liq
    if level_y > H: level_y = H 
    r_surf = params['r_surf']
    liq_x = [0, r_in_bot, r_surf, 0]
    liq_y = [t_b, t_b, level_y, level_y]
    ax.add_patch(patches.Polygon(xy=list(zip(liq_x, liq_y)), closed=True, facecolor='#FFA500', alpha=0.7))
    ax.add_patch(patches.Polygon(xy=list(zip([-x for x in liq_x], liq_y)), closed=True, facecolor='#FFA500', alpha=0.7))

    bbox_white = dict(boxstyle='square,pad=0.2', fc='white', ec='none', alpha=0.9)
    anno_x = -R_top * 1.3
    ax.annotate("", xy=(anno_x, 0), xytext=(anno_x, H), arrowprops=dict(arrowstyle='<->', lw=1.5, color='black'))
    ax.plot([anno_x-100, anno_x+100], [0, 0], 'k-', lw=1)
    ax.plot([anno_x-100, anno_x+100], [H, H], 'k-', lw=1)
    ax.text(anno_x - 150, H/2, f"H={H:.0f}", va='center', ha='right', fontsize=14, fontweight='bold')
    
    ax.annotate("", xy=(0, t_b), xytext=(0, level_y), arrowprops=dict(arrowstyle='<->', lw=1.5, color='red'))
    ax.text(0, level_y/2 + t_b, f"液深\n{h_liq:.0f}", ha='center', va='center', color='red', fontsize=11, fontweight='bold', bbox=bbox_white)
    
    freeboard = params['freeboard']
    fb_x = r_surf * 0.6 
    ax.annotate("", xy=(fb_x, level_y), xytext=(fb_x, H), arrowprops=dict(arrowstyle='<->', lw=1.5, color='red'))
    ax.text(fb_x, (level_y + H)/2, f"净空\n{freeboard:.0f}", ha='center', va='center', color='red', fontsize=10, bbox=bbox_white)
    
    ax.annotate(f"Ф{D_top:.0f}", xy=(0, H), xytext=(0, H + 350), arrowprops=dict(arrowstyle='-', color='gray'), ha='center', fontsize=12, fontweight='bold', bbox=bbox_white)
    ax.annotate("", xy=(-R_top, H+250), xytext=(R_top, H+250), arrowprops=dict(arrowstyle='<|-|>', lw=1.5))
    ax.annotate(f"Ф{D_bot:.0f}", xy=(0, 0), xytext=(0, -350), arrowprops=dict(arrowstyle='-', color='gray'), ha='center', va='top', fontsize=12, fontweight='bold', bbox=bbox_white)
    ax.annotate("", xy=(-R_bot, -250), xytext=(R_bot, -250), arrowprops=dict(arrowstyle='<|-|>', lw=1.5))
    trunnion_y = params['h_trunnion']
    ax.plot([-R_top*1.2, R_top*1.2], [trunnion_y, trunnion_y], color='blue', linestyle='-.', linewidth=1)
    ax.text(R_top*1.25, trunnion_y, f"耳轴 EL+{trunnion_y}", color='blue', va='center', fontsize=10, bbox=bbox_white)
    ax.set_title(f"铁水包方案 (V={params['volume_m3']} $m^3$, 径高比={params['aspect_ratio']})", fontsize=18, pad=25)
    ax.set_aspect('equal')
    ax.set_xlim(-R_top*2.0, R_top*2.0) 
    ax.set_ylim(-500, H + 500)
    plt.grid(True, linestyle='--', alpha=0.3)
    return fig

# --- 主界面 ---
st.title("🏭 智能铁水包/渣罐 设计工具")
st.markdown("---")

col_input, col_display = st.columns([1, 2.5])

with col_input:
    st.subheader("1. 基础与形状")
    input_volume = st.number_input("目标有效容积 (m³)", min_value=0.1, value=4.5, step=0.1)
    input_density = st.number_input("介质密度 (t/m³)", min_value=1.0, value=7.0, step=0.1)
    st.markdown("---")
    st.markdown("**径高比 (直径/高度)**")
    col_slide, col_text = st.columns([2, 1])
    with col_slide: st.slider("粗调", 0.5, 2.5, key='slider_val', on_change=update_slider)
    with col_text: st.number_input("精调", 0.5, 2.5, step=0.01, key='input_val', on_change=update_input)
    st.caption(f"当前生效值: {st.session_state.aspect_ratio}")
    st.markdown("---")
    st.subheader("2. 结构参数 (mm)")
    input_freeboard = st.number_input("净空高度 (液面到顶部)", value=300, step=50)
    input_angle = st.number_input("外壳侧壁倾角 (°)", value=5.0, step=0.5)
    input_wall_thick = st.number_input("侧壁打结料 (mm)", value=160, step=10)
    input_bottom_thick = st.number_input("底部打结料 (mm)", value=230, step=10)

data = solve_ladle_geometry(input_volume, input_density, input_wall_thick, input_bottom_thick, input_freeboard, input_angle, st.session_state.aspect_ratio)

with col_display:
    if data['H_total'] == 0:
        st.error("❌ 形状参数不合理，请调整参数。")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总高度 H", f"{data['H_total']:.0f} mm")
        c2.metric("计算载重", f"{data['capacity_ton']} t")
        c3.metric("上口外径", f"{data['Dia_top_out']:.0f} mm")
        c4.metric("净空高度", f"{data['freeboard']:.0f} mm")
        
        fig = plot_ladle_diagram(data)
        st.pyplot(fig)
        
        # --- 下载功能区 ---
        st.markdown("### 📥 导出设计")
        col_down1, col_down2 = st.columns(2)
        
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=150)
        with col_down1:
            st.download_button("📷 下载设计图纸 (PNG)", data=buf.getvalue(), file_name=f"铁水包图纸_{data['volume_m3']}m3.png", mime="image/png")

        spec_data = [
            {"类别": "几何尺寸", "名称": "总高度 (H)", "数值": f"{data['H_total']:.0f}", "单位": "mm"},
            {"类别": "几何尺寸", "名称": "上口外径", "数值": f"{data['Dia_top_out']:.0f}", "单位": "mm"},
            {"类别": "几何尺寸", "名称": "下底外径", "数值": f"{data['Dia_bot_out']:.0f}", "单位": "mm"},
            {"类别": "结构参数", "名称": "净空高度", "数值": f"{data['freeboard']:.0f}", "单位": "mm"},
            {"类别": "结构参数", "名称": "侧壁厚度", "数值": f"{data['wall_thickness']:.0f}", "单位": "mm"},
            {"类别": "结构参数", "名称": "底部厚度", "数值": f"{data['bottom_thickness']:.0f}", "单位": "mm"},
            {"类别": "结构参数", "名称": "侧壁倾角", "数值": f"{data['shell_angle']:.1f}", "单位": "°"},
            {"类别": "工艺参数", "名称": "液面深度", "数值": f"{data['h_liquid']:.0f}", "单位": "mm"},
            {"类别": "设计指标", "名称": "径高比", "数值": f"{data['aspect_ratio']:.2f}", "单位": "-"},
            {"类别": "设计指标", "名称": "有效容积", "数值": f"{data['volume_m3']:.2f}", "单位": "m³"},
        ]
        df_spec = pd.DataFrame(spec_data)
        csv = df_spec.to_csv(index=False).encode('utf-8-sig')
        with col_down2:
            st.download_button("📊 下载规格书 (Excel/CSV)", data=csv, file_name=f"铁水包参数_{data['volume_m3']}m3.csv", mime="text/csv")

        st.dataframe(df_spec, hide_index=True, use_container_width=True, column_order=["类别", "名称", "数值", "单位"])
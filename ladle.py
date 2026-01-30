import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
from io import BytesIO
import os
import time

# ==========================================
# 1. 页面配置与字体管理
# ==========================================
st.set_page_config(page_title="冶金设备综合计算平台", layout="wide", page_icon="🏭")

# --- 字体加载 (带自动诊断) ---
@st.cache_resource
def configure_fonts():
    # 优先寻找上传的字体文件
    font_files = ["SimHei.ttf", "simhei.ttf"] 
    found_font = None
    for f in font_files:
        if os.path.exists(f):
            found_font = f
            break
    
    if found_font:
        fm.fontManager.addfont(found_font)
        # 获取字体实际名称
        prop = fm.FontProperties(fname=found_font)
        return prop.get_name(), True
    else:
        # 没找到，使用备用列表
        return "sans-serif", False

font_family, is_font_success = configure_fonts()

# 全局设置 Matplotlib
plt.rcParams['font.sans-serif'] = [font_family, 'Microsoft YaHei', 'Arial Unicode MS', 'SimHei', 'DejaVu Sans']
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
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("🔐 冶金设备综合计算平台")
        
        if is_font_success:
            st.success(f"✅ 系统字体加载正常")
        else:
            st.warning("⚠️ 未检测到中文字体文件 (SimHei.ttf)，图表文字可能无法显示。")
            
        st.info("包含模块：1. 矿热电炉参数计算  2. 铁水包结构设计")
        
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submit = st.form_submit_button("登 录", type="primary", use_container_width=True)
            
            if submit:
                if username in USERS and USERS[username] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_name = username
                    st.rerun()
                else:
                    st.error("账号或密码错误")

if not st.session_state.logged_in:
    login_page()
    st.stop()

# ==========================================
# 3. 主界面导航
# ==========================================
with st.sidebar:
    st.header("功能导航")
    module = st.radio("选择设计模块:", ["🔥 矿热炉参数计算", "🏭 铁水包结构设计"], index=0)
    
    st.markdown("---")
    st.write(f"👤 操作员: **{st.session_state.user_name}**")
    if st.button("退出登录"):
        st.session_state.logged_in = False
        st.rerun()

# ==========================================
# 4. 模块一：矿热炉参数计算 (Excel逻辑复刻)
# ==========================================
if module == "🔥 矿热炉参数计算":
    st.title("🔥 矿热电炉参数计算器")
    st.markdown("基于 **容量立方根 ($P^{1/3}$)** 的经验系数法，集成一次侧供电参数。")

    # --- A. 内置数据字典 (源自您的Excel文件) ---
    # 格式: [Ke范围, J范围, Ky范围, Ki范围, Kh范围] -> 默认值取中间
    ALLOY_DB = {
        "硅锰 (SiMn)":     {"Ke": 6.3,  "J": 5.5, "Ky": 2.7,  "Ki": 6.4,  "Kh": 2.5, "range_Ke": (6.2, 6.6)},
        "高碳铬铁 (FeCr)": {"Ke": 6.8,  "J": 5.7, "Ky": 2.65, "Ki": 6.3,  "Kh": 2.6, "range_Ke": (6.0, 7.0)},
        "镍铁 (FeNi-RKEF)":{"Ke": 12.0, "J": 4.0, "Ky": 3.6,  "Ki": 10.0, "Kh": 2.9, "range_Ke": (11.0, 13.0)},
        "硅铁75 (FeSi75)": {"Ke": 6.8,  "J": 6.5, "Ky": 2.25, "Ki": 5.8,  "Kh": 2.2, "range_Ke": (6.0, 7.5)},
        "电石 (CaC2)":     {"Ke": 6.5,  "J": 7.0, "Ky": 2.7,  "Ki": 6.4,  "Kh": 2.2, "range_Ke": (6.0, 7.0)},
        "工业硅 (Si)":     {"Ke": 7.5,  "J": 6.0, "Ky": 2.4,  "Ki": 6.0,  "Kh": 2.3, "range_Ke": (7.0, 8.0)},
        "自定义":          {"Ke": 6.5,  "J": 5.5, "Ky": 2.7,  "Ki": 6.5,  "Kh": 2.5, "range_Ke": (1.0, 20.0)}
    }

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("1. 供电与容量设定")
        alloy = st.selectbox("冶炼品种", list(ALLOY_DB.keys()))
        
        # 新增：一次侧参数输入
        c1_in, c2_in = st.columns(2)
        with c1_in:
            capacity_mva = st.number_input("变压器容量 (MVA)", value=33.0, step=0.5, min_value=1.0)
        with c2_in:
            # 提供常用电压选择，也允许手填
            u1_kv = st.selectbox("一次电压 U₁ (kV)", [110, 35, 10, 6, 220, 10.5], index=1, help="高压侧供电电压")
        
        # 自动加载默认系数
        defaults = ALLOY_DB[alloy]
        st.markdown("---")
        st.caption("🔍 经验系数微调")
        
        ke = st.slider(f"电压系数 Ke", min_value=1.0, max_value=20.0, value=defaults['Ke'], step=0.1, help="决定二次电压高低，硅锰约6.3，镍铁约12")
        j_val = st.slider(f"电流密度 J (A/cm²)", min_value=1.0, max_value=10.0, value=defaults['J'], step=0.1)
        ky = st.number_input(f"极心圆系数 Ky", value=defaults['Ky'], step=0.05)
        ki = st.number_input(f"炉膛内径系数 Ki", value=defaults['Ki'], step=0.1)
        kh = st.number_input(f"炉膛深度系数 Kh", value=defaults['Kh'], step=0.1)
        
        # 额外输入：炉衬厚度 (用于估算外壳)
        lining_thick = st.number_input("平均炉衬厚度 (mm)", value=1200, step=100, help="用于估算炉壳尺寸")

    # --- B. 核心计算 ---
    # 1. 变压器容量 kVA
    p_kva = capacity_mva * 1000
    
    # 2. 一次电流 I1 (A) = P / (sqrt(3) * U1)
    # U1 单位转换成 V: u1_kv * 1000
    i1 = (p_kva * 1000) / (1.73205 * (u1_kv * 1000))
    
    # 3. 二次电压 U2 = Ke * (P^1/3)
    u2 = ke * (p_kva ** (1/3))
    
    # 4. 二次电流 I2 = P / (sqrt(3) * U2)
    i2 = p_kva * 1000 / (1.73205 * u2)
    
    # 5. 电极直径 d = sqrt( I2 / (0.7854 * J) )
    # 先算面积 cm2
    elec_area_cm2 = i2 / j_val
    de_cm = np.sqrt(elec_area_cm2 / 0.7854)
    de_mm = de_cm * 10
    
    # 6. 炉体尺寸
    dc_mm = ky * de_mm  # 极心圆
    di_mm = ki * de_mm  # 炉膛内径
    hh_mm = kh * de_mm  # 炉膛深度
    
    # 7. 估算炉壳
    shell_id_mm = di_mm + 2 * lining_thick
    shell_h_mm = hh_mm + 2000 # 估算高度：深度+炉底+超高

    with col2:
        st.subheader("2. 计算结果分析")
        
        # 关键指标展示 (第一行：一次侧)
        st.markdown("**⚡ 一次侧参数 (High Voltage)**")
        k1_1, k1_2, k1_3 = st.columns(3)
        k1_1.metric("变压器容量", f"{capacity_mva} MVA")
        k1_2.metric("一次电压 U₁", f"{u1_kv} kV")
        k1_3.metric("一次电流 I₁", f"{i1:.1f} A")
        
        st.divider()
        
        # 关键指标展示 (第二行：二次侧)
        st.markdown("**🔥 二次侧与炉体 (Furnace)**")
        k2_1, k2_2, k2_3, k2_4 = st.columns(4)
        k2_1.metric("二次电压 U₂", f"{u2:.1f} V")
        k2_2.metric("二次电流 I₂", f"{i2/1000:.1f} kA")
        k2_3.metric("电极直径 d", f"{de_mm:.0f} mm")
        k2_4.metric("极心圆直径", f"{dc_mm:.0f} mm")
        
        st.info(f"💡 根据 **{alloy}** 经验系数计算：该容量下的炉膛内径约为 **{di_mm/1000:.1f}米**，建议炉壳内径 **{shell_id_mm/1000:.1f}米**。")

        # 绘图
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # 画炉壳
        rect_shell = patches.Rectangle((-shell_id_mm/2, 0), shell_id_mm, shell_h_mm, linewidth=3, edgecolor='#333333', facecolor='none', label='炉壳')
        ax.add_patch(rect_shell)
        
        # 画炉膛 (假设炉底厚度1500)
        bottom_thick = 1500
        rect_hearth = patches.Rectangle((-di_mm/2, bottom_thick), di_mm, hh_mm, linewidth=2, edgecolor='red', facecolor='#FFD700', alpha=0.3, label='炉膛(熔池)')
        ax.add_patch(rect_hearth)
        
        # 画电极 (画两根示意)
        elec_w = de_mm
        elec_h = shell_h_mm * 0.8
        # 左电极 (极心圆位置 -dc/2)
        rect_el1 = patches.Rectangle((-dc_mm/2 - elec_w/2, shell_h_mm/2), elec_w, elec_h, color='#555555', label='电极')
        ax.add_patch(rect_el1)
        # 右电极
        rect_el2 = patches.Rectangle((dc_mm/2 - elec_w/2, shell_h_mm/2), elec_w, elec_h, color='#555555')
        ax.add_patch(rect_el2)
        
        # 标注
        bbox_props = dict(boxstyle="square,pad=0.3", fc="white", ec="black", lw=0.5, alpha=0.8)
        
        # 标注内径
        ax.annotate(f"炉膛内径 {di_mm:.0f}", xy=(0, bottom_thick + hh_mm/2), ha='center', fontsize=12, bbox=bbox_props)
        # 标注极心圆
        ax.annotate(f"极心圆 {dc_mm:.0f}", xy=(0, shell_h_mm - 500), xytext=(0, shell_h_mm + 500), 
                    arrowprops=dict(arrowstyle='-'), ha='center', color='blue', fontsize=12, bbox=bbox_props)
        ax.plot([-dc_mm/2, dc_mm/2], [shell_h_mm + 200, shell_h_mm + 200], color='blue', marker='|')

        ax.set_aspect('equal')
        ax.axis('off') # 不显示坐标轴
        ax.set_title(f"{capacity_mva}MVA {alloy}矿热炉 结构示意图", fontsize=14)
        plt.legend(loc='upper right')
        st.pyplot(fig)
        
        # 导出表格
        res_data = [
            {"参数名称": "变压器容量", "数值": capacity_mva, "单位": "MVA"},
            {"参数名称": "一次电压 U1", "数值": u1_kv, "单位": "kV"},
            {"参数名称": "一次电流 I1", "数值": round(i1, 1), "单位": "A"},
            {"参数名称": "二次电压 U2", "数值": round(u2, 1), "单位": "V"},
            {"参数名称": "二次电流 I2", "数值": round(i2, 1), "单位": "A"},
            {"参数名称": "电极直径 d", "数值": round(de_mm, 0), "单位": "mm"},
            {"参数名称": "极心圆直径 Dc", "数值": round(dc_mm, 0), "单位": "mm"},
            {"参数名称": "炉膛内径 Di", "数值": round(di_mm, 0), "单位": "mm"},
            {"参数名称": "炉膛深度 Hh", "数值": round(hh_mm, 0), "单位": "mm"},
            {"参数名称": "电流密度 J", "数值": j_val, "单位": "A/cm²"},
            {"参数名称": "电压系数 Ke", "数值": ke, "单位": "-"},
        ]
        df_res = pd.DataFrame(res_data)
        csv = df_res.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📊 下载计算书 (CSV)", csv, f"矿热炉参数_{capacity_mva}MVA.csv")

# ==========================================
# 5. 模块二：铁水包设计 (原有功能)
# ==========================================
elif module == "🏭 铁水包结构设计":
    
    # [这里完全保留您之前的铁水包代码逻辑]
    if 'aspect_ratio' not in st.session_state:
        st.session_state.aspect_ratio = 1.01

    def update_slider():
        st.session_state.aspect_ratio = st.session_state.slider_val
    def update_input():
        st.session_state.aspect_ratio = st.session_state.input_val

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
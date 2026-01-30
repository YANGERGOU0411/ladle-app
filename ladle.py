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
        return "sans-serif", False

font_family, is_font_success = configure_fonts()

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
            st.warning("⚠️ 未检测到中文字体文件 (SimHei.ttf)，建议上传以修复显示。")
        st.info("包含模块：1. 矿热电炉参数计算 (带圆整修正)  2. 铁水包结构设计")
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
# 4. 模块一：矿热炉参数计算 (智能圆整版)
# ==========================================
if module == "🔥 矿热炉参数计算":
    st.title("🔥 矿热电炉参数计算器")
    st.markdown("含 **理论计算** 与 **工程圆整** 双向联动系统。")

    # --- A. 数据字典 ---
    ALLOY_DB = {
        "硅锰 (SiMn)":     {"Ke": 6.3,  "J": 5.5, "Ky": 2.7,  "Ki": 6.4,  "Kh": 2.5},
        "高碳铬铁 (FeCr)": {"Ke": 6.8,  "J": 5.7, "Ky": 2.65, "Ki": 6.3,  "Kh": 2.6},
        "镍铁 (FeNi-RKEF)":{"Ke": 12.0, "J": 4.0, "Ky": 3.6,  "Ki": 10.0, "Kh": 2.9},
        "硅铁75 (FeSi75)": {"Ke": 6.8,  "J": 6.5, "Ky": 2.25, "Ki": 5.8,  "Kh": 2.2},
        "电石 (CaC2)":     {"Ke": 6.5,  "J": 7.0, "Ky": 2.7,  "Ki": 6.4,  "Kh": 2.2},
        "工业硅 (Si)":     {"Ke": 7.5,  "J": 6.0, "Ky": 2.4,  "Ki": 6.0,  "Kh": 2.3},
        "自定义":          {"Ke": 6.5,  "J": 5.5, "Ky": 2.7,  "Ki": 6.5,  "Kh": 2.5}
    }

    # --- B. 状态初始化与回调函数 ---
    # 这里的逻辑是：当基础参数改变时，强制刷新“圆整值”为新的理论值
    if 'needs_recalc' not in st.session_state:
        st.session_state.needs_recalc = True

    def trigger_recalc():
        st.session_state.needs_recalc = True

    # --- C. 输入区域 ---
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("1. 基础参数输入")
        alloy = st.selectbox("冶炼品种", list(ALLOY_DB.keys()), on_change=trigger_recalc)
        
        c1_in, c2_in = st.columns(2)
        with c1_in:
            capacity_mva = st.number_input("变压器容量 (MVA)", value=33.0, step=0.5, min_value=1.0, on_change=trigger_recalc)
        with c2_in:
            u1_kv = st.selectbox("一次电压 U₁ (kV)", [110, 35, 10, 6, 220, 10.5], index=1, on_change=trigger_recalc)
        
        defaults = ALLOY_DB[alloy]
        
        st.subheader("2. 导电系统配置")
        tile_num = st.number_input("单相铜瓦数量 (块)", min_value=1, max_value=20, value=8, step=1)
        cc1, cc2 = st.columns(2)
        with cc1:
            tube_d = st.selectbox("铜管外径 Φ (mm)", [50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100], index=4)
        with cc2:
            tube_t = st.selectbox("铜管壁厚 (mm)", [10, 12.5, 15, 17.5, 20], index=1)
        tube_num = tile_num * 2

        st.subheader("3. 经验系数微调")
        ke_val = st.slider("电压系数 Ke", 1.0, 20.0, defaults['Ke'], 0.1, on_change=trigger_recalc)
        j_val = st.slider("电流密度 J (A/cm²)", 1.0, 10.0, defaults['J'], 0.1, on_change=trigger_recalc)
        ky_val = st.number_input("极心圆系数 Ky", value=defaults['Ky'], step=0.05, on_change=trigger_recalc)
        ki_val = st.number_input("炉膛内径系数 Ki", value=defaults['Ki'], step=0.1, on_change=trigger_recalc)
        kh_val = st.number_input("炉膛深度系数 Kh", value=defaults['Kh'], step=0.1, on_change=trigger_recalc)
        lining_thick = st.number_input("平均炉衬厚度 (mm)", value=1200, step=100, on_change=trigger_recalc)

    # --- D. 理论计算 (实时) ---
    p_kva = capacity_mva * 1000
    i1_theo = (p_kva * 1000) / (1.73205 * (u1_kv * 1000))
    u2_theo = ke_val * (p_kva ** (1/3))
    i2_theo = p_kva * 1000 / (1.73205 * u2_theo)
    
    elec_area_theo = i2_theo / j_val
    de_theo_mm = np.sqrt(elec_area_theo / 0.7854) * 10
    
    dc_theo_mm = ky_val * de_theo_mm
    di_theo_mm = ki_val * de_theo_mm
    hh_theo_mm = kh_val * de_theo_mm
    shell_id_theo_mm = di_theo_mm + 2 * lining_thick
    shell_h_theo_mm = hh_theo_mm + 2000

    # --- E. 智能圆整逻辑 (Session State) ---
    # 如果触发了重算（如改变了容量），则将所有圆整值重置为理论值的建议圆整结果
    if st.session_state.needs_recalc:
        st.session_state.sel_u2 = round(u2_theo) # 电压取整
        st.session_state.sel_de = round(de_theo_mm / 10) * 10 # 电极取整到10mm
        st.session_state.sel_dc = round((st.session_state.sel_de * ky_val) / 10) * 10
        st.session_state.sel_di = round((st.session_state.sel_de * ki_val) / 50) * 50 # 炉膛取整到50mm
        st.session_state.sel_hh = round((st.session_state.sel_de * kh_val) / 50) * 50
        st.session_state.sel_shell_id = st.session_state.sel_di + 2 * lining_thick
        st.session_state.sel_shell_h = st.session_state.sel_hh + 2000
        st.session_state.needs_recalc = False
    
    # 定义联动函数：当用户修改圆整电极直径时，自动更新几何参数
    def on_de_change():
        de_new = st.session_state.sel_de_input
        st.session_state.sel_de = de_new
        # 联动更新
        st.session_state.sel_dc = round((de_new * ky_val) / 10) * 10
        st.session_state.sel_di = round((de_new * ki_val) / 50) * 50
        st.session_state.sel_hh = round((de_new * kh_val) / 50) * 50
        st.session_state.sel_shell_id = st.session_state.sel_di + 2 * lining_thick
        st.session_state.sel_shell_h = st.session_state.sel_hh + 2000

    with col2:
        st.subheader("4. 结果分析与参数修正")
        st.caption("💡 提示：右侧数据可直接修改，修改电极直径会自动联动其他尺寸。")

        # 构建对比表格布局
        # 我们使用 st.columns 来对齐显示 "项目 | 理论值 | 确认值(可改)"
        
        st.markdown("##### ⚡ 电气参数")
        c1, c2, c3 = st.columns([1.5, 1.5, 2])
        c1.markdown("**参数名称**")
        c2.markdown("**理论计算值**")
        c3.markdown("**工程圆整值 (可修改)**")
        
        # 1. 变压器
        c1.write("变压器容量")
        c2.write(f"{capacity_mva} MVA")
        c3.info(f"{capacity_mva} MVA")
        
        # 2. 一次电流
        c1.write(f"一次电流 I₁ ({u1_kv}kV)")
        c2.write(f"{i1_theo:.1f} A")
        c3.write(f"{i1_theo:.1f} A") # 随容量自动变，不建议手改

        # 3. 二次电压
        c1.write("二次电压 U₂")
        c2.write(f"{u2_theo:.1f} V")
        sel_u2 = c3.number_input("确认电压 U₂ (V)", value=st.session_state.sel_u2, step=1, key='sel_u2_input')

        # 4. 二次电流 (根据圆整电压反算)
        sel_i2 = (p_kva * 1000) / (1.73205 * sel_u2)
        c1.write("二次电流 I₂")
        c2.write(f"{i2_theo/1000:.1f} kA")
        c3.success(f"反算: {sel_i2/1000:.1f} kA") # 自动显示

        st.markdown("---")
        st.markdown("##### 📏 结构参数 (自动联动)")
        
        cc1, cc2, cc3 = st.columns([1.5, 1.5, 2])
        
        # 5. 电极直径
        cc1.write(f"电极直径 De (J={j_val})")
        cc2.write(f"{de_theo_mm:.0f} mm")
        # 关键：绑定回调函数
        sel_de = cc3.number_input("确认电极 De (mm)", value=float(st.session_state.sel_de), step=10.0, key='sel_de_input', on_change=on_de_change)

        # 6. 极心圆
        cc1.write(f"极心圆直径 Dc (Ky={ky_val})")
        cc2.write(f"{dc_theo_mm:.0f} mm")
        sel_dc = cc3.number_input("确认极心圆 Dc (mm)", value=float(st.session_state.sel_dc), step=10.0, key='sel_dc_input')

        # 7. 炉膛内径
        cc1.write(f"炉膛内径 Di (Ki={ki_val})")
        cc2.write(f"{di_theo_mm:.0f} mm")
        sel_di = cc3.number_input("确认炉膛内径 Di (mm)", value=float(st.session_state.sel_di), step=50.0, key='sel_di_input')

        # 8. 炉膛深度
        cc1.write(f"炉膛深度 Hh (Kh={kh_val})")
        cc2.write(f"{hh_theo_mm:.0f} mm")
        sel_hh = cc3.number_input("确认炉膛深度 Hh (mm)", value=float(st.session_state.sel_hh), step=50.0, key='sel_hh_input')

        # 9. 炉壳尺寸
        cc1.write("炉壳内径 (估)")
        cc2.write(f"{shell_id_theo_mm:.0f} mm")
        sel_shell_id = cc3.number_input("确认炉壳内径 (mm)", value=float(st.session_state.sel_shell_id), step=50.0, key='sel_shell_id_input')
        
        cc1.write("炉壳高度 (估)")
        cc2.write(f"{shell_h_theo_mm:.0f} mm")
        sel_shell_h = cc3.number_input("确认炉壳高度 (mm)", value=float(st.session_state.sel_shell_h), step=50.0, key='sel_shell_h_input')

        # --- 绘图 (使用圆整值) ---
        st.divider()
        st.markdown(f"#### 📐 最终设计图纸 ({alloy} - {capacity_mva}MVA)")
        
        fig, ax = plt.subplots(figsize=(10, 5))
        rect_shell = patches.Rectangle((-sel_shell_id/2, 0), sel_shell_id, sel_shell_h, linewidth=3, edgecolor='#333333', facecolor='none', label='炉壳')
        ax.add_patch(rect_shell)
        bottom_thick = 1500
        rect_hearth = patches.Rectangle((-sel_di/2, bottom_thick), sel_di, sel_hh, linewidth=2, edgecolor='red', facecolor='#FFD700', alpha=0.3, label='炉膛')
        ax.add_patch(rect_hearth)
        elec_w = sel_de
        elec_h = sel_shell_h * 0.8
        ax.add_patch(patches.Rectangle((-sel_dc/2 - elec_w/2, sel_shell_h/2), elec_w, elec_h, color='#555555', label='电极'))
        ax.add_patch(patches.Rectangle((sel_dc/2 - elec_w/2, sel_shell_h/2), elec_w, elec_h, color='#555555'))
        
        # 智能标注 (显示圆整值)
        bbox_props = dict(boxstyle="square,pad=0.3", fc="white", ec="black", lw=0.5, alpha=0.8)
        ax.annotate(f"炉膛内径 {sel_di:.0f}", xy=(0, bottom_thick + sel_hh/2), ha='center', fontsize=12, bbox=bbox_props)
        ax.annotate(f"极心圆 {sel_dc:.0f}", xy=(0, sel_shell_h - 500), xytext=(0, sel_shell_h + 500), arrowprops=dict(arrowstyle='-'), ha='center', color='blue', fontsize=12, bbox=bbox_props)
        ax.plot([-sel_dc/2, sel_dc/2], [sel_shell_h + 200, sel_shell_h + 200], color='blue', marker='|')
        
        ax.set_aspect('equal')
        ax.axis('off')
        plt.legend(loc='upper right')
        st.pyplot(fig)

        # 导出CSV (包含理论与圆整)
        res_data = [
            {"参数类别": "供电参数", "参数名称": "变压器容量", "理论计算值": f"{capacity_mva}", "最终设计值": f"{capacity_mva}", "单位": "MVA"},
            {"参数类别": "供电参数", "参数名称": "一次电压 U1", "理论计算值": f"{u1_kv}", "最终设计值": f"{u1_kv}", "单位": "kV"},
            {"参数类别": "供电参数", "参数名称": "二次电压 U2", "理论计算值": f"{u2_theo:.1f}", "最终设计值": f"{sel_u2:.0f}", "单位": "V"},
            {"参数类别": "供电参数", "参数名称": "二次电流 I2", "理论计算值": f"{i2_theo:.1f}", "最终设计值": f"{sel_i2:.1f}", "单位": "A"},
            {"参数类别": "电极系统", "参数名称": "电极直径 De", "理论计算值": f"{de_theo_mm:.1f}", "最终设计值": f"{sel_de:.0f}", "单位": "mm"},
            {"参数类别": "电极系统", "参数名称": "极心圆直径 Dc", "理论计算值": f"{dc_theo_mm:.1f}", "最终设计值": f"{sel_dc:.0f}", "单位": "mm"},
            {"参数类别": "炉体结构", "参数名称": "炉膛内径 Di", "理论计算值": f"{di_theo_mm:.1f}", "最终设计值": f"{sel_di:.0f}", "单位": "mm"},
            {"参数类别": "炉体结构", "参数名称": "炉膛深度 Hh", "理论计算值": f"{hh_theo_mm:.1f}", "最终设计值": f"{sel_hh:.0f}", "单位": "mm"},
            {"参数类别": "炉体结构", "参数名称": "炉壳内径 (估)", "理论计算值": f"{shell_id_theo_mm:.1f}", "最终设计值": f"{sel_shell_id:.0f}", "单位": "mm"},
            {"参数类别": "导电元件", "参数名称": "铜瓦数量", "理论计算值": "-", "最终设计值": f"{tile_num}", "单位": "块"},
            {"参数类别": "导电元件", "参数名称": "铜管数量", "理论计算值": "-", "最终设计值": f"{tube_num}", "单位": "根"},
        ]
        df_res = pd.DataFrame(res_data)
        st.dataframe(df_res, hide_index=True, use_container_width=True)
        csv = df_res.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下载最终设计参数表 (CSV)", csv, f"矿热炉设计_{capacity_mva}MVA_最终版.csv")

# ==========================================
# 5. 模块二：铁水包设计 (保持不变)
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
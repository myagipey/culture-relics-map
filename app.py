import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
import json
import os
import textwrap

# ==============================================================================
# 1. 页面配置
# ==============================================================================
st.set_page_config(
    page_title="文明的回响",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ------------------------------------------------------------------------------
# 2. CSS 样式
# ------------------------------------------------------------------------------
THEME_BG = "#F6F3EC"
CARD_BG = "#FFFFFF"
TEXT_COLOR = "#000000"

MULTISELECT_BG = "#F6F3EC"
MULTISELECT_TAG_BG = "#5C382E"

st.markdown(f"""
<style>
    header[data-testid="stHeader"] {{ display: none; }}

    .stApp {{ background-color: {THEME_BG}; }}

    .block-container {{
        padding-top: 10px !important;
        padding-bottom: 10px !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100%;
    }}

    div[data-testid="stVerticalBlock"] {{ gap: 10px !important; }}
    div[data-testid="column"] {{ padding: 0px !important; }}

    h1 {{
        font-family: "SimSun", "Times New Roman", serif;
        font-weight: bold;
        color: {TEXT_COLOR} !important;
        font-size: 36px !important;
        margin: 0px 0px 10px 0px !important;
        border-bottom: 3px solid {TEXT_COLOR};
        padding-bottom: 8px !important;
    }}

    div[data-testid="stContainer"] {{
        background-color: {CARD_BG};
        border-radius: 4px;
        border: 0px solid #E5E5E5;
    }}

    div[data-testid="stBorderContainer"] {{
        background-color: {CARD_BG};
        border: 1px solid #ddd;
        padding: 15px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }}

    div[data-testid="stDeckGlJsonChart"] {{
        background-color: {CARD_BG};
        border: 1px solid #ddd;
        border-radius: 4px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        height: 500px !important;
        position: relative;
    }}
    .deckgl-wrapper {{ margin-top: 0px !important; }}

    details[title="Click to view actions"] {{ display: none; }}

    div[data-testid="stMetricLabel"] label {{ color: #000000 !important; }}
    div[data-testid="stMetricValue"] div {{ color: #000000 !important; }}

    div[data-testid="column"] > div:first-of-type {{
        margin-top: 35px;
    }}

    .stMultiSelect label {{ display: none; }} 

    div[data-baseweb="select"] > div {{
        background-color: {MULTISELECT_BG} !important;
        border: 1px solid #d0d0d0 !important;
    }}

    span[data-baseweb="tag"] {{
        background-color: {MULTISELECT_TAG_BG} !important;
        border-color: {MULTISELECT_TAG_BG} !important;
    }}
    span[data-baseweb="tag"] > span {{
        color: #ffffff !important;
    }}
    span[data-baseweb="tag"] svg {{
        fill: #ffffff !important;
    }}

</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 3. 数据处理
# ------------------------------------------------------------------------------
@st.cache_data
def load_data():
    file_path = 'relics_data.json'
    if not os.path.exists(file_path): pass

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return None, [], {}, []

    df = pd.DataFrame(data)
    if 'value' not in df.columns: return None, [], {}, []

    df['lng'] = df['value'].apply(lambda x: x[0])
    df['lat'] = df['value'].apply(lambda x: x[1])
    df = df[(df['lng'] > 70) & (df['lng'] < 140) & (df['lat'] > 0) & (df['lat'] < 60)]

    colors = {
        "古遗址": [187, 145, 73],
        "古墓葬": [228, 213, 156],
        "古建筑": [107, 128, 144],
        "石窟寺": [125, 130, 100],
        "近现代": [147, 56, 55],
        "其他": [149, 165, 166]
    }

    def rgb_to_hex(rgb):
        return '#%02x%02x%02x' % tuple(rgb)

    hex_colors = {k: rgb_to_hex(v) for k, v in colors.items()}

    all_types = [k for k in colors.keys() if k != '其他']

    def get_color_rgb(t):
        for k, v in colors.items():
            if k in str(t): return v
        return colors['其他']

    def get_color_hex(t):
        for k, v in hex_colors.items():
            if k in str(t): return v
        return hex_colors['其他']

    df['color_rgb'] = df['type'].apply(get_color_rgb)
    df['color_hex'] = df['type'].apply(get_color_hex)

    def clean_main_type(t):
        if not isinstance(t, str): return "其他"
        if "近现代" in t: return "近现代"
        return t.split('及')[0]

    df['main_type'] = df['type'].apply(clean_main_type)

    period_order = ["旧石器", "新石器", "夏商周", "秦汉", "三国两晋南北朝", "隋唐五代", "宋辽金元", "明清", "近现代"]

    def map_period(p):
        p = str(p)
        if "旧石器" in p: return "旧石器"
        if "新石器" in p: return "新石器"
        if any(x in p for x in ["夏", "商", "周"]): return "夏商周"
        if any(x in p for x in ["秦", "汉"]): return "秦汉"
        if any(x in p for x in ["三国", "晋", "南北朝"]): return "三国两晋南北朝"
        if any(x in p for x in ["隋", "唐", "五代"]): return "隋唐五代"
        if any(x in p for x in ["宋", "辽", "金", "元"]): return "宋辽金元"
        if any(x in p for x in ["明", "清"]): return "明清"
        if any(x in p for x in ["18", "19", "20", "革命", "近现代"]): return "近现代"
        return "其他"

    df['sim_period'] = df['period'].apply(map_period)
    return df, period_order, hex_colors, all_types


data_result = load_data()
if data_result[0] is None:
    st.error("数据文件 relics_data.json 未找到或格式错误")
    st.stop()

df, period_order, hex_colors, all_types = data_result

# ------------------------------------------------------------------------------
# 4. 高级联动逻辑
# ------------------------------------------------------------------------------
selected_provs = []
selected_time_periods = []

if "rank_chart" in st.session_state:
    try:
        sel = st.session_state.rank_chart
        if hasattr(sel, "selection") and len(sel.selection.prov_click) > 0:
            for x in sel.selection.prov_click:
                if 'province_label' in x:
                    selected_provs.append(x['province_label'].split(' ')[0])
    except:
        pass

if "time_chart" in st.session_state:
    try:
        sel = st.session_state.time_chart
        if hasattr(sel, "selection"):
            if "time_click" in sel.selection and len(sel.selection.time_click) > 0:
                for item in sel.selection.time_click:
                    if 'sim_period' in item:
                        selected_time_periods.append(item['sim_period'])
            elif "time_brush" in sel.selection:
                brush = sel.selection.time_brush
                if 'sim_period' in brush:
                    selected_time_periods = brush['sim_period']
    except:
        pass

# ==============================================================================
# 5. 页面渲染
# ==============================================================================
st.markdown("<h1>文明的回响：国保单位时空演变图谱</h1>", unsafe_allow_html=True)
col_map, col_right = st.columns([3.2, 1], gap="medium")

with col_map:
    selected_types = st.multiselect(
        "筛选文物类型",
        all_types,
        default=all_types,
        placeholder="请选择文物类型 (可多选)",
        key="type_selector"
    )

    df_base = df[df['main_type'].isin(selected_types)] if selected_types else df

    df_map = df_base.copy()
    if selected_provs:
        df_map = df_map[df_map['province'].isin(selected_provs)]
    if selected_time_periods:
        df_map = df_map[df_map['sim_period'].isin(selected_time_periods)]

    df_rank = df_base.copy()
    if selected_time_periods:
        df_rank = df_rank[df_rank['sim_period'].isin(selected_time_periods)]

    df_time = df_base.copy()
    if selected_provs:
        df_time = df_time[df_time['province'].isin(selected_provs)]

    if not df_map.empty:
        mid_lat, mid_lng, zoom = df_map['lat'].mean(), df_map['lng'].mean(), 3.8
    else:
        mid_lat, mid_lng, zoom = 35.0, 105.0, 3.8

    view_state = pdk.ViewState(latitude=mid_lat, longitude=mid_lng, zoom=zoom, pitch=0)

    layer_scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position='[lng, lat]',
        get_color='color_rgb',
        get_radius=3000,
        radius_min_pixels=3,
        radius_max_pixels=10,
        pickable=True,
        stroked=True,
        filled=True,
        line_width_min_pixels=0.5,
        get_line_color=[255, 255, 255, 150],
        opacity=1.0
    )

    tooltip = {
        "html": "<div style='background:rgba(255,255,255,0.95);padding:10px;border-radius:4px;box-shadow:0 2px 5px rgba(0,0,0,0.2);color:#333;font-family:Microsoft YaHei;border:1px solid #ddd;'>"
                "<b style='color:#D35400'>{name}</b><br>"
                "<span style='color:#666'>{province} {city}</span><br>"
                "<span style='color:#666'>{period} | {type}</span><br>"
                "</div>"
    }

    deck = pdk.Deck(
        map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        initial_view_state=view_state,
        layers=[layer_scatter],
        tooltip=tooltip
    )

    st.pydeck_chart(deck, use_container_width=True)

    items_html = ""
    display_types = [t for t in all_types if t in selected_types]

    for name in display_types:
        color = hex_colors.get(name, "#95A5A6")
        items_html += f"""<div style="display: flex; align-items: center; margin-bottom: 6px;"><div style="width: 12px; height: 12px; background-color: {color}; margin-right: 8px; border-radius: 2px; border: 1px solid rgba(0,0,0,0.1);"></div><div style="color: #333; font-size: 12px;">{name}</div></div>"""

    if items_html:
        legend_final = textwrap.dedent(f"""
            <div style="height: 0px; width: 100%; position: relative; z-index: 999; pointer-events: none;">
                <div style="
                    position: absolute;
                    bottom: 25px;
                    left: 15px;
                    background-color: rgba(255, 255, 255, 0.95);
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    padding: 12px 15px;
                    width: auto;
                    min-width: 100px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    pointer-events: auto;
                ">
                    <div style="font-weight: bold; margin-bottom: 10px; font-size: 13px; color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 5px;">图例</div>
                    {items_html}
                </div>
            </div>
        """)
        st.markdown(legend_final, unsafe_allow_html=True)

with col_right:
    with st.container(border=True):
        st.markdown(f"""
        <div style="color:#000000; font-weight:bold; margin-bottom:15px; padding-left:0px;">数据概览</div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 24px; font-weight: bold; color: #000000; line-height: 1;">{{}}</div>
                <div style="font-size: 12px; color: #666; margin-top: 5px;">当前显示</div>
            </div>
            <div style="width: 1px; height: 30px; background-color: #eee;"></div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 24px; font-weight: bold; color: #000000; line-height: 1;">{{}}</div>
                <div style="font-size: 12px; color: #666; margin-top: 5px;">覆盖省份</div>
            </div>
        </div>
        """.format(len(df_map), len(df_map['province'].unique())), unsafe_allow_html=True)

    with st.container(border=True, height=440):
        st.markdown("""
        <div style="color:#000000; font-weight:bold; margin-bottom:10px;">各省文物数量排名</div>
        """, unsafe_allow_html=True)

        prov_counts = df_rank['province'].value_counts().reset_index()
        prov_counts.columns = ['province', 'count']
        prov_counts['province_label'] = prov_counts['province'] + "   " + prov_counts['count'].astype(str)

        BAR_COLOR = "#95A5A6"

        click = alt.selection_point(fields=['province_label'], name="prov_click", toggle=True)

        chart_height = len(prov_counts) * 25

        base = alt.Chart(prov_counts).encode(
            y=alt.Y('province_label', sort='-x', title=None,
                    axis=alt.Axis(labelColor="black", labelFontSize=13, ticks=False, domain=False))
        )

        bars = base.mark_bar(cornerRadiusEnd=3, height=18).encode(
            x=alt.X('count', axis=None),
            color=alt.condition(click, alt.value(BAR_COLOR), alt.value("#BDC3C7")),
            tooltip=alt.value(None)
        )

        chart_rank = bars.add_params(click).properties(
            background='transparent',
            height=chart_height
        )

        st.altair_chart(chart_rank, use_container_width=True, on_select="rerun", key="rank_chart")

# --- 底部：时间轴 ---
with st.container(border=True):
    st.markdown("""
    <div style="color:#000000; font-weight:bold; padding-left:0px; margin-bottom:5px;">历史朝代演变</div>
    """, unsafe_allow_html=True)

    brush = alt.selection_interval(encodings=['x'], name="time_brush")
    click_time = alt.selection_point(fields=['sim_period'], name="time_click")

    time_df_agg = df_time.groupby(['sim_period', 'main_type', 'color_hex']).size().reset_index(name='count')

    # 辅助数据：计算每朝代总数，用于tooltip
    period_totals = df_time.groupby('sim_period').size().reset_index(name='total_count')
    time_df_agg = pd.merge(time_df_agg, period_totals, on='sim_period')

    chart_line = alt.Chart(time_df_agg).mark_bar().encode(
        x=alt.X('sim_period', sort=period_order, title=None,
                axis=alt.Axis(labelColor="black", labelAngle=0, grid=False, domainColor="#DDD")),
        y=alt.Y('count',
                title="文化遗产数量",
                axis=alt.Axis(titleColor="black", labelColor="black", grid=True, gridColor="#EEE", gridDash=[2, 2])),
        color=alt.Color('color_hex', scale=None, legend=None),
        opacity=alt.condition(brush | click_time, alt.value(1), alt.value(0.3)),

        # --- 修改：Tooltip 不显示"朝代" ---
        tooltip=[
            alt.Tooltip('main_type', title='类型'),
            alt.Tooltip('count', title='该类型数量'),
            alt.Tooltip('total_count', title='该朝代总数')
        ]
    ).add_params(brush, click_time).properties(
        height=200,
        background='transparent'
    ).configure_view(strokeWidth=0)

    st.altair_chart(chart_line, use_container_width=True, on_select="rerun", key="time_chart")
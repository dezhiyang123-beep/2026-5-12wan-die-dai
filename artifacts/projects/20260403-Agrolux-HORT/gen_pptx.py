from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Cm
import copy

# ── Color palette ──────────────────────────────────────────────────────────────
GREEN  = RGBColor(34,  85,  51)   # #225533 dark green
WHITE  = RGBColor(255,255,255)
LGRAY  = RGBColor(242,242,242)    # light gray
DGRAY  = RGBColor(51,  51,  51)   # dark gray text
ANTHR  = RGBColor(77,  77,  79)   # anthracite RAL7016
ORANGE = RGBColor(255,140,  0)
RED    = RGBColor(200,  0,   0)
LGREEN_BG = RGBColor(220,240,220) # light green for BOM/action boxes

# ── Slide dimensions 16:9  33.87 × 19.05 cm ───────────────────────────────────
W = Inches(13.33)
H = Inches(7.5)

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H

BLANK = prs.slide_layouts[6]   # completely blank layout

# ══════════════════════════════════════════════════════════════════════════════
# Helper utilities
# ══════════════════════════════════════════════════════════════════════════════

def add_rect(slide, l, t, w, h, fill_rgb=None, line_rgb=None, line_w_pt=None):
    """Add a filled rectangle shape."""
    from pptx.util import Pt as Pt2
    shape = slide.shapes.add_shape(1, l, t, w, h)   # MSO_SHAPE_TYPE.RECTANGLE = 1
    if fill_rgb:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_rgb
    else:
        shape.fill.background()
    if line_rgb:
        shape.line.color.rgb = line_rgb
        if line_w_pt:
            shape.line.width = Pt2(line_w_pt)
    else:
        shape.line.fill.background()
    return shape

def add_textbox(slide, l, t, w, h, text, font_size=13, bold=False, italic=False,
                color=DGRAY, align=PP_ALIGN.LEFT, wrap=True):
    """Add a simple single-run textbox."""
    txBox = slide.shapes.add_textbox(l, t, w, h)
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txBox

def add_text_frame(slide, l, t, w, h, lines, default_size=13, default_color=DGRAY, wrap=True):
    """lines = list of dicts: {text, size, bold, italic, color, align, space_before}"""
    from pptx.util import Pt as Pt2
    txBox = slide.shapes.add_textbox(l, t, w, h)
    tf = txBox.text_frame
    tf.word_wrap = wrap
    first = True
    for item in lines:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.alignment = item.get('align', PP_ALIGN.LEFT)
        if 'space_before' in item:
            p.space_before = Pt2(item['space_before'])
        for seg in item.get('runs', [{'text': item.get('text',''), 'bold': item.get('bold',False),
                                       'italic': item.get('italic',False),
                                       'color': item.get('color', default_color),
                                       'size': item.get('size', default_size)}]):
            run = p.add_run()
            run.text = seg.get('text','')
            run.font.size = Pt2(seg.get('size', default_size))
            run.font.bold = seg.get('bold', False)
            run.font.italic = seg.get('italic', False)
            run.font.color.rgb = seg.get('color', default_color)
    return txBox

def header_bar(slide, title_text, bg_color=GREEN, txt_color=WHITE, font_size=24):
    """Full-width 2 cm header bar."""
    bar_h = Cm(2)
    add_rect(slide, 0, 0, W, bar_h, fill_rgb=bg_color)
    add_textbox(slide, Inches(0.3), Inches(0.05), W - Inches(0.6), bar_h,
                title_text, font_size=font_size, bold=True, color=txt_color)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — COVER
# ══════════════════════════════════════════════════════════════════════════════
slide1 = prs.slides.add_slide(BLANK)

# Full background green
add_rect(slide1, 0, 0, W, H, fill_rgb=GREEN)

# Title
add_textbox(slide1, Inches(0.8), Inches(2.0), W - Inches(1.6), Inches(1.5),
            "Agrolux 温室补光产品组合方案",
            font_size=40, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

# Subtitle
add_textbox(slide1, Inches(0.8), Inches(3.6), W - Inches(1.6), Inches(1.2),
            "FlexBar DS-30 双通道层间灯条  ×  SlideNode SN-40 浮动补光节点",
            font_size=20, bold=False, color=WHITE, align=PP_ALIGN.CENTER)

# Footer
add_textbox(slide1, Inches(0.5), H - Inches(0.5), W - Inches(1.0), Inches(0.4),
            "项目编号：20260403-Agrolux-HORT  |  日期：2026-04-04  |  机密",
            font_size=12, color=WHITE, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — MARKET OPPORTUNITY
# ══════════════════════════════════════════════════════════════════════════════
slide2 = prs.slides.add_slide(BLANK)

# Light gray body background
add_rect(slide2, 0, 0, W, H, fill_rgb=LGRAY)

# Header bar
header_bar(slide2, "市场机会")

bar_h = Cm(2)
content_top = bar_h + Inches(0.25)

# Big number
add_textbox(slide2, Inches(0.6), content_top, Inches(6), Inches(0.75),
            "$3.7B → $10.4B", font_size=36, bold=True, color=GREEN)

add_textbox(slide2, Inches(0.6), content_top + Inches(0.75), Inches(8), Inches(0.4),
            "温室照明市场规模 2023→2028，CAGR 22.4%",
            font_size=14, color=ANTHR)

# 4 bullet points
bullets = [
    "• 行为矛盾①：要满足DLI目标（番茄22-30 mol/m²/day）→ 但电费是最大运营成本",
    "• 行为矛盾②：要换LED节能 → 但LED减热加剧冬季供暖成本",
    "• 行为矛盾③：要多品种光谱优化 → 但同区域顶灯无法分区配光",
    "• 行为矛盾④：要提升中下层叶片光照 → 但顶灯穿透力有限，进入冠层热伤风险高",
]
bullet_top = content_top + Inches(1.3)
for i, b in enumerate(bullets):
    add_textbox(slide2, Inches(0.6), bullet_top + Inches(i * 0.65),
                W - Inches(1.2), Inches(0.65),
                b, font_size=13, color=DGRAY, wrap=True)

# Source note
add_textbox(slide2, Inches(0.6), H - Inches(0.55), W - Inches(1.2), Inches(0.4),
            "来源：MarketsandMarkets 2024 [H]",
            font_size=10, italic=True, color=ANTHR)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — TARGET USER
# ══════════════════════════════════════════════════════════════════════════════
slide3 = prs.slides.add_slide(BLANK)
add_rect(slide3, 0, 0, W, H, fill_rgb=LGRAY)
header_bar(slide3, "目标用户")

bar_h = Cm(2)
ct = bar_h + Inches(0.25)
col_w = (W - Inches(1.0)) / 2
lcol = Inches(0.5)
rcol = lcol + col_w + Inches(0.1)

# Left column
add_textbox(slide3, lcol, ct, col_w, Inches(0.5),
            "Head Grower", font_size=20, bold=True, color=GREEN)
add_textbox(slide3, lcol, ct + Inches(0.55), col_w, Inches(0.65),
            "商业温室技术负责人，日均工作10h+，管理1公顷以上种植区",
            font_size=13, color=DGRAY, wrap=True)

pain_title_top = ct + Inches(1.3)
add_textbox(slide3, lcol, pain_title_top, col_w, Inches(0.35),
            "痛点：", font_size=13, bold=True, color=DGRAY)

pains = [
    "• 轮作换品种时光谱切换靠经验，无标准化流程",
    "• 层间补光安装复杂，现有产品固定安装无法随苗高调整",
    "• OS控制系统刚上线，团队学习成本高",
]
for i, p_text in enumerate(pains):
    add_textbox(slide3, lcol, pain_title_top + Inches(0.4 + i*0.65),
                col_w - Inches(0.1), Inches(0.65),
                p_text, font_size=13, color=DGRAY, wrap=True)

# Right column
add_textbox(slide3, rcol, ct, col_w, Inches(0.5),
            "关键使用场景", font_size=20, bold=True, color=GREEN)

scenarios = [
    "• 冬季番茄密植期：顶光DLI不足+冠层内部光照衰减>70%",
    "• 轮作节点：番茄→甜椒，光谱需从高蓝切至高红",
    "• 生长追踪：番茄每周长15-20cm，固定灯效率每周下降",
]
for i, s_text in enumerate(scenarios):
    add_textbox(slide3, rcol, ct + Inches(0.6 + i * 0.75),
                col_w - Inches(0.1), Inches(0.75),
                s_text, font_size=13, color=DGRAY, wrap=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — C-05 FlexBar DS-30
# ══════════════════════════════════════════════════════════════════════════════
slide4 = prs.slides.add_slide(BLANK)
add_rect(slide4, 0, 0, W, H, fill_rgb=LGRAY)
header_bar(slide4, "C-05  FlexBar DS-30  双通道层间灯条")

bar_h = Cm(2)
ct = bar_h + Inches(0.2)
left_w = W * 0.60
right_w = W * 0.40
rl = left_w + Inches(0.1)

# --- Left side ---
# Tag (green box)
tag_h = Inches(0.38)
tag_shape = add_rect(slide4, Inches(0.4), ct, Inches(6.0), tag_h, fill_rgb=GREEN)
add_textbox(slide4, Inches(0.45), ct + Inches(0.02), Inches(5.9), tag_h,
            "解决：层间补光 + 轮作光谱切换", font_size=12, bold=False, color=WHITE)

p0_top = ct + tag_h + Inches(0.15)
# P0 label
add_textbox(slide4, Inches(0.4), p0_top, left_w - Inches(0.5), Inches(0.35),
            "P0功能：", font_size=13, bold=True, color=GREEN)

p0_items = [
    "• 层间补光 ≥200µmol/s/m，30-40cm冠层内精准打光",
    "• 双光谱预设：配方A（生长期高蓝）/ B（结果期高红），一键切换",
    "• Modbus接入LYRA/Agrolux OS，远程切换光谱",
]
for i, it in enumerate(p0_items):
    add_textbox(slide4, Inches(0.4), p0_top + Inches(0.4 + i*0.55),
                left_w - Inches(0.5), Inches(0.55),
                it, font_size=13, color=DGRAY, wrap=True)

spec_top = p0_top + Inches(2.1)
spec_box = add_rect(slide4, Inches(0.4), spec_top, left_w - Inches(0.5), Inches(0.55),
                    fill_rgb=RGBColor(220,220,220))
add_textbox(slide4, Inches(0.5), spec_top + Inches(0.03), left_w - Inches(0.7), Inches(0.5),
            "宽30mm  |  40-60W/m  |  ≥3.6µmol/J  |  IP67  |  BOM≤$28/m",
            font_size=12, color=DGRAY)

diff_top = spec_top + Inches(0.7)
add_textbox(slide4, Inches(0.4), diff_top, left_w - Inches(0.5), Inches(0.45),
            "全球无已知产品同时具备层间安装+双通道可调光谱",
            font_size=13, italic=True, color=GREEN)
add_textbox(slide4, Inches(0.4), diff_top + Inches(0.48), left_w - Inches(0.5), Inches(0.45),
            "vs Hortilux Inter：60mm宽固定单谱 vs 本方案30mm双谱",
            font_size=13, italic=True, color=GREEN)

# --- Right side ---
dfm_top = ct
dfm_h = Inches(0.55)
dfm_shape = add_rect(slide4, rl, dfm_top, right_w - Inches(0.3), dfm_h, fill_rgb=ORANGE)
add_textbox(slide4, rl + Inches(0.1), dfm_top + Inches(0.05), right_w - Inches(0.5), dfm_h,
            "DFM：CONDITIONAL", font_size=14, bold=True, color=WHITE)

add_textbox(slide4, rl, dfm_top + Inches(0.7), right_w - Inches(0.3), Inches(0.65),
            "BOM：$22-28/m（灯条）+ $45/台驱动器（均摊≤$8/m）",
            font_size=13, color=DGRAY, wrap=True)

risk_top = dfm_top + Inches(1.5)
add_textbox(slide4, rl, risk_top, right_w - Inches(0.3), Inches(0.35),
            "主要风险：", font_size=12, bold=True, color=DGRAY)
risks = [
    "⚠ 热阻：双通道8h连续，结温需验证≤105°C",
    "⚠ EMI：双PWM驱动器互扰，需EMC预测试",
]
for i, r in enumerate(risks):
    add_textbox(slide4, rl, risk_top + Inches(0.4 + i*0.65),
                right_w - Inches(0.3), Inches(0.65),
                r, font_size=12, color=RED, wrap=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — C-02 SlideNode SN-40
# ══════════════════════════════════════════════════════════════════════════════
slide5 = prs.slides.add_slide(BLANK)
add_rect(slide5, 0, 0, W, H, fill_rgb=LGRAY)
header_bar(slide5, "C-02  SlideNode SN-40  浮动轨道补光节点", bg_color=ANTHR)

bar_h = Cm(2)
ct = bar_h + Inches(0.2)
left_w = W * 0.60
right_w = W * 0.40
rl = left_w + Inches(0.1)

# --- Left side ---
tag_h = Inches(0.38)
add_rect(slide5, Inches(0.4), ct, Inches(5.5), tag_h, fill_rgb=ANTHR)
add_textbox(slide5, Inches(0.45), ct + Inches(0.02), Inches(5.4), tag_h,
            "解决：动态追踪作物生长高度", font_size=12, color=WHITE)

p0_top = ct + tag_h + Inches(0.15)
add_textbox(slide5, Inches(0.4), p0_top, left_w - Inches(0.5), Inches(0.35),
            "P0功能：", font_size=13, bold=True, color=ANTHR)

p0_items = [
    "• 单手15秒调位：弹簧夹沿灌溉导轨滑动，无需工具",
    "• 40W COB / 400µmol/s，始终维持最优光距30-40cm",
    "• Zigbee自组网（8节点+1网关），Modbus接入Agrolux OS",
]
for i, it in enumerate(p0_items):
    add_textbox(slide5, Inches(0.4), p0_top + Inches(0.4 + i*0.55),
                left_w - Inches(0.5), Inches(0.55),
                it, font_size=13, color=DGRAY, wrap=True)

spec_top = p0_top + Inches(2.1)
add_rect(slide5, Inches(0.4), spec_top, left_w - Inches(0.5), Inches(0.55),
         fill_rgb=RGBColor(220,220,220))
add_textbox(slide5, Inches(0.5), spec_top + Inches(0.03), left_w - Inches(0.7), Inches(0.5),
            "Ø80mm×20mm  |  40W  |  IP65  |  RH 95%  |  BOM≤$45/节点",
            font_size=12, color=DGRAY)

diff_top = spec_top + Inches(0.7)
add_textbox(slide5, Inches(0.4), diff_top, left_w - Inches(0.5), Inches(0.45),
            "市场唯一可随作物动态移位的补光节点",
            font_size=13, italic=True, color=ANTHR)
add_textbox(slide5, Inches(0.4), diff_top + Inches(0.48), left_w - Inches(0.5), Inches(0.55),
            "vs Hortilux Inter：固定安装，效率损失30-40%（植株0.5m→3m周期内）",
            font_size=13, italic=True, color=ANTHR, wrap=True)

# --- Right side ---
dfm_top = ct
dfm_h = Inches(0.55)
add_rect(slide5, rl, dfm_top, right_w - Inches(0.3), dfm_h, fill_rgb=ORANGE)
add_textbox(slide5, rl + Inches(0.1), dfm_top + Inches(0.05), right_w - Inches(0.5), dfm_h,
            "DFM：CONDITIONAL", font_size=14, bold=True, color=WHITE)

add_textbox(slide5, rl, dfm_top + Inches(0.7), right_w - Inches(0.3), Inches(0.45),
            "BOM：$35-45/节点（含Zigbee模块）",
            font_size=13, color=DGRAY, wrap=True)

risk_top = dfm_top + Inches(1.5)
add_textbox(slide5, rl, risk_top, right_w - Inches(0.3), Inches(0.35),
            "主要风险：", font_size=12, bold=True, color=DGRAY)
risks = [
    "⚠ 无线稳定性：金属温室80-95%RH多径干扰，需实地测试",
    "⚠ 热阻：20mm圆盘40W COB，FEA验证优先",
]
for i, r in enumerate(risks):
    add_textbox(slide5, rl, risk_top + Inches(0.4 + i*0.65),
                right_w - Inches(0.3), Inches(0.65),
                r, font_size=12, color=RED, wrap=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — CMF + RENDER PROMPTS
# ══════════════════════════════════════════════════════════════════════════════
slide6 = prs.slides.add_slide(BLANK)
add_rect(slide6, 0, 0, W, H, fill_rgb=LGRAY)
header_bar(slide6, "CMF规格 + 效果图提示词")

bar_h = Cm(2)
ct = bar_h + Inches(0.25)
col_w = (W - Inches(1.2)) / 2
lcol = Inches(0.5)
rcol = lcol + col_w + Inches(0.2)

# ---- Left column: C-05 ----
add_textbox(slide6, lcol, ct, col_w, Inches(0.45),
            "FlexBar DS-30", font_size=16, bold=True, color=DGRAY)

cmf_c05 = [
    ("颜色：", "RAL 9003 Signal White，ΔE≤1.5"),
    ("材料：", "6063-T5铝基板 + ASA驱动器壳体 + M12 IP67接头"),
    ("表面处理：", "阳极氧化哑光GU15-25 / 聚氨酯面漆GU20-30"),
]
row_h = Inches(0.55)
for i, (label, val) in enumerate(cmf_c05):
    top_i = ct + Inches(0.5 + i * 0.6)
    add_textbox(slide6, lcol, top_i, Inches(1.4), row_h, label,
                font_size=13, bold=True, color=DGRAY)
    add_textbox(slide6, lcol + Inches(1.4), top_i, col_w - Inches(1.4), row_h,
                val, font_size=13, color=DGRAY, wrap=True)

prompt_top = ct + Inches(2.4)
add_textbox(slide6, lcol, prompt_top, col_w, Inches(0.35),
            "效果图提示词示例：", font_size=12, bold=True, color=ANTHR)
prompt_c05 = (
    "Angle 1: 30mm wide anodized aluminum LED strip, 1.2m length, "
    "dual LED rows (red+blue-white), signal white RAL9003, spring clips, "
    "M12 connectors, 45° isometric, studio lighting, dark background, photorealistic 8K"
)
add_rect(slide6, lcol, prompt_top + Inches(0.38), col_w, Inches(1.2),
         fill_rgb=RGBColor(230,230,230))
add_textbox(slide6, lcol + Inches(0.1), prompt_top + Inches(0.42),
            col_w - Inches(0.2), Inches(1.15),
            prompt_c05, font_size=11, italic=True, color=ANTHR, wrap=True)

# ---- Right column: C-02 ----
add_textbox(slide6, rcol, ct, col_w, Inches(0.45),
            "SlideNode SN-40", font_size=16, bold=True, color=DGRAY)

cmf_c02 = [
    ("颜色：", "RAL 7016 Anthracite Gray，ΔE≤2.0"),
    ("材料：", "ADC12压铸铝 + PC光学镜片 + 316L不锈钢夹具"),
    ("表面处理：", "TGIC环氧粉末哑光GU10-20，细砂纹防滑"),
]
for i, (label, val) in enumerate(cmf_c02):
    top_i = ct + Inches(0.5 + i * 0.6)
    add_textbox(slide6, rcol, top_i, Inches(1.4), row_h, label,
                font_size=13, bold=True, color=DGRAY)
    add_textbox(slide6, rcol + Inches(1.4), top_i, col_w - Inches(1.4), row_h,
                val, font_size=13, color=DGRAY, wrap=True)

add_textbox(slide6, rcol, prompt_top, col_w, Inches(0.35),
            "效果图提示词示例：", font_size=12, bold=True, color=ANTHR)
prompt_c02 = (
    "Angle 1: 80mm diameter × 20mm disc, anthracite gray RAL7016, "
    "55mm PC COB lens, top spring clamp with thumb-press button, "
    "matte powder coat, 45° isometric, dark background, photorealistic 8K"
)
add_rect(slide6, rcol, prompt_top + Inches(0.38), col_w, Inches(1.2),
         fill_rgb=RGBColor(230,230,230))
add_textbox(slide6, rcol + Inches(0.1), prompt_top + Inches(0.42),
            col_w - Inches(0.2), Inches(1.15),
            prompt_c02, font_size=11, italic=True, color=ANTHR, wrap=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — MANUFACTURABILITY SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
from pptx.util import Pt as Pt2
from pptx.oxml.ns import qn
from lxml import etree

slide7 = prs.slides.add_slide(BLANK)
add_rect(slide7, 0, 0, W, H, fill_rgb=LGRAY)
header_bar(slide7, "落地性评估")

bar_h = Cm(2)
ct = bar_h + Inches(0.2)

# Table headers and rows
table_data = [
    ["产品",          "风险项",              "等级", "缓解措施"],
    ["FlexBar DS-30", "双通道热阻（结温验证）",  "H",  "FEA仿真→降功率备选"],
    ["FlexBar DS-30", "双PWM驱动EMI互扰",      "H",  "EMC预测试$3-5k"],
    ["FlexBar DS-30", "UL 8800认证周期",        "M",  "预算$25-35k，6个月"],
    ["SlideNode SN-40","无线稳定性（温室实测）", "H",  "72h实地测试优先"],
    ["SlideNode SN-40","圆盘热阻（FEA验证）",   "H",  "必须先做FEA再打样"],
    ["SlideNode SN-40","网关单点故障",           "M",  "离线安全模式（已写入PRD）"],
]

# Column widths
col_widths = [Inches(2.2), Inches(4.0), Inches(1.0), Inches(5.4)]
table_left = Inches(0.4)
table_top  = ct
table_w    = sum(col_widths)
table_h    = Inches(2.8)

tbl = slide7.shapes.add_table(
    len(table_data), 4,
    table_left, table_top, table_w, table_h
).table

# Set column widths
for ci, cw in enumerate(col_widths):
    tbl.columns[ci].width = cw

risk_colors = {"H": RED, "M": ORANGE, "L": ANTHR}

for ri, row in enumerate(table_data):
    for ci, cell_text in enumerate(row):
        cell = tbl.cell(ri, ci)
        cell.text = cell_text
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.runs[0] if p.runs else p.add_run()
        run.font.size = Pt2(13)
        run.font.bold = (ri == 0)
        if ri == 0:
            run.font.color.rgb = WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = GREEN
        else:
            if ci == 2:  # risk level column
                run.font.color.rgb = risk_colors.get(cell_text, DGRAY)
                run.font.bold = True
            else:
                run.font.color.rgb = DGRAY
            if ri % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LGRAY

# BOM estimate boxes below table
bom_top = ct + Inches(3.0)
box_w = (W - Inches(1.2)) / 2
lbox = Inches(0.4)
rbox = lbox + box_w + Inches(0.2)

# Left box - FlexBar (light green border)
add_rect(slide7, lbox, bom_top, box_w, Inches(1.2),
         fill_rgb=RGBColor(235,248,235), line_rgb=GREEN, line_w_pt=1.5)
add_textbox(slide7, lbox + Inches(0.1), bom_top + Inches(0.05),
            box_w - Inches(0.2), Inches(1.1),
            "FlexBar DS-30\n灯条：$22-28/m\n驱动器：$45/台（均摊$7-9/m）\n合计：约$29-37/m",
            font_size=12, color=DGRAY, wrap=True)

# Right box - SlideNode (light gray border)
add_rect(slide7, rbox, bom_top, box_w, Inches(1.2),
         fill_rgb=WHITE, line_rgb=ANTHR, line_w_pt=1.5)
add_textbox(slide7, rbox + Inches(0.1), bom_top + Inches(0.05),
            box_w - Inches(0.2), Inches(1.1),
            "SlideNode SN-40\n节点：$35-45/个\n量产500件后→$27-35/个\n（压铸模$18k开模）",
            font_size=12, color=DGRAY, wrap=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — RECOMMENDATION
# ══════════════════════════════════════════════════════════════════════════════
slide8 = prs.slides.add_slide(BLANK)
add_rect(slide8, 0, 0, W, H, fill_rgb=LGRAY)
header_bar(slide8, "推销策略 与 下一步行动")

bar_h = Cm(2)
ct = bar_h + Inches(0.2)

# Strategy section title
add_textbox(slide8, Inches(0.5), ct, W - Inches(1.0), Inches(0.5),
            "推荐顺序：C-05先行，C-02跟进",
            font_size=20, bold=True, color=GREEN)

strategy_bullets = [
    "• C-05门槛低：不依赖LYRA接口授权，Modbus通用协议，可独立落地",
    "• C-05价格可接受：$29-37/m，种植者可小批试用，降低Owner决策门槛",
    "• C-02需先验证无线可靠性（首要H级风险），建议借用客户温室实测后再推进",
    "• 两个产品可作为产品组合pitch：'层间补光完整解决方案，固定+动态两种选择'",
]
for i, b in enumerate(strategy_bullets):
    add_textbox(slide8, Inches(0.5), ct + Inches(0.6 + i*0.5),
                W - Inches(1.0), Inches(0.5),
                b, font_size=13, color=DGRAY, wrap=True)

# Boss 7D table
boss_top = ct + Inches(2.7)
boss_data = [
    ["维度",    "C-05评分",                          "C-02评分"],
    ["使用场景", "★★★★☆ 场景清晰，轮作+层间",         "★★★★☆ 场景清晰，高茎作物追踪"],
    ["目标人群", "★★★★☆ Head Grower明确",             "★★★☆☆ 操作动作需用户研究验证"],
    ["差异化",  "★★★★★ 全球无已知同类",               "★★★★★ 市场唯一动态移位节点"],
    ["制造可行性","★★★☆☆ 热/EMI需验证",               "★★☆☆☆ 热+无线双H风险"],
    ["成本结构", "★★★★☆ BOM可控",                     "★★★☆☆ 量产前成本偏高"],
    ["市场规模", "★★★★☆ CAGR 22.4%，层间补光明确需求", "★★★☆☆ 高茎作物子集"],
    ["客户买单", "★★★☆☆ 取决于Agrolux OEM开放度[L]",  "★★★☆☆ 同上"],
]

boss_col_widths = [Inches(1.5), Inches(4.5), Inches(4.5)]
boss_w = sum(boss_col_widths)
boss_h = Inches(2.3)

btbl = slide8.shapes.add_table(
    len(boss_data), 3,
    Inches(0.4), boss_top, boss_w, boss_h
).table

for ci, cw in enumerate(boss_col_widths):
    btbl.columns[ci].width = cw

for ri, row in enumerate(boss_data):
    for ci, cell_text in enumerate(row):
        cell = btbl.cell(ri, ci)
        cell.text = cell_text
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.runs[0] if p.runs else p.add_run()
        run.font.size = Pt2(11)
        run.font.bold = (ri == 0)
        if ri == 0:
            run.font.color.rgb = WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = GREEN
        else:
            run.font.color.rgb = DGRAY
            if ri % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LGRAY

# Next actions box
action_left  = W * 0.60 + Inches(0.1)
action_top   = ct + Inches(0.1)
action_w     = W - action_left - Inches(0.2)
action_h     = Inches(2.4)

add_rect(slide8, action_left, action_top, action_w, action_h,
         fill_rgb=RGBColor(220,240,220), line_rgb=GREEN, line_w_pt=1.5)
add_textbox(slide8, action_left + Inches(0.1), action_top + Inches(0.05),
            action_w - Inches(0.2), Inches(0.4),
            "立即行动（按优先级）", font_size=14, bold=True, color=GREEN)

actions = [
    "1. 联系Agrolux partnerships部门，确认OEM合作开放度（影响所有方向）",
    "2. C-05：安排双通道热阻FEA仿真（1周），同步EMC预测试咨询（SGS/Intertek）",
    "3. C-02：在目标客户温室借测Zigbee 72h可靠性（最低成本验证H级风险）",
    "4. C-02量产规划：确认年需求量是否>500件，决定是否开压铸模",
]
for i, act in enumerate(actions):
    add_textbox(slide8, action_left + Inches(0.1),
                action_top + Inches(0.5 + i * 0.47),
                action_w - Inches(0.2), Inches(0.47),
                act, font_size=11, color=DGRAY, wrap=True)

# Footer
add_textbox(slide8, Inches(0.3), H - Inches(0.4), W - Inches(0.6), Inches(0.35),
            "© 2026 | 项目编号：20260403-Agrolux-HORT | 机密文件，仅供Agrolux内部评审",
            font_size=10, color=ANTHR, align=PP_ALIGN.CENTER)

# ══════════════════════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════════════════════
import os
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "final_pitch.pptx")
prs.save(out_path)
print(f"Saved: {out_path}")
sz = os.path.getsize(out_path)
print(f"File size: {sz:,} bytes ({sz/1024:.1f} KB)")
assert sz > 10 * 1024, f"File too small: {sz} bytes"
print("OK: > 10 KB")


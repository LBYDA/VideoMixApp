"""将 SVG 图标转换为 ICO 文件"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent.parent

# 由于 SVG 转 PNG 需要 cairosvg/resvg，这里直接生成一个简单的 ICO
# 使用 Pillow 直接绘制一个视频混剪图标

SIZES = [256, 128, 64, 48, 32, 16]

img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))

from PIL import ImageDraw

draw = ImageDraw.Draw(img)

# 背景圆角矩形
draw.rounded_rectangle([4, 4, 252, 252], radius=48, fill=(26, 26, 46, 255))

# 渐变色块（简化为纯色）
draw.rounded_rectangle([4, 4, 252, 252], radius=48, fill=(74, 144, 217, 255))
draw.rounded_rectangle([60, 4, 252, 252], radius=0, fill=(26, 26, 46, 255))

# 胶片框
draw.rounded_rectangle([44, 52, 212, 204], radius=12, outline=(255, 255, 255, 230), width=4)

# 胶片齿轮孔 - 左侧
for y in [72, 100, 128, 156]:
    draw.rounded_rectangle([40, y, 48, y + 12], radius=3, fill=(255, 255, 255, 230))

# 胶片齿轮孔 - 右侧
for y in [72, 100, 128, 156]:
    draw.rounded_rectangle([208, y, 216, y + 12], radius=3, fill=(255, 255, 255, 230))

# 播放三角
draw.polygon([108, 92, 108, 164, 164, 128], fill=(74, 144, 217, 240))

# 剪刀（简化为 X 形）
cx, cy = 182, 78
draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], outline=(255, 255, 255, 220), width=3)
draw.ellipse([cx - 10, cy + 14, cx + 10, cy + 34], outline=(255, 255, 255, 220), width=3)
draw.line([cx - 3, cy + 4, cx - 3, cy + 20], fill=(255, 255, 255, 220), width=3)
draw.line([cx + 3, cy + 4, cx + 3, cy + 20], fill=(255, 255, 255, 220), width=3)

# 字幕线条
sx, sy = 120, 182
for i, w in enumerate([24, 28, 20]):
    draw.rounded_rectangle([sx + sum([26, 30, 24][:i]) + (sum([24, 28][:i]) if i > 0 else 0), sy,
                           sx + sum([26, 30, 24][:i]) + (sum([24, 28, 20][:i])), sy + 4], radius=2, fill=(255, 255, 255, 180))
draw.rounded_rectangle([sx, sy + 12, sx + 40, sy + 16], radius=2, fill=(255, 255, 255, 180))

# 生成多尺寸 ICO
icons = []
for size in SIZES:
    resized = img.resize((size, size), Image.LANCZOS)
    icons.append(resized)

ico_path = ROOT / "frontend" / "public" / "favicon.ico"
icons[0].save(
    str(ico_path),
    format="ICO",
    sizes=[(s, s) for s in SIZES],
    append_images=icons[1:],
)

print(f"ICO 已生成: {ico_path}")
print(f"尺寸: {SIZES}")

"""生成 Idea Weaver 应用图标 —— 青色 'W' 圆形图标"""

from PIL import Image, ImageDraw, ImageFont


def generate_icon():
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆形青色底
    margin = 16
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill="#0891B2",
        outline="#06B6D4",
        width=4,
    )

    # 白色 W 字母
    try:
        font = ImageFont.truetype("segoeui.ttf", 120)
    except OSError:
        font = ImageFont.load_default()

    text = "W"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) / 2
    y = (size - th) / 2 - 10
    draw.text((x, y), text, fill="#FFFFFF", font=font)

    # 保存
    img.save("weaver.ico", format="ICO", sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("Icon generated: weaver.ico")


if __name__ == "__main__":
    generate_icon()

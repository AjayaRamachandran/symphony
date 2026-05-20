from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


OUT = Path("src-tauri/installer")
SCALE = 4

COLORS = {
    "background": "#222222",
    "foreground": "#d9d9d9",
    "muted": "#898989",
    "primary": "#ea7b36",
    "dark_primary": "#bc4512",
    "magenta": "#da0f90",
    "purple": "#8f00ff",
}


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def blend(left, right, t):
    lr, lg, lb = hex_to_rgb(left)
    rr, rg, rb = hex_to_rgb(right)
    return (
        round(lr + (rr - lr) * t),
        round(lg + (rg - lg) * t),
        round(lb + (rb - lb) * t),
    )


def load_font(size, bold=False):
    names = ("segoeuib.ttf", "arialbd.ttf") if bold else ("segoeui.ttf", "arial.ttf")
    for name in names:
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            return ImageFont.truetype(str(path), size * SCALE)
    return ImageFont.load_default()


def rounded_rect(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(
        tuple(v * SCALE for v in box),
        radius=radius * SCALE,
        fill=fill,
        outline=outline,
        width=width * SCALE,
    )


def gradient_rect(image, box, left, right, radius=0):
    x0, y0, x1, y1 = [v * SCALE for v in box]
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)

    for x in range(width):
        draw.line([(x, 0), (x, height)], fill=blend(left, right, x / max(1, width - 1)) + (255,))

    if radius:
        mask = Image.new("L", gradient.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((0, 0, width, height), radius=radius * SCALE, fill=255)
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        layer.paste(gradient, (x0, y0), mask)
        image.alpha_composite(layer)
    else:
        image.alpha_composite(gradient, (x0, y0))


def draw_tiles(draw, width, height, opacity=18):
    tile = 16
    for y in range(0, height + tile, tile):
        for x in range(0, width + tile, tile):
            shade = 40 + ((x // tile + y // tile) % 3) * 7
            draw.rounded_rectangle(
                (x * SCALE, y * SCALE, (x + tile - 2) * SCALE, (y + tile - 2) * SCALE),
                radius=2 * SCALE,
                fill=(shade, shade, shade, opacity),
            )


def draw_note(image, x, y, scale=1.0):
    draw = ImageDraw.Draw(image, "RGBA")
    s = SCALE * scale
    cx = x * SCALE
    cy = y * SCALE

    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((cx + 2 * s, cy + 2 * s, cx + 34 * s, cy + 54 * s), radius=7 * s, fill=(0, 0, 0, 90))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(2 * SCALE)))

    for yy in range(int(2 * s), int(45 * s)):
        t = yy / max(1, 45 * s)
        draw.rounded_rectangle(
            (cx + 20 * s, cy + yy, cx + 32 * s, cy + yy + 2 * s),
            radius=5 * s,
            fill=blend(COLORS["primary"], COLORS["magenta"], min(1, t)),
        )

    draw.rounded_rectangle((cx + 20 * s, cy + 2 * s, cx + 54 * s, cy + 18 * s), radius=5 * s, fill=hex_to_rgb(COLORS["magenta"]))
    draw.rounded_rectangle((cx + 3 * s, cy + 40 * s, cx + 33 * s, cy + 57 * s), radius=7 * s, fill=hex_to_rgb(COLORS["purple"]))
    draw.rounded_rectangle((cx - 6 * s, cy + 35 * s, cx + 14 * s, cy + 50 * s), radius=7 * s, fill=hex_to_rgb(COLORS["purple"]))


def save_bmp(image, path):
    image = image.resize((image.width // SCALE, image.height // SCALE), Image.Resampling.LANCZOS).convert("RGB")
    image.save(path, format="BMP")


def make_header():
    image = Image.new("RGBA", (150 * SCALE, 57 * SCALE), hex_to_rgb(COLORS["background"]) + (255,))
    draw = ImageDraw.Draw(image, "RGBA")

    draw_tiles(draw, 150, 57, opacity=24)
    for index, x in enumerate((-24, 18, 65, 109)):
        gradient_rect(image, (x, 43 - (index % 2) * 9, x + 52, 52 - (index % 2) * 9), COLORS["dark_primary"], COLORS["primary"], radius=2)

    rounded_rect(draw, (8, 8, 42, 42), 8, (18, 18, 18, 255), outline=(255, 255, 255, 18), width=1)
    draw_note(image, 13, 11, 0.45)
    draw.text((50 * SCALE, 11 * SCALE), "Symphony", font=load_font(15, True), fill=hex_to_rgb(COLORS["foreground"]) + (255,))
    draw.text((51 * SCALE, 30 * SCALE), "Installer", font=load_font(7), fill=hex_to_rgb(COLORS["muted"]) + (255,))
    save_bmp(image, OUT / "nsis-header.bmp")


def make_sidebar():
    image = Image.new("RGBA", (164 * SCALE, 314 * SCALE), hex_to_rgb(COLORS["background"]) + (255,))
    draw = ImageDraw.Draw(image, "RGBA")

    draw_tiles(draw, 164, 314, opacity=20)
    for y in range(314 * SCALE):
        t = y / max(1, 314 * SCALE - 1)
        draw.line([(0, y), (164 * SCALE, y)], fill=blend(COLORS["dark_primary"], COLORS["magenta"], t) + (32,))

    for x, y, width in ((-30, 118, 86), (42, 92, 132), (-8, 198, 112), (72, 170, 126), (-18, 260, 90)):
        gradient_rect(image, (x, y, x + width, y + 18), COLORS["dark_primary"], COLORS["primary"], radius=3)

    rounded_rect(draw, (33, 32, 131, 130), 22, (18, 18, 18, 238), outline=(255, 255, 255, 20), width=1)
    draw_note(image, 54, 52, 1.0)
    draw.text((30 * SCALE, 231 * SCALE), "Symphony", font=load_font(24, True), fill=hex_to_rgb(COLORS["foreground"]) + (255,))
    draw.text((31 * SCALE, 262 * SCALE), "Create something", font=load_font(10), fill=hex_to_rgb(COLORS["muted"]) + (255,))
    draw.text((31 * SCALE, 276 * SCALE), "amazing.", font=load_font(10), fill=hex_to_rgb(COLORS["muted"]) + (255,))
    save_bmp(image, OUT / "nsis-sidebar.bmp")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    make_header()
    make_sidebar()


if __name__ == "__main__":
    main()

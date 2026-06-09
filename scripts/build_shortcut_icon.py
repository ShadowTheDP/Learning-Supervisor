from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = PROJECT_ROOT / "app" / "static" / "icons"
ICO_PATH = ICON_DIR / "learning_supervisor.ico"
PREVIEW_PATH = ICON_DIR / "learning_supervisor_preview.png"

BG_TOP = (8, 19, 33, 255)
BG_BOTTOM = (2, 6, 11, 255)
CYAN = (57, 197, 255, 255)
MINT = (117, 247, 227, 255)
WARM = (255, 171, 92, 255)
TEXT = (243, 247, 251, 255)
PANEL = (15, 27, 45, 255)
SPINE = (6, 13, 24, 220)


def mix(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def lerp_color(start: tuple[int, int, int, int], end: tuple[int, int, int, int], t: float) -> tuple[int, int, int, int]:
    return tuple(mix(start[index], end[index], t) for index in range(4))


def add_vertical_gradient(image: Image.Image, top: tuple[int, int, int, int], bottom: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for y in range(height):
        t = y / max(1, height - 1)
        draw.line([(0, y), (width, y)], fill=lerp_color(top, bottom, t))


def apply_round_mask(image: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=radius, fill=255)
    rounded = Image.new("RGBA", image.size, (0, 0, 0, 0))
    rounded.paste(image, mask=mask)
    return rounded


def add_glow_blob(base: Image.Image, bbox: tuple[int, int, int, int], color: tuple[int, int, int, int], blur_radius: int) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(bbox, fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(blur_radius))
    base.alpha_composite(layer)


def add_grid(base: Image.Image, inset: int, spacing: int, color: tuple[int, int, int, int]) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    left = inset
    top = inset
    right = base.width - inset
    bottom = base.height - inset
    for x in range(left, right + 1, spacing):
        draw.line((x, top, x, bottom), fill=color, width=max(1, spacing // 14))
    for y in range(top, bottom + 1, spacing):
        draw.line((left, y, right, y), fill=color, width=max(1, spacing // 14))
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).ellipse((inset, inset, base.width - inset, base.height - inset), fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    base.alpha_composite(layer)


def add_orbit_arcs(base: Image.Image, box: tuple[int, int, int, int], width: int) -> None:
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.arc(box, start=208, end=348, fill=(57, 197, 255, 210), width=width + max(8, width // 2))
    glow_draw.arc(box, start=22, end=152, fill=(255, 171, 92, 190), width=width + max(8, width // 2))
    glow = glow.filter(ImageFilter.GaussianBlur(max(10, width // 2)))
    base.alpha_composite(glow)

    crisp = Image.new("RGBA", base.size, (0, 0, 0, 0))
    crisp_draw = ImageDraw.Draw(crisp)
    crisp_draw.arc(box, start=210, end=346, fill=(117, 247, 227, 255), width=width)
    crisp_draw.arc(box, start=26, end=148, fill=(255, 171, 92, 255), width=width)
    crisp_draw.ellipse(
        (
            int(base.width * 0.72),
            int(base.height * 0.19),
            int(base.width * 0.79),
            int(base.height * 0.26),
        ),
        fill=(255, 202, 142, 255),
    )
    crisp_draw.ellipse(
        (
            int(base.width * 0.16),
            int(base.height * 0.63),
            int(base.width * 0.22),
            int(base.height * 0.69),
        ),
        fill=(135, 242, 255, 240),
    )
    base.alpha_composite(crisp)


def polygon_shadow(base: Image.Image, points: list[tuple[float, float]], offset: tuple[int, int], blur_radius: int, alpha: int) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    shifted = [(int(x + offset[0]), int(y + offset[1])) for x, y in points]
    ImageDraw.Draw(layer).polygon(shifted, fill=(0, 0, 0, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(blur_radius))
    base.alpha_composite(layer)


def draw_book_mark(base: Image.Image) -> None:
    width = base.width
    height = base.height
    left_page = [
        (width * 0.28, height * 0.28),
        (width * 0.48, height * 0.22),
        (width * 0.48, height * 0.72),
        (width * 0.28, height * 0.78),
    ]
    right_page = [
        (width * 0.52, height * 0.22),
        (width * 0.72, height * 0.28),
        (width * 0.72, height * 0.78),
        (width * 0.52, height * 0.72),
    ]

    polygon_shadow(base, left_page, offset=(0, max(4, width // 40)), blur_radius=max(8, width // 18), alpha=96)
    polygon_shadow(base, right_page, offset=(0, max(4, width // 40)), blur_radius=max(8, width // 18), alpha=96)

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    draw.polygon(left_page, fill=(244, 248, 252, 255))
    draw.polygon(right_page, fill=(232, 241, 250, 255))

    inner_left = [
        (width * 0.31, height * 0.33),
        (width * 0.45, height * 0.29),
        (width * 0.45, height * 0.67),
        (width * 0.31, height * 0.71),
    ]
    inner_right = [
        (width * 0.55, height * 0.29),
        (width * 0.69, height * 0.33),
        (width * 0.69, height * 0.71),
        (width * 0.55, height * 0.67),
    ]
    draw.polygon(inner_left, fill=(220, 232, 245, 78))
    draw.polygon(inner_right, fill=(255, 255, 255, 52))

    draw.line(
        ((width * 0.5, height * 0.22), (width * 0.5, height * 0.73)),
        fill=SPINE,
        width=max(4, width // 36),
    )

    line_width = max(3, width // 52)
    for ratio in (0.39, 0.48, 0.57):
        draw.line(
            ((width * 0.34, height * ratio), (width * 0.43, height * (ratio - 0.03))),
            fill=(125, 170, 205, 118),
            width=line_width,
        )
        draw.line(
            ((width * 0.57, height * (ratio - 0.03)), (width * 0.66, height * ratio)),
            fill=(135, 175, 208, 112),
            width=line_width,
        )

    ribbon = [
        (width * 0.33, height * 0.23),
        (width * 0.4, height * 0.21),
        (width * 0.4, height * 0.45),
        (width * 0.365, height * 0.41),
        (width * 0.33, height * 0.47),
    ]
    draw.polygon(ribbon, fill=MINT)

    halo = Image.new("RGBA", base.size, (0, 0, 0, 0))
    halo_draw = ImageDraw.Draw(halo)
    halo_draw.rounded_rectangle(
        (
            int(width * 0.24),
            int(height * 0.18),
            int(width * 0.76),
            int(height * 0.8),
        ),
        radius=max(16, width // 10),
        outline=(117, 247, 227, 110),
        width=max(4, width // 48),
    )
    halo = halo.filter(ImageFilter.GaussianBlur(max(10, width // 24)))
    base.alpha_composite(halo)
    base.alpha_composite(layer)


def draw_icon(size: int) -> Image.Image:
    scale = 4
    canvas_size = size * scale
    base = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

    panel = Image.new("RGBA", base.size, (0, 0, 0, 0))
    add_vertical_gradient(panel, BG_TOP, BG_BOTTOM)
    panel = apply_round_mask(panel, radius=int(canvas_size * 0.24))
    base.alpha_composite(panel)

    add_glow_blob(base, (int(canvas_size * 0.05), int(canvas_size * 0.04), int(canvas_size * 0.58), int(canvas_size * 0.5)), (57, 197, 255, 44), int(canvas_size * 0.08))
    add_glow_blob(base, (int(canvas_size * 0.48), int(canvas_size * 0.08), int(canvas_size * 0.95), int(canvas_size * 0.46)), (255, 171, 92, 38), int(canvas_size * 0.08))
    add_glow_blob(base, (int(canvas_size * 0.18), int(canvas_size * 0.55), int(canvas_size * 0.76), int(canvas_size * 0.98)), (117, 247, 227, 26), int(canvas_size * 0.1))

    add_grid(base, inset=int(canvas_size * 0.14), spacing=max(18, canvas_size // 10), color=(255, 255, 255, 14))

    border = Image.new("RGBA", base.size, (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    inset = max(4, canvas_size // 48)
    border_draw.rounded_rectangle(
        (inset, inset, canvas_size - inset - 1, canvas_size - inset - 1),
        radius=int(canvas_size * 0.24),
        outline=(160, 231, 255, 52),
        width=max(4, canvas_size // 70),
    )
    base.alpha_composite(border)

    add_orbit_arcs(
        base,
        (
            int(canvas_size * 0.17),
            int(canvas_size * 0.15),
            int(canvas_size * 0.83),
            int(canvas_size * 0.81),
        ),
        width=max(12, canvas_size // 24),
    )
    draw_book_mark(base)

    corner = Image.new("RGBA", base.size, (0, 0, 0, 0))
    corner_draw = ImageDraw.Draw(corner)
    corner_draw.line(
        (
            (int(canvas_size * 0.13), int(canvas_size * 0.28)),
            (int(canvas_size * 0.13), int(canvas_size * 0.13)),
            (int(canvas_size * 0.28), int(canvas_size * 0.13)),
        ),
        fill=(117, 247, 227, 180),
        width=max(6, canvas_size // 64),
        joint="curve",
    )
    corner_draw.line(
        (
            (int(canvas_size * 0.72), int(canvas_size * 0.87)),
            (int(canvas_size * 0.87), int(canvas_size * 0.87)),
            (int(canvas_size * 0.87), int(canvas_size * 0.72)),
        ),
        fill=(255, 171, 92, 160),
        width=max(6, canvas_size // 64),
        joint="curve",
    )
    base.alpha_composite(corner)

    return base.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [draw_icon(size) for size in sizes]
    images[-1].save(ICO_PATH, format="ICO", sizes=[(size, size) for size in sizes])
    images[-1].save(PREVIEW_PATH, format="PNG")
    print(f"Saved icon: {ICO_PATH}")
    print(f"Saved preview: {PREVIEW_PATH}")


if __name__ == "__main__":
    main()

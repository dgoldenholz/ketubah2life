#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from scipy import ndimage


@dataclass
class TemplateRecord:
    index: int
    file: str
    source_file: str
    width: int
    height: int
    text_mask_coverage: float
    notes: str


def safe_stem(path: Path) -> str:
    return (
        path.stem.replace(" ", "_")
        .replace(".", "_")
        .replace("__", "_")
        .strip("_")[:70]
    )


def rgb_luma(arr: np.ndarray) -> np.ndarray:
    return arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152 + arr[..., 2] * 0.0722


def rgb_sat(arr: np.ndarray) -> np.ndarray:
    return arr.max(axis=2) - arr.min(axis=2)


def polish_photo(image: Image.Image) -> Image.Image:
    """Correct camera cast, uneven lighting, and soft capture without redrawing art."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    arr = np.asarray(image).astype(np.float32)
    lum = rgb_luma(arr)
    sat = rgb_sat(arr)

    bright_paper = (lum > np.percentile(lum, 72)) & (sat < 54)
    if int(bright_paper.sum()) < 500:
        bright_paper = lum > np.percentile(lum, 86)
    white_point = np.percentile(arr[bright_paper], 97.5, axis=0)
    white_point = np.maximum(white_point, 1.0)
    scale = np.clip(238.0 / white_point, 0.86, 1.23)
    arr = np.clip(arr * scale, 0, 255)

    lum = rgb_luma(arr)
    sigma = max(18.0, min(arr.shape[:2]) / 11.0)
    background = ndimage.gaussian_filter(lum, sigma=sigma)
    target = np.percentile(background, 62)
    factor = np.clip((target / np.maximum(background, 1.0)) ** 0.34, 0.78, 1.20)
    arr = np.clip(arr * factor[..., None], 0, 255)

    out = Image.fromarray(arr.astype(np.uint8), "RGB")
    out = ImageEnhance.Color(out).enhance(1.13)
    out = ImageEnhance.Contrast(out).enhance(1.055)
    out = ImageEnhance.Brightness(out).enhance(1.015)
    out = out.filter(ImageFilter.UnsharpMask(radius=1.15, percent=105, threshold=3))
    return out


def source_family(name: str) -> str:
    n = name.lower()
    exact = {
        "67504011272": "crown_heart",
        "69430228040": "botanical_gold_circle",
        "71409079192": "minimal_gold_circle",
        "71555476231": "peacock_arch",
        "71573576103": "branch_circle",
        "img_0280": "tree_trunk",
        "img_0281": "musical_s_curve",
        "img_0290": "ring_circle",
        "img_0298": "bold_ring_circle",
        "img_0319": "hamsa_outline",
        "img_0439": "floral_rectangle",
        "img_0445": "vivid_heart_swirl",
        "img_0519": "ornate_scroll_frame",
        "img_0608": "two_trees",
        "img_0652": "rose_garland",
        "img_0678": "floral_canopy",
        "img_0710": "round_wreath",
        "img_0813": "crown_scroll",
        "img_0879": "rose_garland",
        "img_1014": "sun_ocean",
        "img_1186": "pastel_s_cloud",
        "img_1250": "floral_s_curve",
        "img_1264": "side_floral_circle",
        "img_1372": "blue_wreath",
        "img_1390": "blue_wreath",
        "img_1399": "playful_heart",
        "img_1404": "side_floral_circle",
        "img_1422": "purple_roundel",
        "img_1580": "crown_heart",
        "img_1627": "infinity_loop",
        "img_1768": "figure_eight",
        "img_2014": "pale_rose_rectangle",
        "img_2022": "minimal_gold_circle",
        "img_2333": "leaf_silhouette",
        "img_2382": "blue_wreath",
        "img_2693": "hamsa_floral",
        "img_2718": "blue_mandala",
        "img_2853": "gold_rings_minimal",
        "img_2858": "wildflower_rectangle",
        "img_2860": "eucalyptus_wreath",
        "img_2875": "eucalyptus_wreath",
        "img_2881": "abstract_calligraphy",
        "img_3557": "framed_s_panel",
        "img_3561": "lace_hamsa",
        "img_3682": "celebration_swash",
        "img_3723": "gold_arch",
        "img_3777": "red_roundel",
    }
    for key, family in exact.items():
        if key in n:
            return family
    return "generic_center"


def box_px(box: tuple[float, float, float, float], size: tuple[int, int]) -> tuple[int, int, int, int]:
    w, h = size
    return (round(box[0] * w), round(box[1] * h), round(box[2] * w), round(box[3] * h))


def draw_ellipse(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], size: tuple[int, int]) -> None:
    draw.ellipse(box_px(box, size), fill=255)


def draw_rect(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], size: tuple[int, int]) -> None:
    draw.rounded_rectangle(box_px(box, size), radius=max(6, min(size) // 95), fill=255)


def draw_polygon(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], size: tuple[int, int]) -> None:
    w, h = size
    draw.polygon([(round(x * w), round(y * h)) for x, y in points], fill=255)


def draw_ellipse_outline(
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    size: tuple[int, int],
    width_frac: float = 0.035,
) -> None:
    width = max(8, round(min(size) * width_frac))
    draw.ellipse(box_px(box, size), outline=255, width=width)


def draw_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    size: tuple[int, int],
    width_frac: float,
) -> None:
    w, h = size
    width = max(10, round(min(size) * width_frac))
    xy = [(round(x * w), round(y * h)) for x, y in points]
    draw.line(xy, fill=255, width=width, joint="curve")


def draw_heart(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], size: tuple[int, int]) -> None:
    x0, y0, x1, y1 = box_px(box, size)
    bw = x1 - x0
    bh = y1 - y0
    pts: list[tuple[int, int]] = []
    for i in range(180):
        t = 2 * math.pi * i / 180
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((round(x0 + bw * (x + 17) / 34), round(y0 + bh * (y + 17) / 34)))
    draw.polygon(pts, fill=255)


def draw_arch(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], size: tuple[int, int]) -> None:
    x0, y0, x1, y1 = box_px(box, size)
    width = x1 - x0
    top_h = max(1, width // 2)
    draw.rectangle((x0, y0 + top_h // 2, x1, y1), fill=255)
    draw.ellipse((x0, y0, x1, y0 + top_h), fill=255)


def draw_hamsa(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], size: tuple[int, int]) -> None:
    x0, y0, x1, y1 = box_px(box, size)
    w = x1 - x0
    h = y1 - y0
    pts = [
        (x0 + 0.50 * w, y0 + 0.00 * h),
        (x0 + 0.70 * w, y0 + 0.08 * h),
        (x0 + 0.78 * w, y0 + 0.31 * h),
        (x0 + 1.00 * w, y0 + 0.33 * h),
        (x0 + 0.83 * w, y0 + 0.55 * h),
        (x0 + 0.70 * w, y0 + 0.78 * h),
        (x0 + 0.50 * w, y0 + 1.00 * h),
        (x0 + 0.30 * w, y0 + 0.78 * h),
        (x0 + 0.17 * w, y0 + 0.55 * h),
        (x0 + 0.00 * w, y0 + 0.33 * h),
        (x0 + 0.22 * w, y0 + 0.31 * h),
        (x0 + 0.30 * w, y0 + 0.08 * h),
    ]
    draw.polygon([(round(x), round(y)) for x, y in pts], fill=255)
    draw.ellipse((x0 + 0.23 * w, y0 + 0.14 * h, x0 + 0.77 * w, y0 + 0.58 * h), fill=255)


def add_common_circle(draw: ImageDraw.ImageDraw, size: tuple[int, int], box=(0.25, 0.22, 0.75, 0.72)) -> None:
    inner = (box[0] - 0.035, box[1] - 0.035, box[2] + 0.035, box[3] + 0.035)
    outer = (box[0] - 0.080, box[1] - 0.080, box[2] + 0.080, box[3] + 0.080)
    draw_ellipse(draw, inner, size)
    draw_ellipse_outline(draw, outer, size, 0.058)


def make_text_field_mask(image: Image.Image, source_name: str) -> np.ndarray:
    size = image.size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    family = source_family(source_name)

    if family == "crown_heart":
        draw_heart(draw, (0.14, 0.25, 0.88, 0.80), size)
        draw_ellipse(draw, (0.15, 0.32, 0.86, 0.76), size)
        draw_rect(draw, (0.18, 0.38, 0.84, 0.68), size)
    elif family == "botanical_gold_circle":
        add_common_circle(draw, size, (0.25, 0.25, 0.75, 0.71))
        draw_rect(draw, (0.28, 0.14, 0.72, 0.30), size)
        draw_rect(draw, (0.29, 0.66, 0.71, 0.80), size)
    elif family == "minimal_gold_circle":
        add_common_circle(draw, size, (0.24, 0.20, 0.76, 0.70))
        draw_ellipse(draw, (0.05, 0.03, 0.95, 0.92), size)
        draw_rect(draw, (0.22, 0.08, 0.78, 0.28), size)
        draw_rect(draw, (0.23, 0.62, 0.77, 0.82), size)
    elif family == "peacock_arch":
        draw_arch(draw, (0.30, 0.13, 0.74, 0.76), size)
        draw_rect(draw, (0.34, 0.67, 0.70, 0.82), size)
    elif family == "branch_circle":
        add_common_circle(draw, size, (0.25, 0.25, 0.75, 0.71))
        draw_rect(draw, (0.29, 0.15, 0.71, 0.31), size)
        draw_rect(draw, (0.29, 0.66, 0.71, 0.80), size)
    elif family == "tree_trunk":
        draw_rect(draw, (0.00, 0.26, 0.45, 0.90), size)
        draw_rect(draw, (0.51, 0.26, 1.00, 0.90), size)
        draw_rect(draw, (0.16, 0.04, 0.84, 0.21), size)
    elif family == "musical_s_curve":
        draw_polygon(draw, [(0.18, 0.08), (0.64, 0.10), (0.69, 0.32), (0.54, 0.52), (0.70, 0.80), (0.52, 0.96), (0.10, 0.88), (0.24, 0.58), (0.10, 0.30)], size)
        draw_rect(draw, (0.00, 0.05, 0.82, 0.96), size)
        draw_ellipse(draw, (0.06, 0.06, 0.74, 0.94), size)
        draw_rect(draw, (0.06, 0.10, 0.74, 0.90), size)
        draw_line(draw, [(0.54, 0.08), (0.44, 0.30), (0.50, 0.52), (0.63, 0.74), (0.52, 0.94)], size, 0.20)
    elif family in {"ring_circle", "bold_ring_circle", "round_wreath", "purple_roundel", "red_roundel"}:
        add_common_circle(draw, size, (0.20, 0.16, 0.80, 0.78))
        draw_ellipse(draw, (0.03, 0.00, 0.97, 0.96), size)
        draw_ellipse_outline(draw, (0.06, 0.03, 0.94, 0.93), size, 0.115)
        draw_rect(draw, (0.08, 0.05, 0.92, 0.25), size)
        draw_rect(draw, (0.08, 0.74, 0.92, 0.94), size)
    elif family == "hamsa_outline":
        draw_hamsa(draw, (0.15, 0.11, 0.85, 0.82), size)
        draw_rect(draw, (0.28, 0.16, 0.72, 0.72), size)
    elif family == "floral_rectangle":
        draw_rect(draw, (0.04, 0.03, 0.96, 0.23), size)
        draw_rect(draw, (0.36, 0.21, 0.93, 0.70), size)
        draw_rect(draw, (0.36, 0.69, 0.91, 0.79), size)
        draw_rect(draw, (0.38, 0.79, 0.90, 0.94), size)
    elif family == "vivid_heart_swirl":
        draw_ellipse(draw, (0.16, 0.08, 0.66, 0.57), size)
        draw_ellipse(draw, (0.56, 0.23, 0.94, 0.62), size)
        draw_rect(draw, (0.35, 0.58, 0.80, 0.78), size)
        draw_rect(draw, (0.42, 0.78, 0.78, 0.91), size)
    elif family == "ornate_scroll_frame":
        draw_rect(draw, (0.28, 0.23, 0.72, 0.73), size)
        draw_rect(draw, (0.26, 0.74, 0.74, 0.84), size)
    elif family == "two_trees":
        add_common_circle(draw, size, (0.18, 0.14, 0.82, 0.78))
        draw_ellipse_outline(draw, (0.08, 0.06, 0.92, 0.90), size, 0.090)
        draw_rect(draw, (0.16, 0.82, 0.84, 0.96), size)
    elif family in {"rose_garland", "floral_canopy"}:
        add_common_circle(draw, size, (0.18, 0.14, 0.82, 0.76))
        draw_ellipse(draw, (0.02, 0.02, 0.98, 0.94), size)
        draw_rect(draw, (0.05, 0.68, 0.94, 0.92), size)
    elif family == "crown_scroll":
        draw_rect(draw, (0.05, 0.14, 0.93, 0.74), size)
        draw_rect(draw, (0.08, 0.70, 0.90, 0.91), size)
    elif family == "sun_ocean":
        draw_ellipse(draw, (0.22, 0.33, 0.75, 0.62), size)
        draw_rect(draw, (0.28, 0.58, 0.72, 0.75), size)
    elif family == "pastel_s_cloud":
        draw_polygon(draw, [(0.22, 0.06), (0.54, 0.10), (0.55, 0.36), (0.42, 0.52), (0.54, 0.82), (0.40, 0.94), (0.12, 0.86), (0.27, 0.58), (0.16, 0.30)], size)
        draw_rect(draw, (0.00, 0.02, 0.92, 0.97), size)
        draw_line(draw, [(0.43, 0.06), (0.38, 0.32), (0.46, 0.55), (0.49, 0.80)], size, 0.15)
    elif family == "floral_s_curve":
        draw_ellipse(draw, (0.34, 0.20, 0.74, 0.70), size)
        draw_ellipse(draw, (0.04, 0.04, 0.96, 0.92), size)
        draw_rect(draw, (0.03, 0.04, 0.97, 0.14), size)
        draw_rect(draw, (0.02, 0.14, 0.12, 0.92), size)
        draw_rect(draw, (0.88, 0.14, 0.98, 0.92), size)
        draw_rect(draw, (0.14, 0.83, 0.86, 0.96), size)
    elif family == "side_floral_circle":
        add_common_circle(draw, size, (0.19, 0.13, 0.81, 0.77))
        draw_ellipse(draw, (0.02, 0.00, 0.98, 0.94), size)
        draw_ellipse_outline(draw, (0.08, 0.04, 0.92, 0.88), size, 0.080)
        draw_rect(draw, (0.30, 0.70, 0.70, 0.82), size)
    elif family == "blue_wreath":
        add_common_circle(draw, size, (0.19, 0.16, 0.81, 0.78))
        draw_ellipse(draw, (0.12, 0.09, 0.88, 0.86), size)
        draw_rect(draw, (0.29, 0.72, 0.71, 0.84), size)
    elif family == "playful_heart":
        draw_heart(draw, (0.48, 0.04, 0.96, 0.45), size)
        draw_ellipse(draw, (0.48, 0.05, 0.96, 0.42), size)
        draw_rect(draw, (0.28, 0.35, 0.96, 0.86), size)
    elif family == "infinity_loop":
        draw_ellipse(draw, (0.28, 0.53, 0.84, 0.86), size)
        draw_rect(draw, (0.32, 0.54, 0.80, 0.87), size)
    elif family == "figure_eight":
        draw_ellipse(draw, (0.36, 0.18, 0.70, 0.54), size)
        draw_ellipse(draw, (0.35, 0.52, 0.73, 0.90), size)
        draw_rect(draw, (0.02, 0.05, 0.13, 0.94), size)
        draw_rect(draw, (0.87, 0.05, 0.98, 0.94), size)
        draw_rect(draw, (0.10, 0.02, 0.90, 0.10), size)
        draw_rect(draw, (0.10, 0.90, 0.90, 0.98), size)
    elif family == "pale_rose_rectangle":
        draw_rect(draw, (0.18, 0.12, 0.82, 0.76), size)
        draw_rect(draw, (0.20, 0.72, 0.80, 0.88), size)
    elif family == "leaf_silhouette":
        draw_polygon(draw, [(0.30, 0.04), (0.82, 0.12), (0.82, 0.50), (0.62, 0.96), (0.20, 0.82), (0.22, 0.36)], size)
        draw_rect(draw, (0.05, 0.03, 0.96, 0.96), size)
    elif family == "hamsa_floral":
        draw_hamsa(draw, (0.16, 0.08, 0.86, 0.86), size)
        draw_rect(draw, (0.20, 0.14, 0.83, 0.86), size)
    elif family == "blue_mandala":
        add_common_circle(draw, size, (0.23, 0.25, 0.77, 0.74))
    elif family == "gold_rings_minimal":
        draw_rect(draw, (0.00, 0.00, 0.94, 0.92), size)
        draw_rect(draw, (0.10, 0.68, 0.90, 0.92), size)
        draw_ellipse_outline(draw, (0.22, 0.06, 0.74, 0.76), size, 0.035)
    elif family == "wildflower_rectangle":
        draw_rect(draw, (0.25, 0.18, 0.75, 0.72), size)
        draw_rect(draw, (0.24, 0.72, 0.76, 0.84), size)
    elif family == "eucalyptus_wreath":
        add_common_circle(draw, size, (0.22, 0.20, 0.78, 0.75))
    elif family == "abstract_calligraphy":
        draw_rect(draw, (0.00, 0.00, 0.76, 0.96), size)
        draw_rect(draw, (0.58, 0.10, 0.84, 0.84), size)
    elif family == "framed_s_panel":
        draw_rect(draw, (0.35, 0.18, 0.66, 0.78), size)
    elif family == "lace_hamsa":
        draw_hamsa(draw, (0.12, 0.08, 0.88, 0.86), size)
        draw_rect(draw, (0.18, 0.14, 0.82, 0.86), size)
    elif family == "celebration_swash":
        draw_rect(draw, (0.00, 0.00, 0.96, 0.92), size)
    elif family == "gold_arch":
        draw_arch(draw, (0.15, 0.08, 0.85, 0.88), size)
        draw_rect(draw, (0.18, 0.18, 0.82, 0.92), size)
    else:
        draw_rect(draw, (0.24, 0.18, 0.76, 0.78), size)

    mask_arr = np.asarray(mask) > 0
    mask_arr = ndimage.binary_dilation(mask_arr, iterations=max(1, min(size) // 900))
    mask_arr = ndimage.binary_closing(mask_arr, iterations=1)
    return mask_arr


def rebuild_text_fields(image: Image.Image, mask: np.ndarray) -> Image.Image:
    if not bool(mask.any()):
        return image

    arr = np.asarray(image.convert("RGB")).astype(np.float32)
    h, w = mask.shape
    blurred = np.empty_like(arr)
    blur_sigma = max(18.0, min(h, w) / 22.0)
    for channel in range(3):
        blurred[..., channel] = ndimage.gaussian_filter(arr[..., channel], sigma=blur_sigma)

    result = arr.copy()
    labels, _ = ndimage.label(mask)
    objects = ndimage.find_objects(labels)
    lum = rgb_luma(arr)

    for label_id, slc in enumerate(objects, start=1):
        if slc is None:
            continue
        comp = labels[slc] == label_id
        full_comp = labels == label_id
        ring_iterations = max(10, min(h, w) // 65)
        ring = ndimage.binary_dilation(full_comp, iterations=ring_iterations) & ~mask
        samples = arr[ring]
        if samples.size == 0:
            samples = arr[~mask]
        if samples.size == 0:
            samples = arr.reshape(-1, 3)

        sample_lum = rgb_luma(samples.reshape(-1, 1, 3)).reshape(-1)
        usable = samples[sample_lum > max(42, float(np.percentile(sample_lum, 18)))]
        if len(usable) < 100:
            usable = samples
        median = np.median(usable, axis=0)

        yy, xx = np.where(full_comp)
        region_fill = blurred[yy, xx] * 0.48 + median * 0.52
        result[yy, xx] = region_fill

    noise = np.random.default_rng(1337).normal(0, 1.6, size=result.shape).astype(np.float32)
    result[mask] = np.clip(result[mask] + noise[mask], 0, 255)

    alpha = ndimage.gaussian_filter(mask.astype(np.float32), sigma=max(1.4, min(h, w) / 1050.0))
    alpha = np.clip(alpha, 0, 1)[..., None]
    blended = arr * (1 - alpha) + result * alpha
    return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8), "RGB")


def create_mask_preview(source: Image.Image, mask: np.ndarray) -> Image.Image:
    base = source.convert("RGB")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    red = np.zeros((base.height, base.width, 4), dtype=np.uint8)
    red[mask] = (255, 0, 0, 118)
    overlay = Image.fromarray(red, "RGBA")
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


def build_contact_sheets(records: list[TemplateRecord], source_dir: Path, out_dir: Path, sheet_dir: Path) -> None:
    sheet_dir.mkdir(parents=True, exist_ok=True)
    thumb_w, thumb_h = 210, 280
    cell_w, cell_h = 455, 334
    cols = 2
    rows = 4
    per_sheet = cols * rows

    for sheet_index in range(0, len(records), per_sheet):
        chunk = records[sheet_index : sheet_index + per_sheet]
        sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (239, 238, 233))
        draw = ImageDraw.Draw(sheet)
        for i, rec in enumerate(chunk):
            x = (i % cols) * cell_w
            y = (i // cols) * cell_h
            src = Image.open(source_dir / rec.source_file).convert("RGB")
            dst = Image.open(out_dir / rec.file).convert("RGB")
            src.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            dst.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            sheet.paste(src, (x + 8 + (thumb_w - src.width) // 2, y + 8))
            sheet.paste(dst, (x + 236 + (thumb_w - dst.width) // 2, y + 8))
            draw.text((x + 8, y + 294), f"{rec.index:02d} source", fill=(35, 35, 35))
            draw.text((x + 236, y + 294), "cleaned template", fill=(35, 35, 35))
            draw.text((x + 8, y + 312), rec.source_file[:52], fill=(75, 75, 75))
        sheet_no = sheet_index // per_sheet + 1
        sheet.save(sheet_dir / f"source_cleanup_contact_sheet_{sheet_no:02d}.jpg", quality=92)


def write_metadata(records: list[TemplateRecord], root: Path) -> None:
    with (root / "metadata.json").open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, indent=2)
    with (root / "metadata.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(records[0]).keys()))
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def process_source(path: Path, out_path: Path, mask_path: Path | None) -> tuple[Image.Image, float]:
    source = Image.open(path)
    polished = polish_photo(source)

    combined_mask = make_text_field_mask(polished, path.name)
    working = rebuild_text_fields(polished, combined_mask)

    final = ImageEnhance.Color(working).enhance(1.035)
    final = ImageEnhance.Contrast(final).enhance(1.018)
    final = final.filter(ImageFilter.UnsharpMask(radius=0.8, percent=70, threshold=2))
    final.save(out_path)

    if mask_path is not None:
        create_mask_preview(polished, combined_mask).save(mask_path, quality=90)

    return final, float(combined_mask.mean())


def build_templates(source_dir: Path, output_root: Path, write_masks: bool) -> list[TemplateRecord]:
    source_files = sorted(source_dir.glob("*.png"))
    if not source_files:
        raise SystemExit(f"No rendered source PNGs found in {source_dir}")

    template_dir = output_root / "source_templates"
    mask_dir = output_root / "mask_previews"
    template_dir.mkdir(parents=True, exist_ok=True)
    if write_masks:
        mask_dir.mkdir(parents=True, exist_ok=True)

    records: list[TemplateRecord] = []
    for index, path in enumerate(source_files, start=1):
        out_name = f"source_template_{index:02d}_{safe_stem(path)}.png"
        out_path = template_dir / out_name
        mask_path = mask_dir / f"mask_{index:02d}_{safe_stem(path)}.jpg" if write_masks else None
        final, coverage = process_source(path, out_path, mask_path)
        records.append(
            TemplateRecord(
                index=index,
                file=out_name,
                source_file=path.name,
                width=final.width,
                height=final.height,
                text_mask_coverage=round(coverage, 5),
                notes="Photo-preserving source cleanup: lighting/color correction, text stroke removal, local paper texture reconstruction.",
            )
        )
        print(f"{index:02d}/{len(source_files)} {path.name} -> {out_name} mask={coverage:.3%}")

    build_contact_sheets(records, source_dir, template_dir, output_root / "contact_sheets")
    write_metadata(records, output_root)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Build close-to-source, text-free ketubah templates from rendered photos.")
    parser.add_argument("--source-dir", type=Path, default=Path("template_work/rendered_originals"))
    parser.add_argument("--output-root", type=Path, default=Path("artist_source_templates"))
    parser.add_argument("--mask-previews", action="store_true", help="Write red overlay previews of removed text/blemish masks.")
    args = parser.parse_args()

    records = build_templates(args.source_dir, args.output_root, args.mask_previews)
    print(f"Wrote {len(records)} close-to-source templates to {args.output_root / 'source_templates'}")


if __name__ == "__main__":
    main()

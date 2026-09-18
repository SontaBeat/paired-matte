#!/usr/bin/env python3
"""Build, normalize, inspect, and validate aligned solid-background assets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageFilter, ImageOps
except ImportError as exc:  # pragma: no cover - environment dependent
    raise SystemExit(
        "Pillow is required. Install it with `python3 -m pip install Pillow` "
        "or the active environment's package manager."
    ) from exc


DEFAULT_BACKGROUND = (128, 128, 128)


def existing_file(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"file does not exist: {path}")
    return path


def output_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if path.suffix.lower() != ".png":
        raise argparse.ArgumentTypeError("output must use the .png extension")
    return path


def parse_color(value: str) -> tuple[int, int, int]:
    normalized = value.strip().removeprefix("#")
    if len(normalized) != 6:
        raise argparse.ArgumentTypeError("color must be a six-digit hex value such as #808080")
    try:
        color = tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("color must contain only hexadecimal digits") from exc
    return color  # type: ignore[return-value]


def color_hex(color: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02X}" for channel in color)


def require_writable_output(path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"Refusing to overwrite existing output: {path}. Use --force to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)


def source_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def load_rgb(path: Path, target_size: tuple[int, int] | None = None) -> Image.Image:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        if target_size is not None and rgb.size != target_size:
            rgb = rgb.resize(target_size, Image.Resampling.LANCZOS)
        return rgb


def load_mask(path: Path, target_size: tuple[int, int] | None = None) -> tuple[Image.Image, float]:
    rgb = load_rgb(path, target_size)
    grayscale = ImageOps.grayscale(rgb)
    channels = rgb.split()
    chroma = ImageChops.lighter(
        ImageChops.difference(channels[0], channels[1]),
        ImageChops.difference(channels[1], channels[2]),
    )
    chroma = ImageChops.lighter(chroma, ImageChops.difference(channels[0], channels[2]))
    non_neutral = sum(chroma.histogram()[4:])
    chroma_ratio = non_neutral / (rgb.width * rgb.height)
    return grayscale, chroma_ratio


def clamp_mask(mask: Image.Image, black_threshold: int, white_threshold: int) -> Image.Image:
    if not 0 <= black_threshold < white_threshold <= 255:
        raise SystemExit("Require 0 <= --black-threshold < --white-threshold <= 255")
    lookup = [
        0 if value <= black_threshold else 255 if value >= white_threshold else value
        for value in range(256)
    ]
    return mask.point(lookup, mode="L")


def mask_stats(mask: Image.Image) -> dict[str, int]:
    histogram = mask.histogram()
    black = histogram[0]
    white = histogram[255]
    total = mask.width * mask.height
    return {"black": black, "white": white, "gray": total - black - white, "total": total}


def print_mask_report(mask: Image.Image, chroma_ratio: float) -> None:
    stats = mask_stats(mask)
    print(
        "mask "
        f"size={mask.width}x{mask.height} mode={mask.mode} "
        f"black={stats['black']} white={stats['white']} gray={stats['gray']} "
        f"non_neutral_input={chroma_ratio:.4%}"
    )
    if chroma_ratio > 0.001:
        print("warning: model mask contained colored pixels; converted to neutral grayscale", file=sys.stderr)
    if stats["black"] == 0:
        print("warning: mask has no pure-black pixels; inspect a full-frame subject carefully", file=sys.stderr)
    if stats["white"] == 0:
        print("warning: mask has no pure-white pixels; this is valid only for a fully translucent subject", file=sys.stderr)


def source_info(args: argparse.Namespace) -> None:
    with Image.open(args.source_image) as image:
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A")
        histogram = alpha.histogram()
        transparent = histogram[0]
        opaque = histogram[255]
        partial = rgba.width * rgba.height - transparent - opaque
        meaningful_alpha = transparent > 0 or partial > 0
        print(
            f"source size={rgba.width}x{rgba.height} mode={image.mode} "
            f"meaningful_alpha={'yes' if meaningful_alpha else 'no'} "
            f"alpha_transparent={transparent} alpha_opaque={opaque} alpha_partial={partial}"
        )


def from_alpha(args: argparse.Namespace) -> None:
    with Image.open(args.source_image) as image:
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A")
        histogram = alpha.histogram()
        meaningful_alpha = histogram[0] > 0 or sum(histogram[1:255]) > 0
        if not meaningful_alpha:
            raise SystemExit("Source has no meaningful alpha channel; use the image-generation workflow.")

        background = Image.new("RGBA", rgba.size, args.background + (255,))
        solid = Image.alpha_composite(background, rgba).convert("RGB")

    require_writable_output(args.solid_out, args.force)
    require_writable_output(args.mask_out, args.force)
    solid.save(args.solid_out, format="PNG", optimize=True)
    alpha.save(args.mask_out, format="PNG", optimize=True)
    print(
        f"from-alpha size={solid.width}x{solid.height} "
        f"background={color_hex(args.background)} mask_mode=L"
    )
    print(f"saved {args.solid_out}")
    print(f"saved {args.mask_out}")


def normalize_mask(args: argparse.Namespace) -> None:
    target_size = source_size(args.source_image)
    mask, chroma_ratio = load_mask(args.mask_image, target_size)
    mask = clamp_mask(mask, args.black_threshold, args.white_threshold)
    require_writable_output(args.mask_out, args.force)
    mask.save(args.mask_out, format="PNG", optimize=True)
    print_mask_report(mask, chroma_ratio)
    print(f"saved {args.mask_out}")


def finalize_solid(args: argparse.Namespace) -> None:
    target_size = source_size(args.source_image)
    mask, _ = load_mask(args.mask_image, target_size)
    solid_image = load_rgb(args.solid_image, target_size)

    keep_generated = mask.point([0 if value == 0 else 255 for value in range(256)], mode="L")
    background = Image.new("RGB", target_size, args.background)
    final = Image.composite(solid_image, background, keep_generated)

    require_writable_output(args.solid_out, args.force)
    final.save(args.solid_out, format="PNG", optimize=True)
    exact_background_pixels = mask.histogram()[0]
    print(
        f"solid size={final.width}x{final.height} mode={final.mode} "
        f"exact_background_pixels={exact_background_pixels} "
        f"background={color_hex(args.background)}"
    )
    print(f"saved {args.solid_out}")


def alignment_overlay(args: argparse.Namespace) -> None:
    target_size = source_size(args.source_image)
    solid = load_rgb(args.solid_image, target_size)
    mask, _ = load_mask(args.mask_image, target_size)
    binary = mask.point([255 if value > args.mask_threshold else 0 for value in range(256)], mode="L")
    kernel_size = args.edge_width * 2 + 1
    dilated = binary.filter(ImageFilter.MaxFilter(kernel_size))
    eroded = binary.filter(ImageFilter.MinFilter(kernel_size))
    edge = ImageChops.subtract(dilated, eroded)
    outline = Image.new("RGB", target_size, args.outline_color)
    overlay = Image.composite(outline, solid, edge)

    require_writable_output(args.overlay_out, args.force)
    overlay.save(args.overlay_out, format="PNG", optimize=True)
    edge_pixels = sum(edge.histogram()[1:])
    print(
        f"overlay size={overlay.width}x{overlay.height} edge_pixels={edge_pixels} "
        f"outline={color_hex(args.outline_color)}"
    )
    print(f"saved {args.overlay_out}")


def validate(args: argparse.Namespace) -> None:
    target_size = source_size(args.source_image)
    failures: list[str] = []

    with Image.open(args.mask_image) as raw_mask:
        if raw_mask.size != target_size:
            failures.append(f"mask size {raw_mask.size} does not match source {target_size}")
        if raw_mask.mode != "L":
            failures.append(f"mask mode is {raw_mask.mode}, expected L")
        mask = raw_mask.convert("L")

    with Image.open(args.solid_image) as raw_solid:
        if raw_solid.size != target_size:
            failures.append(f"solid image size {raw_solid.size} does not match source {target_size}")
        solid = raw_solid.convert("RGB")

    if mask.size == solid.size:
        mask_pixels = mask.load()
        solid_pixels = solid.load()
        wrong_background = 0
        zero_pixels = 0
        for y in range(mask.height):
            for x in range(mask.width):
                if mask_pixels[x, y] == 0:
                    zero_pixels += 1
                    if solid_pixels[x, y] != args.background:
                        wrong_background += 1
        if wrong_background:
            failures.append(
                f"{wrong_background} of {zero_pixels} zero-mask pixels are not exact "
                f"RGB {args.background}"
            )

    stats = mask_stats(mask)
    if args.require_black and stats["black"] == 0:
        failures.append("mask contains no pure-black pixels")
    if args.require_white and stats["white"] == 0:
        failures.append("mask contains no pure-white pixels")

    print(
        f"validated source={target_size[0]}x{target_size[1]} "
        f"background={color_hex(args.background)} "
        f"mask_black={stats['black']} mask_white={stats['white']} mask_gray={stats['gray']}"
    )
    if failures:
        for failure in failures:
            print(f"error: {failure}", file=sys.stderr)
        raise SystemExit(1)
    if stats["black"] == 0:
        print("warning: no pure-black pixels; confirm the subject intentionally fills the canvas", file=sys.stderr)
    if stats["white"] == 0:
        print("warning: no pure-white pixels; confirm the subject is intentionally fully translucent", file=sys.stderr)
    print("validation passed")


def add_background(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--background",
        type=parse_color,
        default=DEFAULT_BACKGROUND,
        help="solid background as six-digit hex; default #808080",
    )


def add_shared_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-image", type=existing_file, required=True)


def add_force(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--force", action="store_true")


def add_finalize_parser(subparsers: argparse._SubParsersAction, name: str, help_text: str) -> None:
    parser = subparsers.add_parser(name, help=help_text)
    add_shared_inputs(parser)
    parser.add_argument("--solid-image", "--gray-image", dest="solid_image", type=existing_file, required=True)
    parser.add_argument("--mask-image", type=existing_file, required=True)
    parser.add_argument("--solid-out", "--gray-out", dest="solid_out", type=output_path, required=True)
    add_background(parser)
    add_force(parser)
    parser.set_defaults(handler=finalize_solid)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    info_parser = subparsers.add_parser("source-info", help="report dimensions and meaningful alpha")
    add_shared_inputs(info_parser)
    info_parser.set_defaults(handler=source_info)

    alpha_parser = subparsers.add_parser("from-alpha", help="build an exact pair from source alpha")
    add_shared_inputs(alpha_parser)
    alpha_parser.add_argument("--solid-out", type=output_path, required=True)
    alpha_parser.add_argument("--mask-out", type=output_path, required=True)
    add_background(alpha_parser)
    add_force(alpha_parser)
    alpha_parser.set_defaults(handler=from_alpha)

    mask_parser = subparsers.add_parser("normalize-mask", help="resize, grayscale, and clamp a model mask")
    add_shared_inputs(mask_parser)
    mask_parser.add_argument("--mask-image", type=existing_file, required=True)
    mask_parser.add_argument("--mask-out", type=output_path, required=True)
    mask_parser.add_argument("--black-threshold", type=int, default=8)
    mask_parser.add_argument("--white-threshold", type=int, default=247)
    add_force(mask_parser)
    mask_parser.set_defaults(handler=normalize_mask)

    add_finalize_parser(subparsers, "finalize-solid", "restore source size and enforce a solid background")
    add_finalize_parser(subparsers, "finalize-gray", "compatibility alias for finalize-solid")

    overlay_parser = subparsers.add_parser(
        "alignment-overlay",
        help="draw the normalized mask boundary over the raw solid-background image",
    )
    add_shared_inputs(overlay_parser)
    overlay_parser.add_argument("--solid-image", "--gray-image", dest="solid_image", type=existing_file, required=True)
    overlay_parser.add_argument("--mask-image", type=existing_file, required=True)
    overlay_parser.add_argument("--overlay-out", type=output_path, required=True)
    overlay_parser.add_argument("--mask-threshold", type=int, default=8)
    overlay_parser.add_argument("--edge-width", type=int, choices=range(1, 9), default=2)
    overlay_parser.add_argument("--outline-color", type=parse_color, default=(255, 0, 0))
    add_force(overlay_parser)
    overlay_parser.set_defaults(handler=alignment_overlay)

    validate_parser = subparsers.add_parser("validate", help="validate dimensions, mode, and exact pixels")
    add_shared_inputs(validate_parser)
    validate_parser.add_argument(
        "--solid-image",
        "--gray-image",
        dest="solid_image",
        type=existing_file,
        required=True,
    )
    validate_parser.add_argument("--mask-image", type=existing_file, required=True)
    add_background(validate_parser)
    validate_parser.add_argument("--require-black", action="store_true")
    validate_parser.add_argument("--require-white", action="store_true")
    validate_parser.set_defaults(handler=validate)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()

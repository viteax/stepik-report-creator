"""Рисует SVG-значок покрытия по coverage.xml – без сторонних сервисов.

Использование: python scripts/coverage_badge.py coverage.xml coverage.svg
"""

import sys
import xml.etree.ElementTree as ET

TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="coverage: {value}">
  <title>coverage: {value}</title>
  <linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
  <clipPath id="r"><rect width="{width}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{left}" height="20" fill="#555"/>
    <rect x="{left}" width="{right}" height="20" fill="{color}"/>
    <rect width="{width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{left_mid}" y="14">coverage</text>
    <text x="{right_mid}" y="14">{value}</text>
  </g>
</svg>
"""


def color(percent: float) -> str:
    if percent >= 90:
        return "#4c1"
    if percent >= 75:
        return "#a3c51c"
    if percent >= 60:
        return "#dfb317"
    return "#e05d44"


def make_badge(percent: float) -> str:
    value = f"{percent:.0f}%"
    left, right = 62, 7 * len(value) + 14
    return TEMPLATE.format(
        width=left + right,
        left=left,
        right=right,
        left_mid=left // 2,
        right_mid=left + right // 2,
        value=value,
        color=color(percent),
    )


def read_percent(xml_path: str) -> float:
    return float(ET.parse(xml_path).getroot().attrib["line-rate"]) * 100


if __name__ == "__main__":
    xml_path, svg_path = sys.argv[1:3]
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(make_badge(read_percent(xml_path)))

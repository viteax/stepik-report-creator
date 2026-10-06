from scripts.coverage_badge import color, make_badge, read_percent


def test_color_thresholds():
    assert color(95) == "#4c1"
    assert color(80) == "#a3c51c"
    assert color(65) == "#dfb317"
    assert color(10) == "#e05d44"


def test_badge_contains_percent():
    svg = make_badge(84.39)

    assert "84%" in svg
    assert svg.startswith("<svg")


def test_read_percent(tmp_path):
    xml = tmp_path / "coverage.xml"
    xml.write_text('<coverage line-rate="0.5"></coverage>')

    assert read_percent(str(xml)) == 50

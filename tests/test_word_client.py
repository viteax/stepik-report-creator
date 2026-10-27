from stepik_report.cli import TEMPLATE_PATH
from stepik_report.models import CodeSolution
from stepik_report.report import Report

SOLUTION = CodeSolution(
    title="Скобки",
    description="Проверьте правильность скобочной последовательности.",
    code="def solve(s: str) -> bool:\n    stack = []\n    return not stack\n",
)


def test_headings(tmp_path):
    doc = Report(template=TEMPLATE_PATH)
    doc.add_lesson("Купи слона")
    doc.add_page_break()
    doc.add_lesson("Делай деньги")
    path = doc.save(str(tmp_path / "temp"))

    assert path.endswith("temp.docx")
    headings = [p.text for p in doc.doc.paragraphs if p.style.name == "Heading 2"]
    assert headings[-2:] == [
        "2.1. Решения задач на тему «Купи слона»",
        "2.2. Решения задач на тему «Делай деньги»",
    ]


def test_code_as_text():
    doc = Report(template=TEMPLATE_PATH)
    doc.add_solution(SOLUTION)
    code_paragraphs = [p for p in doc.doc.paragraphs if p.style.name == "Code"]
    assert len(code_paragraphs) == 1
    assert "stack = []" in code_paragraphs[0].text


def test_custom_numbering_on_empty_document():
    """Другой формат отчета – только шаблоны строк, без шаблона docx."""
    doc = Report(
        part_no=1,
        lesson_heading="{part}.{n} Решения задач на тему «{title}»",
        listing_caption="Листинг {part}.{n} – {title}",
    )
    doc.add_lesson("Циклы")
    doc.add_solution(SOLUTION)
    doc.add_solution(SOLUTION)

    texts = [p.text for p in doc.doc.paragraphs]
    assert "1.1 Решения задач на тему «Циклы»" in texts
    assert [t for t in texts if t.startswith("Листинг")] == ["Листинг 1.1 – Скобки", "Листинг 1.2 – Скобки"]
    assert doc.lessons == 1 and doc.solutions == 2

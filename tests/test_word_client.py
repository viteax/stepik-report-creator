from clients.word import WordClient
from main import TEMPLATE_PATH


def test_headings():
    doc = WordClient(doc_path=TEMPLATE_PATH)
    doc.add_heading2("Купи слона", heading_no=1)
    doc.add_page_break()
    doc.add_heading2("Делай деньги", heading_no=2)
    doc.save("temp.docx")
    assert doc


def test_code_as_text():
    doc = WordClient(doc_path=TEMPLATE_PATH)
    doc.add_solution(
        no=1,
        title="Скобки",
        descr="Проверьте правильность скобочной последовательности.",
        code="def solve(s: str) -> bool:\n    stack = []\n    return not stack\n",
    )
    code_paragraphs = [p for p in doc.doc.paragraphs if p.style.name == "Code"]
    assert len(code_paragraphs) == 1
    assert "stack = []" in code_paragraphs[0].text

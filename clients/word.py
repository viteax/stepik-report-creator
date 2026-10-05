import os

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Cm

from docx_code import add_code, ensure_code_style

PAGE_WIDTH_CM = 15.25


class WordClient:
    def __init__(self, doc_path: str):
        self.doc = Document(docx=doc_path)
        ensure_code_style(self.doc)

    def add_heading1(self, title: str) -> None:
        self.doc.add_heading(title, level=1)
        self.doc.add_paragraph()

    def add_heading2(self, title: str, heading_no: int) -> None:
        self.doc.add_heading(
            f"2.{heading_no}. Решения задач на тему «{title}»",
            level=2,
        )
        self.doc.add_paragraph()

    def _add_problem(self, title: str, descr: str) -> None:
        self.doc.add_paragraph(f"«{title}».")
        self.doc.add_paragraph(f"{descr}")
        self.doc.add_paragraph()

    def add_code(self, code: str) -> None:
        """Код текстом с подсветкой синтаксиса (см. docx_code.py)."""
        add_code(self.doc, code)

    def add_solution(self, no: int, title: str, descr: str, code: str) -> None:
        """Решение в виде листинга: код текстом, его можно копировать."""
        self._add_problem(title, descr)

        label = self.doc.add_paragraph(f"Листинг 2.{no} – Решение задачи «{title}»")
        label.paragraph_format.keep_with_next = True
        self.add_code(code)

        self.doc.add_paragraph()

    def add_solution_picture(
        self, no: int, title: str, descr: str, img_path: str
    ) -> None:
        """Решение в виде картинки (старый режим, флаг --images)."""
        self._add_problem(title, descr)

        pic_p = self.doc.add_paragraph()
        pic_p.add_run().add_picture(img_path, width=Cm(PAGE_WIDTH_CM))
        pic_p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        label = self.doc.add_paragraph(f"Рисунок 2.{no} – Решение задачи «{title}»")
        label.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        self.doc.add_paragraph()

    def add_page_break(self):
        self.doc.add_page_break()

    def save(self, doc_name: str) -> str:
        os.makedirs("my_docs", exist_ok=True)
        if not doc_name.endswith(".docx"):
            doc_name += ".docx"
        path = f"my_docs/{doc_name}"
        self.doc.save(path)
        return path

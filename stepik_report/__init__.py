"""Отчет по разделу курса Stepik в docx: условия задач и последние правильные решения листингами.

Как библиотека:

    from stepik_report import Report, StepikClient, get_section_solutions

    stepik = StepikClient(token)              # или StepikClient.from_credentials(id, secret)
    section = stepik.get_section(stepik.get_section_id(58852, 7))
    report = Report()                         # или Report(template="мой-шаблон.docx")
    for lesson in get_section_solutions(stepik, section):
        report.add_lesson(lesson.title)
        for solution in lesson.solutions:
            report.add_solution(solution)
    report.save("7.docx")

Клиент синхронный (requests): из asyncio – через asyncio.to_thread.
"""

from .client import AuthError, NotFoundError, StepikClient, StepikError, get_token
from .docx_code import add_code, add_listing, ensure_code_style, lexer_name
from .models import CodeProblem, CodeSolution, Course, LessonSolutions, Section
from .report import Report
from .solutions import get_code_solutions, get_section_solutions, parse_block_text

__version__ = "2.0.0"

__all__ = [
    "AuthError",
    "CodeProblem",
    "CodeSolution",
    "Course",
    "LessonSolutions",
    "NotFoundError",
    "Report",
    "Section",
    "StepikClient",
    "StepikError",
    "add_code",
    "add_listing",
    "ensure_code_style",
    "get_code_solutions",
    "get_section_solutions",
    "get_token",
    "lexer_name",
    "parse_block_text",
]

import argparse
import logging
import os
import time

import coloredlogs

from clients.stepik import StepikClient
from clients.word import WordClient
from logic import IMGS_PATH, get_code_solutions

TEMPLATE_PATH = "assets/template.docx"
PYTHON_COURSE_ID = 58852

logger = logging.getLogger(__name__)

coloredlogs.install(level="DEBUG")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="stepik-report-creator",
        description="Собирает docx-отчет с решениями задач из раздела курса Stepik.",
    )
    parser.add_argument(
        "section",
        nargs="?",
        type=int,
        help="номер раздела (лабы); если не указан, спросим интерактивно",
    )
    parser.add_argument(
        "--course",
        type=int,
        default=PYTHON_COURSE_ID,
        help=f"id курса на Stepik (по умолчанию {PYTHON_COURSE_ID})",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    started_at = time.perf_counter()
    logger.info("Start")
    os.makedirs(IMGS_PATH, exist_ok=True)

    stepik = StepikClient()

    course_id = args.course
    section_no = args.section or int(input("Введите номер раздела (номер лабы): "))
    section = stepik.get_section(stepik.get_section_id(course_id, section_no))
    doc_name = f"{section_no}-{section.title.strip().replace(' ', '-')}"

    current_no = 1
    heading_no = 1

    custom_template_path = f"assets/{section_no}-template.docx"
    doc = WordClient(TEMPLATE_PATH)
    if os.path.isfile(custom_template_path):
        doc = WordClient(doc_path=custom_template_path)

    lessons = stepik.get_lessons(course_id, section_no)
    for lesson in lessons:
        code_solutions = get_code_solutions(lesson, stepik)
        if not code_solutions:
            logger.warning(f"No any solutions for «{lesson.title}»\n")
            continue

        doc.add_heading2(lesson.title, heading_no=heading_no)
        for solution in code_solutions:
            doc.add_solution(
                no=current_no,
                title=solution.title,
                descr=solution.description,
                img_path=solution.img_path,
            )
            current_no += 1
        doc.add_page_break()
        heading_no += 1

    doc.add_heading1("Заключение")
    doc.save(doc_name=doc_name)

    elapsed = time.perf_counter() - started_at
    print(f"Документ {doc_name}.docx готов.")
    print(f"Задач в отчете: {current_no - 1}, затрачено времени: {elapsed:.1f} с.")
    print("(он находится в папке my_docs)")


if __name__ == "__main__":
    main()

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Собирает отчет по разделу курса Stepik в Word (.docx)."
    )
    parser.add_argument(
        "section",
        nargs="?",
        type=int,
        help="номер раздела курса (номер лабы); если не указан – спросим",
    )
    parser.add_argument(
        "--course",
        type=int,
        default=PYTHON_COURSE_ID,
        help=f"id курса на Stepik (по умолчанию {PYTHON_COURSE_ID})",
    )
    parser.add_argument(
        "--images",
        action="store_true",
        help="вставлять код картинками (старый режим) вместо текста",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    coloredlogs.install(level="DEBUG")

    section_no = args.section or int(input("Введите номер раздела (номер лабы): "))
    started = time.perf_counter()
    logger.info("Start")

    if args.images:
        os.makedirs(IMGS_PATH, exist_ok=True)

    stepik = StepikClient()

    section = stepik.get_section(stepik.get_section_id(args.course, section_no))
    doc_name = f"{section_no}-{section.title.strip().replace(' ', '-')}"

    current_no = 1
    heading_no = 1

    custom_template_path = f"assets/{section_no}-template.docx"
    template = (
        custom_template_path if os.path.isfile(custom_template_path) else TEMPLATE_PATH
    )
    doc = WordClient(doc_path=template)

    lessons = stepik.get_lessons(args.course, section_no)
    for lesson in lessons:
        code_solutions = get_code_solutions(lesson, stepik, as_images=args.images)
        if not code_solutions:
            logger.warning(f"No any solutions for «{lesson.title}»\n")
            continue

        doc.add_heading2(lesson.title, heading_no=heading_no)
        for solution in code_solutions:
            if args.images:
                doc.add_solution_picture(
                    no=current_no,
                    title=solution.title,
                    descr=solution.description,
                    img_path=solution.img_path,
                )
            else:
                doc.add_solution(
                    no=current_no,
                    title=solution.title,
                    descr=solution.description,
                    code=solution.code,
                )
            current_no += 1
        doc.add_page_break()
        heading_no += 1

    doc.add_heading1("Заключение")
    path = doc.save(doc_name=doc_name)

    elapsed = time.perf_counter() - started
    print(f"Готово: {path}")
    print(f"Задач в отчете: {current_no - 1}, время: {elapsed:.1f} с")


if __name__ == "__main__":
    main()

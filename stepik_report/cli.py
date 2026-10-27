"""Командная строка: uv run main.py 7. Ключи своего приложения Stepik – в .env (см. README)."""

import argparse
import logging
import os
import time

import coloredlogs
from environs import Env

from .client import AuthError, StepikClient
from .report import Report
from .solutions import IMGS_PATH, get_code_solutions

TEMPLATE_PATH = "assets/template.docx"
DOCS_PATH = "my_docs"
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


def make_client() -> StepikClient:
    """Токен по ключам приложения из .env (CLIENT_ID, CLIENT_SECRET)."""
    env = Env()
    env.read_env()
    return StepikClient.from_credentials(env("CLIENT_ID"), env("CLIENT_SECRET"))


def main():
    args = parse_args()
    coloredlogs.install(level="DEBUG")

    section_no = args.section or int(input("Введите номер раздела (номер лабы): "))
    started = time.perf_counter()
    logger.info("Start")

    if args.images:
        os.makedirs(IMGS_PATH, exist_ok=True)

    try:
        stepik = make_client()
    except AuthError:
        print("Unable to authorize with provided credentials")
        raise SystemExit(1)

    section = stepik.get_section(stepik.get_section_id(args.course, section_no))
    doc_name = f"{section_no}-{section.title.strip().replace(' ', '-')}"

    custom_template_path = f"assets/{section_no}-template.docx"
    template = (
        custom_template_path if os.path.isfile(custom_template_path) else TEMPLATE_PATH
    )
    doc = Report(template=template)

    for lesson in stepik.get_section_lessons(section):
        code_solutions = get_code_solutions(lesson, stepik, as_images=args.images)
        if not code_solutions:
            logger.warning(f"No any solutions for «{lesson.title}»\n")
            continue

        doc.add_lesson(lesson.title)
        for solution in code_solutions:
            if args.images:
                doc.add_solution_picture(solution)
            else:
                doc.add_solution(solution)
        doc.add_page_break()

    doc.add_heading("Заключение", level=1)
    path = doc.save(f"{DOCS_PATH}/{doc_name}")

    elapsed = time.perf_counter() - started
    print(f"Готово: {path}")
    print(f"Задач в отчете: {doc.solutions}, время: {elapsed:.1f} с")


if __name__ == "__main__":
    main()

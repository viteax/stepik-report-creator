"""Разбор условия задачи и сбор решений по урокам. Картинки кода (режим --images) – через Pillow,
он нужен только для этого режима: pip install "stepik-report-creator[images]"."""

import logging
import re

from bs4 import BeautifulSoup

from .client import StepikClient
from .models import CodeProblem, CodeSolution, Lesson, LessonSolutions, Section

PADDING = 0
FONT_SIZE = 64
FONT_PATH = "assets/JetBrainsMono-Regular.ttf"
IMGS_PATH = "images"

_INPUT_FORMAT = re.compile(r"^\s*(формат входных данных|входные данные|формат ввода)", re.I)
_MATH = re.compile(r"\$+([^$]*)\$+")

logger = logging.getLogger(__name__)


def save_code_picture(img_path: str, code_str: str, font_path: str = FONT_PATH) -> None:
    """Saves picture"""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1, 1), (255, 255, 255))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, FONT_SIZE)

    code_str = code_str.strip()
    box_size = d.textbbox(
        (PADDING, PADDING),
        code_str,
        font=font,
    )
    line_length = box_size[2]
    line_height = box_size[3]

    img = img.resize((line_length + PADDING, line_height + PADDING))
    d = ImageDraw.Draw(img)
    d.text(
        (PADDING, PADDING),
        code_str,
        fill=(0, 0, 0),
        font=font,
    )
    img.save(img_path, "PNG")


def legalize_title(title: str) -> str:
    return "".join(
        symb
        for symb in title
        if symb not in ("\\", "/", ":", "*", "?", '"', "<", ">", "|")
    )


def _clean(text: str) -> str:
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    # формулы: $x_1$ → x1, а snake_case в обычном тексте не трогаем
    text = _MATH.sub(lambda m: m.group(1).replace("\\", "").replace("_", ""), text)
    return re.sub(r"\s+", " ", text).strip()


def parse_block_text(html_text: str | None) -> CodeProblem | None:
    """Заголовок из <h2> и абзацы условия до «Формат входных данных».
    Без <h2> заголовок пустой – подставит get_code_solutions. None – текста нет совсем."""
    if not (html_text or "").strip():
        return None
    soup = BeautifulSoup(html_text, "html.parser")

    problem_title = _clean(soup.h2.text) if soup.h2 else ""
    problem_descriptions = []
    for p in soup.find_all("p"):
        text = _clean(p.text)
        if _INPUT_FORMAT.match(text):
            break
        if text:
            problem_descriptions.append(text)

    return CodeProblem(
        title=legalize_title(problem_title),
        description=" ".join(problem_descriptions),
    )


def get_code_solutions(
    lesson: Lesson,
    stepik: StepikClient,
    as_images: bool = False,
    imgs_path: str = IMGS_PATH,
) -> list[CodeSolution]:
    """Задачи на код из урока, у которых есть правильное решение."""
    logger.info(f"Getting code solutions «{lesson.title}»\n")

    code_solutions = []
    for no, step in enumerate(stepik.get_steps(lesson.steps), 1):
        if step.block.name != "code":
            continue

        code_problem = parse_block_text(step.block.text)
        if not code_problem:
            continue

        reply = stepik.get_solution(step_id=step.id)
        if not reply:
            continue

        title = code_problem.title or f"Задача {no}"
        img_path = None
        if as_images:
            img_path = f"{imgs_path}/{title}.png"
            save_code_picture(img_path, reply.code)

        code_solutions.append(
            CodeSolution(
                title=title,
                description=code_problem.description,
                code=reply.code,
                language=reply.language or "python3",
                img_path=img_path,
            )
        )
    return code_solutions


def get_section_solutions(stepik: StepikClient, section: Section) -> list[LessonSolutions]:
    """Все уроки раздела с решениями; уроки без задач на код пропускаются."""
    out = []
    for lesson in stepik.get_section_lessons(section):
        solutions = get_code_solutions(lesson, stepik)
        if solutions:
            out.append(LessonSolutions(title=lesson.title.strip(), solutions=solutions))
    return out

# «Отчет Creator»: генерирую отчеты по лабам со Stepik в Word на Python

*Или как стать героем в глазах одногруппников.*

> **TL;DR.** Скрипт на Python забирает условия задач и мои решения через API Stepik, оформляет их по ГОСТу и собирает готовый .docx. Один отчет раньше занимал около двух часов, теперь – около двух секунд. Код – на [GitHub](https://github.com/viteax/stepik-report-creator).

![Страница отчета: условие задачи и код с подсветкой](https://raw.githubusercontent.com/viteax/stepik-report-creator/master/docs/screenshots/listing-page.png)

## Откуда взялась проблема

Смотришь на название дисциплины «Алгоритмы и структуры данных» и думаешь, что все будет супер. А потом выясняется: по каждому разделу курса на Stepik нужно сдать отчет. И ты такой: «Ну #₽@&*».

Задач в каждом разделе немало (за семестр набирается около 400), а в отчете для каждой должны быть условие, код решения и подпись к нему – и все это по ГОСТу.

«Окей, – думаю я, – вроде не так уж сложно». Но однажды я убил около двух часов на один отчет и понял, что так продолжаться не может. Так появился он – ~~Тайлер Дерден~~ мой проект по автоматизации отчетов, «Отчет Creator».

## Подход к задаче

Писать решил на Python: он лаконичный, а код на нем легко читать. Заодно хотел пощупать пакетный менеджер uv – проект и начинался как знакомство с ним. Для начала я ответил себе на три вопроса:

1. Где брать условия задач?
2. Как вставлять код решения, чтобы не съехала верстка?
3. Как собрать из этого документ Word?

С третьим все оказалось просто: для работы с .docx есть пакет `python-docx`.

На первый вопрос было два ответа: парсить страницы (не хотелось) или найти API (хотелось). Я вбил в поиск «stepik api» – и о чудо, API открытый. Документация – по сути сырые описания JSON, но для моей задачи этого хватило.

Сложнее всего было со вторым вопросом. Первая мысль – открыть страницу с решением в браузере через Selenium, сделать скриншот и обрезать. Звучало страшно, сложно и нудно, поэтому я стал искать путь проще (спойлер: нашел, а после комментариев к первой версии статьи – еще один, правильнее, см. раздел «Обновление»).

## Решение

### Модели данных

Сначала нужно было разобраться, где в ответах API лежат нужные данные. Чтобы не ковыряться в словарях, я описал ответы моделями Pydantic – заодно они валидируют JSON:

```python
from pydantic import BaseModel


class Lesson(BaseModel):
    id: int
    steps: list[int]
    title: str


class LessonResponse(BaseModel):
    meta: dict
    lessons: list[Lesson]


class Block(BaseModel):
    name: str
    text: str


class Step(BaseModel):
    id: int
    block: Block


class StepResponse(BaseModel):
    meta: dict
    steps: list[Step]

# ... и т. д.
```

### Клиент Stepik

Цепочка такая: курс → разделы (sections) → уроки (lessons) → шаги (steps). Задачи с кодом – это шаги с блоком типа `code`.

```python
class StepikClient:
    session = get_session()

    def get_section_id(self, course_id: int, section_no: int) -> int:
        resp = self.session.get(f"{API_URL}/courses/{course_id}")
        course_resp = CoursesResponse.model_validate(resp.json())
        sections_ids = course_resp.courses[0].sections
        if not (0 < section_no <= len(sections_ids)):
            raise IndexError("Раздела с таким номером не существует")
        return sections_ids[section_no - 1]

    def get_section(self, id: int) -> Section:
        resp = self.session.get(f"{API_URL}/sections/{id}")
        return SectionsResponse.model_validate(resp.json()).sections[0]

    def get_lesson(self, id: int) -> Lesson:
        resp = self.session.get(f"{API_URL}/lessons/{id}")
        return LessonResponse.model_validate(resp.json()).lessons[0]

    # и другие методы
```

Чтобы получить **свои** решения, нужен токен. Stepik выдает его по OAuth2: на странице [stepik.org/oauth2/applications](https://stepik.org/oauth2/applications/) создаем приложение с типом клиента `confidential` и grant type `client-credentials`, получаем `client_id` и `client_secret` и кладем их в `.env`. Дальше токен получается одним запросом:

```python
def get_session() -> requests.Session:
    config = load_config()  # CLIENT_ID и CLIENT_SECRET из .env
    auth = requests.auth.HTTPBasicAuth(config.client_id, config.client_secret)
    response = requests.post(
        "https://stepik.org/oauth2/token/",
        data={"grant_type": "client_credentials"},
        auth=auth,
    )
    token = response.json().get("access_token")
    if not token:
        raise SystemExit("Unable to authorize with provided credentials")

    session = requests.Session()
    session.headers = {"Authorization": f"Bearer {token}"}
    return session
```

С этой сессией эндпоинт `/api/submissions?step={id}` отдает все мои посылки по задаче. Берем последнюю со статусом `correct`:

```python
def get_solution_code(self, step_id: int) -> str | None:
    submission_json = self._get(f"{API_URL}/submissions?step={step_id}")
    submission_resp = SubmissionResponse.model_validate(submission_json)
    for submission in reversed(submission_resp.submissions):
        if submission.status == "correct":
            return submission.reply.code
    return None
```

### Разбор условия

Условие приходит в виде HTML, так что пришлось немного попарсить его через BeautifulSoup. Берем заголовок и текст до раздела «Формат входных данных»:

```python
def parse_block_text(html_text: str) -> CodeProblem | None:
    soup = BeautifulSoup(html_text, "html.parser")

    # В описаниях некоторых задач нет заголовка.
    # Это задачи повышенной сложности, их в отчет не включаем.
    if not soup.h2:
        return None

    problem_title = soup.h2.text.replace("\xa0", " ")
    problem_descriptions = []
    for p in soup.find_all("p"):
        text = p.text
        if text.startswith("Формат входных данных"):
            break
        problem_descriptions.append(text.replace("\xa0", " "))

    return CodeProblem(title=problem_title, description=problem_descriptions)
```

### Код решения картинкой (первая версия)

Получив строку с решением, я вбил в поиск «str to png python» и познакомился с Pillow. Рисуем текст моноширинным шрифтом JetBrains Mono на белом фоне – никакого браузера:

```python
PADDING = 20
FONT_SIZE = 24
FONT_PATH = "assets/JetBrainsMono-Regular.ttf"


def save_code_picture(img_path: str, code_str: str) -> None:
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    code_str = code_str.strip()

    # Сначала меряем, сколько места займет текст...
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    _, _, right, bottom = probe.textbbox((PADDING, PADDING), code_str, font=font)

    # ...потом рисуем на холсте нужного размера
    img = Image.new("RGB", (right + PADDING, bottom + PADDING), "white")
    ImageDraw.Draw(img).text((PADDING, PADDING), code_str, fill="black", font=font)
    img.save(img_path, "PNG")
```

На это написал тесты, чтобы убедиться, что картинки получаются корректными.

Дальше все собирается в список решений для каждого урока:

```python
def get_code_solutions(lesson: Lesson) -> list[CodeSolution]:
    stepik = StepikClient()
    code_solutions = []

    for step_id in lesson.steps:
        step = stepik.get_step(id=step_id)
        if step.block.name != "code":
            continue

        code_problem = parse_block_text(step.block.text)
        code_str = stepik.get_solution_code(step_id=step_id)
        if not code_problem or not code_str:
            continue

        img_path = f"{IMGS_PATH}/{legalize_title(code_problem.title)}.png"
        save_code_picture(img_path, code_str)
        code_solutions.append(
            CodeSolution(
                title=code_problem.title,
                description=code_problem.description,
                img_path=img_path,
            )
        )
    return code_solutions
```

### Сборка документа

Вся верстка живет в `WordClient`. Главный трюк для ГОСТа – не настраивать шрифты и отступы кодом, а взять за основу свой старый отчет: титульник, введение, стили заголовков и абзацев подтягиваются из шаблона. А если у лабы свое введение и цель, рядом кладется `assets/<номер раздела>-template.docx` – и для этого раздела берется он.

```python
class WordClient:
    def __init__(self, template_path: str):
        self.doc = Document(template_path)

    def add_heading2(self, title: str, heading_no: int) -> None:
        self.doc.add_heading(f"2.{heading_no}. Решения задач на тему «{title}»", level=2)

    def add_solution(self, no: int, title: str, descr: str, img_path: str) -> None:
        self.doc.add_paragraph(f"«{title}».")
        self.doc.add_paragraph(descr)

        pic = self.doc.add_paragraph()
        pic.add_run().add_picture(img_path)
        pic.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        label = self.doc.add_paragraph(f"Рисунок 2.{no} – Решение задачи «{title}»")
        label.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    def save(self, doc_name: str) -> None:
        os.makedirs("my_docs", exist_ok=True)
        self.doc.save(f"my_docs/{doc_name}.docx")
```

`main.py` просто связывает все вместе: спрашивает номер раздела, проходит по урокам и складывает решения в документ с правильной нумерацией рисунков. Полный код – в [репозитории](https://github.com/viteax/stepik-report-creator).

### Запуск

Нужны Python 3.13+ и [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/viteax/stepik-report-creator.git
cd stepik-report-creator
uv sync
cp .env.example .env    # вписываем CLIENT_ID и CLIENT_SECRET
uv run main.py 7        # 7 – номер раздела (лабы)
```

Готовый отчет появится в `my_docs/`. Другой курс – `--course <id>`, код картинками по-старому – `--images`.

## Обновление: код текстом, а не картинкой

Главная претензия в комментариях – «код рисунками – брр». Справедливо: картинку нельзя скопировать, ее не найти поиском по документу, и выглядит она хуже текста. Изначально я думал, что `python-docx` такое не умеет, но @milssky подсказал решение: как и в обычном Word, достаточно завести отдельный стиль для кода. А подсветку синтаксиса дает `pygments`, который советовал @Andrey_Solomatin.

Сначала создаем стиль – моноширинный шрифт, одинарный интервал, без красной строки:

```python
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Pt

CODE_STYLE = "Code"


def ensure_code_style(doc) -> None:
    if CODE_STYLE in [s.name for s in doc.styles]:
        return
    style = doc.styles.add_style(CODE_STYLE, WD_STYLE_TYPE.PARAGRAPH)
    style.base_style = doc.styles["Normal"]
    style.font.name = "Courier New"  # есть на любом компьютере, в отличие от JetBrains Mono
    style.font.size = Pt(10)
    pf = style.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.line_spacing = 1.0
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
```

Затем разбиваем код на токены и каждый пишем отдельным фрагментом (run) со своим цветом. Переносы строк `python-docx` сам превращает в разрывы строки, так что весь листинг – один абзац:

```python
from docx.shared import RGBColor
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.styles import get_style_by_name

PYGMENTS_STYLE = get_style_by_name("friendly")


def add_code(self, code: str) -> None:
    p = self.doc.add_paragraph(style=CODE_STYLE)
    for token_type, value in lex(code.strip("\n"), PythonLexer()):
        token_style = PYGMENTS_STYLE.style_for_token(token_type)
        run = p.add_run(value)
        if token_style["color"]:
            run.font.color.rgb = RGBColor.from_string(token_style["color"])
        run.bold = token_style["bold"]
        run.italic = token_style["italic"]
```

Подпись «Рисунок» при этом меняется на «Листинг» и ставится над кодом, а чтобы она не осталась одна внизу страницы, абзацу включается `keep_with_next`. Старый режим с картинками я оставил за флагом `--images` – вдруг кому-то так привычнее.

В комментариях предлагали и другие варианты:

| Вариант | Плюсы | Почему не подошел |
|---|---|---|
| LaTeX + minted (@sogonov) | Лучшая подсветка, идеальная верстка | Кафедра принимает только .docx |
| pandoc | Markdown → .docx одной командой | Сложнее точно попасть в шаблон ГОСТа |
| Sphinx (@Andrey_Solomatin) | Сразу PDF и HTML | Нужен .docx, и для одного отчета это тяжеловато |

Спасибо всем, кто подсказал!

## Что в итоге

- Отчет по разделу собирается за ~2 секунды вместо ~2 часов.
- Проектом пользуются около 60 человек – две группы по 30.
- Чего пока нет: подсветка только для Python, задачи без заголовка в условии пропускаются, формулы из условий упрощаются до текста.

Когда я делал отчеты вручную, копируя куски текста в Word, меня раздражала монотонность и я не понимал, чему эта работа учит. А потом, повторяя одно и то же полтора часа подряд, понял: для меня смысл оказался не в том, чтобы сделать отчет, а в том, чтобы этот процесс автоматизировать.

Проект научил меня разбираться в сырой документации API, искать информацию и подходить к задаче с разных сторон, чтобы найти самое простое решение. Раньше я не думал, что с помощью программирования можно решать такие бытовые задачи. Оказалось, можно – и с тех пор программирование для меня еще и про фантазию и творчество.

Если учитесь по курсам на Stepik – пробуйте, а идеи и пулреквесты жду в [репозитории](https://github.com/viteax/stepik-report-creator).

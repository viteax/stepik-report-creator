"""StepikClient без сети: ответы API подставляются вместо requests."""

import pytest
import requests

from stepik_report import AuthError, NotFoundError, StepikClient, StepikError, lexer_name
from stepik_report.solutions import get_section_solutions, parse_block_text


class FakeResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status_code = status
        self.ok = status < 400

    def json(self):
        return self.data


class FakeSession:
    """Отвечает как API Stepik на units/lessons/steps/submissions."""

    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        path = url.rsplit("/api/", 1)[1]
        self.calls.append(path)
        ids = [v for k, v in params] if isinstance(params, list) else []
        if path == "units":
            return FakeResponse({"units": [{"id": i, "lesson": i * 10} for i in reversed(ids)]})
        if path == "lessons":
            return FakeResponse(
                {"lessons": [{"id": i, "title": f" Урок {i} ", "steps": [i + 1, i + 2, i + 3]} for i in ids]}
            )
        if path == "steps":
            return FakeResponse(
                {
                    "steps": [
                        {
                            "id": i,
                            "block": {
                                "name": "text" if i % 10 == 3 else "code",
                                "text": f"<h2>Задача {i}</h2><p>Условие {i}</p>" if i % 10 == 1 else "<p>Без h2</p>",
                            },
                        }
                        for i in ids
                    ]
                }
            )
        if path == "submissions":
            step = params["step"]
            if step == 22:  # решал, но неправильно
                return FakeResponse({"meta": {}, "submissions": [{"id": 1, "status": "wrong", "reply": {"code": "x"}}]})
            return FakeResponse(
                {
                    "meta": {"has_next": False},
                    "submissions": [
                        {"id": 9, "status": "correct", "reply": {"code": f"print({step})", "language": "python3.10"}},
                        {"id": 5, "status": "correct", "reply": {"code": "old", "language": "python3"}},
                    ],
                }
            )
        if path == "courses/404":
            return FakeResponse({}, 404)
        if path == "stepics/1":
            return FakeResponse({"users": [{"first_name": "Иван", "last_name": "Петров"}]})
        if path == "boom":
            raise requests.ConnectionError("нет сети")
        return FakeResponse({}, 401)


@pytest.fixture
def stepik():
    client = StepikClient("T")
    client.session = FakeSession()
    return client


def test_section_solutions(stepik):
    from stepik_report.models import Section

    lessons = get_section_solutions(stepik, Section(id=1, units=[1, 2], title="Циклы"))

    assert [x.title for x in lessons] == ["Урок 10", "Урок 20"]  # порядок как в разделе, а не как ответил API
    first = lessons[0].solutions
    assert [(s.title, s.description, s.code, s.language) for s in first] == [
        ("Задача 11", "Условие 11", "print(11)", "python3.10"),  # из двух правильных – последнее
        ("Задача 2", "Без h2", "print(12)", "python3.10"),  # без <h2> – номер шага в уроке
    ]
    assert [s.title for s in lessons[1].solutions] == ["Задача 21"]  # у 22 нет правильного решения


def test_errors(stepik):
    assert stepik.get_me() == "Иван Петров"
    with pytest.raises(NotFoundError):
        stepik.get_course(404)
    with pytest.raises(AuthError):
        stepik._get("secret")
    with pytest.raises(StepikError):
        stepik._get("boom")


def test_parse_block_text_math_and_input_format():
    problem = parse_block_text(
        "<h2>Сумма&nbsp;чисел</h2><p>Даны $x_1$ и $x_2$.</p><p>Имя snake_case не трогаем.</p>"
        "<p>Входные данные</p><p>два числа</p>"
    )
    assert problem.title == "Сумма чисел"
    assert problem.description == "Даны x1 и x2. Имя snake_case не трогаем."
    assert parse_block_text("") is None


def test_lexer_name():
    assert lexer_name("python3.10") == "python"
    assert lexer_name("c++17") == "cpp"
    assert lexer_name("javascript") == "javascript"
    assert lexer_name("java11") == "java"
    assert lexer_name("c") == "c"
    assert lexer_name("brainfuck") == "text"

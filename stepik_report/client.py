"""Запросы к API Stepik. Клиент получает готовый токен: из client-credentials (свое приложение,
см. get_token и README) или из OAuth-входа студента – тогда /submissions отдает его решения."""

import logging

import requests
import requests.auth

from .models import (
    Course,
    CoursesResponse,
    Lesson,
    LessonResponse,
    Reply,
    Section,
    SectionsResponse,
    Step,
    StepResponse,
    SubmissionResponse,
    UnitsResponse,
)

API_URL = "https://stepik.org/api"
TOKEN_URL = "https://stepik.org/oauth2/token/"
BATCH = 20  # сколько объектов просить за раз (ids[]=…)
SUBMISSION_PAGES = 3

logger = logging.getLogger(__name__)


class StepikError(Exception):
    """Stepik ответил ошибкой или недоступен."""


class AuthError(StepikError):
    """Токен не приняли (401) или ключи приложения неверные."""


class NotFoundError(StepikError):
    pass


def get_token(client_id: str, client_secret: str) -> str:
    """Токен по client-credentials: действует от имени владельца приложения."""
    try:
        response = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=requests.auth.HTTPBasicAuth(client_id, client_secret),
            timeout=30,
        )
    except requests.RequestException as e:
        raise StepikError(f"token: {e!r}") from e
    token = response.json().get("access_token") if response.ok else None
    if not token:
        raise AuthError("Unable to authorize with provided credentials")
    return token


class StepikClient:
    def __init__(self, token: str, timeout: float = 30):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.timeout = timeout

    @classmethod
    def from_credentials(cls, client_id: str, client_secret: str) -> "StepikClient":
        return cls(get_token(client_id, client_secret))

    def close(self) -> None:
        self.session.close()

    def _get(self, path: str, params=None) -> dict:
        try:
            resp = self.session.get(f"{API_URL}/{path}", params=params, timeout=self.timeout)
        except requests.RequestException as e:
            raise StepikError(f"{path}: {e!r}") from e
        if resp.status_code == 401:
            raise AuthError(path)
        if resp.status_code == 404:
            raise NotFoundError(path)
        if not resp.ok:
            raise StepikError(f"{path}: {resp.status_code}")
        return resp.json()

    def _many(self, resource: str, ids: list[int]) -> list[dict]:
        """Объекты по списку id в том же порядке – пачками, а не запросом на каждый."""
        found: dict[int, dict] = {}
        for i in range(0, len(ids), BATCH):
            data = self._get(resource, [("ids[]", x) for x in ids[i : i + BATCH]])
            for obj in data.get(resource, []):
                found[obj["id"]] = obj
        return [found[x] for x in ids if x in found]

    def get_me(self) -> str:
        """Имя того, от чьего имени токен."""
        u = (self._get("stepics/1").get("users") or [{}])[0]
        name = u.get("full_name") or " ".join(
            filter(None, (u.get("first_name"), u.get("last_name")))
        )
        return name or "без имени"

    def get_course(self, course_id: int) -> Course:
        courses = CoursesResponse.model_validate(self._get(f"courses/{course_id}")).courses
        if not courses:
            raise NotFoundError(f"course {course_id}")
        return courses[0]

    def get_sections(self, ids: list[int]) -> list[Section]:
        data = {"sections": self._many("sections", ids)}
        return SectionsResponse.model_validate(data).sections

    def get_section_id(self, course_id: int, section_no: int) -> int:
        sections_ids = self.get_course(course_id).sections
        if not (0 < section_no <= len(sections_ids)):
            raise IndexError("Секции с таким номером не существует")
        return sections_ids[section_no - 1]

    def get_section(self, id: int) -> Section:
        return SectionsResponse.model_validate(self._get(f"sections/{id}")).sections[0]

    def get_lesson(self, id: int) -> Lesson:
        return LessonResponse.model_validate(self._get(f"lessons/{id}")).lessons[0]

    def get_section_lessons(self, section: Section) -> list[Lesson]:
        units = UnitsResponse.model_validate({"units": self._many("units", section.units)})
        lessons = self._many("lessons", [u.lesson for u in units.units])
        return LessonResponse.model_validate({"lessons": lessons}).lessons

    def get_lessons(self, course_id: int, section_no: int) -> list[Lesson]:
        section = self.get_section(self.get_section_id(course_id, section_no))
        return self.get_section_lessons(section)

    def get_step(self, id: int) -> Step:
        return StepResponse.model_validate(self._get(f"steps/{id}")).steps[0]

    def get_steps(self, ids: list[int]) -> list[Step]:
        return StepResponse.model_validate({"steps": self._many("steps", ids)}).steps

    def get_solution(self, step_id: int) -> Reply | None:
        """Последнее правильное решение шага (код и язык) или None."""
        best = None
        for page in range(1, SUBMISSION_PAGES + 1):
            params = {"step": step_id, "status": "correct", "order": "desc", "page": page}
            data = self._get("submissions", params)
            for sub in SubmissionResponse.model_validate(data).submissions:
                if sub.status == "correct" and sub.reply and sub.reply.code:
                    if best is None or sub.id > best.id:
                        best = sub
            if best or not (data.get("meta") or {}).get("has_next"):
                break
        return best.reply if best else None

    def get_solution_code(self, step_id: int) -> str | None:
        reply = self.get_solution(step_id)
        return reply.code if reply else None

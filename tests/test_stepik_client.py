import pytest

from stepik_report.cli import make_client
from stepik_report.models import Block, Step


@pytest.mark.network
def test_get_lessons():
    stepik = make_client()
    lessons = stepik.get_lessons(
        course_id=58852,
        section_no=1,
    )

    assert [lesson.id for lesson in lessons] == [290248, 363342, 1086413, 1602702]


@pytest.mark.network
def test_get_lessons_ids_invalid():
    stepik = make_client()
    with pytest.raises(IndexError):
        stepik.get_lessons(
            course_id=58852,
            section_no=17,
        )


@pytest.mark.network
def test_get_step():
    stepik = make_client()
    step = stepik.get_step(1010120)

    assert step == Step(
        id=1010120,
        block=Block(
            name="code",
            text='<h2 style="text-align:center;">Звёздный прямоугольник</h2>\n\n<p>Напишите программу, которая выводит прямоугольник,&nbsp;по периметру состоящий из звёздочек (<code>*</code>).</p>\n\n<p><strong>Примечание.</strong>&nbsp;Высота и ширина прямоугольника равны $4$ и $17$ звёздочкам соответственно.</p>',
        ),
    )

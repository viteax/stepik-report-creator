import os

import pytest
from PIL import Image

from clients.stepik import StepikClient
from logic import IMGS_PATH, parse_block_text, save_code_picture


def test_save_picture():
    os.makedirs(IMGS_PATH, exist_ok=True)

    pic_path = f"{IMGS_PATH}/test.png"

    save_code_picture(img_path=pic_path, code_str="lmao == gnome\nSkibidi")
    img = Image.open(pic_path)

    assert img


def test_parse_block_text():
    html_text = (
        "<h2>Заголовок</h2>\n<p>Доброе утро, мальчик</p>\n  <p>Как ты поживаешь?</p>"
    )
    ans = "Доброе утро, мальчик Как ты поживаешь?"

    code_problem = parse_block_text(html_text=html_text)

    assert code_problem.description == ans


@pytest.mark.network
def test_debug():
    stepik = StepikClient()
    step = stepik.get_step(1223214)

    code_problem = parse_block_text(step.block.text)
    print(code_problem)

    assert 1 == 1

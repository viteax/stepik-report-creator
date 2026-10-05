# Код в Word без картинок: подсветка синтаксиса через python-docx и Pygments

*Сто строк на Python – и листинги в .docx выглядят как в IDE, копируются, ищутся и нумеруются сами.*

В [прошлой статье](https://habr.com/ru/articles/906470/) я рассказывал про «Отчет Creator» – скрипт, который собирает отчеты по лабам со Stepik в Word. Код решений он вставлял **картинками**, и первый же комментарий был: «Код рисунками – брр».

Справедливо. Я тогда думал, что `python-docx` иначе не умеет. Оказалось – умеет, просто об этом почти нигде не написано. Разобрался, переделал и собрал все в небольшой модуль, который можно взять в любой свой генератор документов: отчеты, курсовые, документацию.

Вот что получается:

![Два листинга в Word: Python и C++ с подсветкой, рамкой и подписью «Листинг N»](listings.png)

## Почему не картинки

| | Картинка | Текст |
|---|---|---|
| Скопировать код | нельзя | можно |
| Найти через Ctrl+F | нельзя | можно |
| Четкость при печати и масштабе | зависит от разрешения | всегда четко |
| Поменять шрифт или размер в Word | только перегенерировать | через стиль, за секунду |
| Проверка на антиплагиат / нормоконтроль | часто придираются | вопросов нет |

Плюс скорость и размер. Я сравнил 30 одинаковых листингов по 14 строк:

| Способ | Время генерации | Размер .docx |
|---|---|---|
| Картинки (Pillow) | 4,1 с | 130 КБ |
| Текст (python-docx + Pygments) | 0,6 с | 39 КБ |

Пустой документ весит около 36 КБ, так что 30 текстовых листингов добавляют всего пару килобайт.

## Шаг 1. Стиль для кода

Первое, что подсказали в комментариях: в Word для кода заводят отдельный стиль. Тогда все листинги выглядят одинаково, а поменять шрифт можно в одном месте.

```python
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Pt

CODE_STYLE = "Code"


def ensure_code_style(doc, font="Courier New", size=10):
    if CODE_STYLE in [s.name for s in doc.styles]:
        return
    style = doc.styles.add_style(CODE_STYLE, WD_STYLE_TYPE.PARAGRAPH)
    style.base_style = doc.styles["Normal"]
    style.font.size = Pt(size)
    style.font.no_proof = True  # без красных волнистых подчеркиваний
    _set_all_fonts(style.element.get_or_add_rPr(), font)

    pf = style.paragraph_format
    pf.first_line_indent = Pt(0)  # в шаблонах по ГОСТу обычно есть красная строка
    pf.left_indent = Pt(0)
    pf.line_spacing = 1.0         # а еще полуторный интервал
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
```

Тут два неочевидных момента.

**`no_proof`.** Без него Word подчеркнет красным каждый `def` и `popleft`. Свойство «Не проверять правописание» снимает это для всего стиля.

**Шрифт.** Если просто написать `style.font.name = "Courier New"`, python-docx выставит шрифт только для латиницы (`w:ascii` и `w:hAnsi`). Для остальных диапазонов символов Word возьмет шрифт из базового стиля, и в одной строке могут оказаться два шрифта. Поэтому задаем все четыре атрибута:

```python
from docx.oxml.ns import qn


def _set_all_fonts(rpr, name):
    rfonts = rpr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), name)
```

Почему Courier New, а не JetBrains Mono, как было на картинках? Его не нужно устанавливать: он есть в Windows и macOS, и документ откроется одинаково у преподавателя.

## Шаг 2. Рамка и заливка

Чтобы листинг читался как блок, добавим стилю светлую заливку и тонкую рамку. Готового API для этого в python-docx нет, придется спуститься в XML:

```python
from docx.oxml import OxmlElement


def _add_box(ppr, fill="F6F8FA", border="D0D7DE"):
    pbdr = OxmlElement("w:pBdr")
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")      # в восьмых долях пункта: 4 = 0,5 pt
        el.set(qn("w:space"), "4")
        el.set(qn("w:color"), border)
        pbdr.append(el)
    ppr.insert_element_before(pbdr, "w:shd", *_PPR_TAIL)

    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    ppr.insert_element_before(shd, *_PPR_TAIL)
```

Главная ловушка – **порядок элементов**. Внутри `<w:pPr>` дочерние теги должны идти в порядке, заданном схемой OOXML. Если сделать просто `ppr.append(shd)`, заливка может оказаться после `<w:spacing>`. LibreOffice такое проглотит, а Word может отказаться открывать документ с ошибкой «нечитаемое содержимое». Поэтому вставляем через `insert_element_before` и передаем список тегов, которые обязаны идти после нашего:

```python
_PPR_TAIL = (
    "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
    "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
    "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
    "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
    "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
    "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange",
)
```

Список я взял из исходников python-docx (`CT_PPr`), там он лежит как раз для этого.

## Шаг 3. Подсветка: токены → runs

Абзац в Word состоит из фрагментов (runs), у каждого свое форматирование. Идея простая: Pygments режет код на токены и для каждого говорит цвет, жирность и курсив, а мы превращаем токены в runs.

```python
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name


def _runs(code, language, style_name):
    style = get_style_by_name(style_name)
    chunks = []
    lexer = get_lexer_by_name(language, ensurenl=False)
    for token_type, value in lex(code, lexer):
        s = style.style_for_token(token_type)
        fmt = (s["color"], s["bold"], s["italic"])
        if chunks and (chunks[-1][1] == fmt or value.isspace()):
            chunks[-1][0] += value  # склеиваем с предыдущим фрагментом
        else:
            chunks.append([value, fmt])
    return chunks
```

**Склейка фрагментов.** Наивно – один токен = один run. Но Pygments дробит код очень мелко: каждый пробел, скобка и запятая – отдельный токен. Если подряд идут токены с одинаковым стилем или пробелы (им цвет не важен), их можно слить в один run. На примере выше это дает 57 runs вместо 147 для Python и 39 вместо 103 для C++. Документ легче, и Word с ним работает быстрее.

**`ensurenl=False`.** По умолчанию Pygments дописывает в конец кода перевод строки, и в рамке снизу появляется пустая строка. Эта опция ее убирает.

Сама вставка:

```python
from docx.shared import RGBColor


def add_code(doc, code, language="python", style_name="friendly"):
    ensure_code_style(doc)
    p = doc.add_paragraph(style=CODE_STYLE)
    for text, (color, bold, italic) in _runs(code.strip("\n"), language, style_name):
        run = p.add_run(text)
        if color:
            run.font.color.rgb = RGBColor.from_string(color)
        run.bold = bold
        run.italic = italic
    return p
```

Весь листинг – **один абзац**. `add_run` сам превращает `\n` в разрыв строки `<w:br/>`, а `\t` – в табуляцию, и выставляет `xml:space="preserve"`, так что отступы не теряются. Если делать по абзацу на строку, рамка нарисуется вокруг каждой строки отдельно, а интервалы между абзацами разъедутся.

## Шаг 4. Подпись с автонумерацией

Номер в подписи можно написать текстом: «Листинг 3». Но если потом вставить листинг в середину, нумерация поедет. В Word для этого есть поле `SEQ` – то же самое делает «Ссылки → Вставить название». Вставим его руками:

```python
def _add_field(paragraph, instr, cached):
    def fld(kind):
        r = paragraph.add_run()
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), kind)
        r._r.append(el)

    fld("begin")
    r = paragraph.add_run()
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = f" {instr} "
    r._r.append(instr_el)
    fld("separate")
    paragraph.add_run(cached)  # то, что видно до обновления полей
    fld("end")


def add_listing(doc, code, title, number, language="python"):
    caption = doc.add_paragraph("Листинг ")
    _add_field(caption, "SEQ Листинг \\* ARABIC", str(number))
    caption.add_run(f" – {title}")
    caption.paragraph_format.keep_with_next = True

    add_code(doc, code, language)
```

Поле состоит из трех `fldChar`: начало, разделитель и конец. Между началом и разделителем – инструкция, между разделителем и концом – закешированный результат. Его мы сразу заполняем правильным номером, поэтому документ выглядит корректно и без обновления полей. А если потом вручную переставить листинги, достаточно нажать Ctrl+A и F9 – Word пересчитает номера.

`keep_with_next` не дает подписи остаться одной внизу страницы, когда сам код уехал на следующую.

## Использование

```python
from docx import Document
from docx_code import add_listing

doc = Document("template.docx")  # ваш шаблон по ГОСТу
add_listing(doc, open("bfs.py").read(), "Поиск в ширину", 1)
add_listing(doc, open("main.cpp").read(), "Чтение массива", 2, language="cpp")
doc.save("report.docx")
```

Что можно настроить:

- **Язык.** Подходит любой из [500+ лексеров Pygments](https://pygments.org/languages/): `"cpp"`, `"java"`, `"sql"`, `"bash"`, `"go"`. Если язык заранее неизвестен, есть `guess_lexer(code)`, но угадывает он не всегда.
- **Цветовая схема.** `"friendly"` хорошо смотрится на светлом фоне. Для черно-белой печати есть `"bw"`: только жирный и курсив, без цветов. Остальные схемы – на [pygments.org/styles](https://pygments.org/styles/).
- **Шрифт и размер.** Аргументы `ensure_code_style`. Если стиль `Code` уже есть в шаблоне, функция его не трогает, так что оформление можно целиком задать в самом Word.

## Подводные камни

- **Длинные строки.** Word переносит их по ширине страницы, и отступ продолжения теряется. Проще всего держать код в 80 символов или уменьшить размер шрифта до 9 pt.
- **Номера строк.** В этот модуль их не добавлял. Самый надежный вариант – таблица из двух колонок: номера и код. У встроенной нумерации строк Word (`suppressLineNumbers` и `lnNumType`) нумерация идет на весь раздел, а не на отдельный листинг.
- **LibreOffice vs Word.** LibreOffice прощает ошибки в порядке XML-элементов, Word – нет. Если генерируете документы для сдачи, проверяйте результат именно в Word.

## Где это работает

Модуль уже живет в [«Отчет Creator»](https://github.com/viteax/stepik-report-creator): отчет по разделу курса со Stepik теперь собирается с листингами текстом, а старый режим с картинками остался за флагом `--images`. Полный код модуля – в файле [`docx_code.py`](https://github.com/viteax/stepik-report-creator/blob/master/docx_code.py) в репозитории.

Спасибо @milssky за идею со стилем и @Andrey_Solomatin за Pygments – без комментариев к прошлой статье этого текста бы не было. Если знаете, как красиво сделать номера строк или перенос длинных строк с сохранением отступа, – пишите в комментариях.

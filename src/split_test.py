# SPDX-FileCopyrightText: 2025 Sascha Brawer <sascha@brawer.ch>
# SPDX-License-Identifier: MIT

import pytest

from split_v2 import Splitter, cleanup_text, merge_lines
from utils import Box, OCRLine
from validator import Validator


@pytest.fixture(scope="module")
def splitter() -> Splitter:
    return Splitter(Validator())


def test_cleanup_text():
    assert cleanup_text("ſtraß⸗") == "strass-"
    assert cleanup_text("Aarberger:") == "Aarberger-"
    assert cleanup_text("Aarberger=") == "Aarberger-"
    assert cleanup_text("Räfichgaffe 8 b") == "Käfichgasse 8b"
    assert cleanup_text("Mtzg. 8 b u. 9") == "Mtzg. 8b u. 9"


def test_merge_lines():
    assert merge_lines([]) == []
    lines = [
        OCRLine(29210592, 1, "Adam, Wittwe, Schneiderin,", Box(284, 1963, 628, 54)),
        OCRLine(29210592, 1, "Aarberg. 63", Box(381, 2011, 254, 52)),
        OCRLine(29210592, 1, "— Schweſt., Schneiderinnen,", Box(309, 2066, 604, 45)),
        OCRLine(29210592, 1, "Marktgaſſe 83.", Box(381, 2105, 301, 52)),
        OCRLine(29210592, 1, "Adamina Jean, Lehrer, Poſt⸗", Box(283, 2149, 631, 62)),
        OCRLine(29210592, 1, "gaſſe 44", Box(380, 2204, 170, 47)),
    ]
    assert merge_lines(lines) == [
        OCRLine(
            29210592,
            1,
            "Adam, Wittwe, Schneiderin, Aarberg. 63",
            Box(284, 1963, 628, 100),
        ),
        OCRLine(
            29210592,
            1,
            "— Schwest., Schneiderinnen, Marktgasse 83.",
            Box(309, 2066, 604, 91),
        ),
        OCRLine(
            29210592, 1, "Adamina Jean, Lehrer, Postgasse 44", Box(283, 2149, 631, 102)
        ),
    ]


def test_split_name(splitter):
    split = splitter.split_name
    assert split("Meier, M., Schneiderin") == ("Meier", "M., Schneiderin")
    assert split("Meier M., Schneiderin") == ("Meier", "M., Schneiderin")
    assert split("de Vigneule, B., Ag. 23") == ("de Vigneule", "B., Ag. 23")
    assert split("De Vigneule, B., Ag. 23") == ("de Vigneule", "B., Ag. 23")

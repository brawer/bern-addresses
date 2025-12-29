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
    assert split("De Vigneule, B., Ag. 23") == ("de Vigneule", "B., Ag. 23")
    assert split("v. Büren H., geb. v. Tavel") == ("von Büren", "H., geb. v. Tavel")
    assert split("V. Büren, Ag. 23") == ("von Büren", "Ag. 23")
    assert split("Buss & Cie., Parfümerie") == ("Buss", "& Cie., Parfümerie")


def test_split_company(splitter):
    assert splitter.split_company("Buß", "& Cie., Parfümerie, Brückfeld") == (
        "Buß & Cie.",
        "Parfümerie, Brückfeld",
    )
    assert splitter.split_company("Meier", "M., Schneiderin") == ("", "M., Schneiderin")


def test_split_given_name(splitter):
    split = splitter.split_given_name
    assert split("A. M., Zieglergasse 169") == ("A. M.", "Zieglergasse 169")
    assert split("Anna Maria, Zieglergasse 169") == ("Anna Maria", "Zieglergasse 169")
    assert split("Lehrerin, Zieglergasse 169") == ("", "Lehrerin, Zieglergasse 169")


def test_split_maiden_name(splitter):
    split = splitter.split_maiden_name
    assert split("Anna, Zieglergasse 169") == ("", "Anna, Zieglergasse 169")
    assert split("geborne Zbinden, Anna, Zieglergasse 169") == (
        "Zbinden",
        "Anna, Zieglergasse 169",
    )
    assert split("geborne v. Sinner, Frau, Kramgasse 172") == (
        "von Sinner",
        "Frau, Kramgasse 172",
    )


def test_split_title(splitter):
    split = splitter.split_title
    assert split("Frau, Lehrer., Jkg. 1") == ("Frau", "Lehrer., Jkg. 1")


def test_split_addresses(splitter):
    split = splitter.split_addresses
    assert split("") == ([], "")
    assert split("Metzg. 85 und 87, Bla, Bla") == (
        ["Metzg. 85", "Metzg. 87"],
        "Bla, Bla",
    )
    assert split("Lehrer, XY, Metzg. 85 und 87") == (
        ["Metzg. 85", "Metzg. 87"],
        "Lehrer, XY",
    )


def test_cleanup_address(splitter):
    c = splitter.cleanup_address
    assert c("") == []
    assert c("Lehrerin") == []
    assert c("Bahnhof") == ["Bahnhof"]
    assert c("Something 85") == []
    assert c("Metzg. 85") == ["Metzg. 85"]
    assert c("Kramg. 190.") == ["Kramg. 190"]
    assert c("Brunng. 7u. Marzielerain") == ["Brunng. 7", "Marzielerain"]
    assert c("Metzg. 85 und 87") == ["Metzg. 85", "Metzg. 87"]
    assert c("Aarbg. 21 u. Postg. 24") == ["Aarbg. 21", "Postg. 24"]
    assert c("Nng. 101 u. alte Gasfabrik") == ["Nng. 101", "alte Gasfabrik"]

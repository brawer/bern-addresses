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
    assert cleanup_text("ſtraß⸗") == "straß-"
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


def test_merge_lines_bug_404():
    # https://github.com/brawer/bern-addresses/issues/404
    lines = [
        OCRLine(29210900, 2, "Jäggi Eman. Fried., Amtsnot.", Box(977, 1311, 665, 51)),
        OCRLine(29210900, 2, "Pelikan 230 u. Kirchg. 268", Box(1078, 1363, 566, 49)),
        OCRLine(29210900, 2, "— =Gruner, Hotellaube 229 ±", Box(1003, 1609, 652, 55)),
        OCRLine(29210900, 2, "Chariatte, Schnd., Markt-", Box(1071, 1661, 570, 58)),
        OCRLine(29210900, 2, "gasse 44", Box(1078, 1712, 174, 52)),
        OCRLine(29210900, 2, "— =", Box(1008, 1681, 59, 17)),
        OCRLine(29210900, 2, "— R., 2. Pfr. a. d. H.-G.-", Box(1003, 1767, 639, 47)),
        OCRLine(29210900, 2, "Kirche, Aarbg. 54", Box(1079, 1810, 397, 58)),
    ]
    assert merge_lines(lines) == [
        OCRLine(
            page_id=29210900,
            column=2,
            text="Jäggi Eman. Fried., Amtsnot. Pelikan 230u. Kirchg. 268",
            box=Box(x=977, y=1311, width=667, height=101),
        ),
        OCRLine(
            page_id=29210900,
            column=2,
            text="— =Gruner, Hotellaube 229 ± Chariatte, Schnd., Marktgasse 44",
            box=Box(x=1003, y=1609, width=652, height=155),
        ),
        OCRLine(
            page_id=29210900,
            column=2,
            text="— -",
            box=Box(x=1008, y=1681, width=59, height=17),
        ),
        OCRLine(
            page_id=29210900,
            column=2,
            text="— R., 2. Pfr. a. d. H.-G.Kirche, Aarbg. 54",
            box=Box(x=1003, y=1767, width=639, height=101),
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


def test_split_occupations(splitter):
    split = splitter.split_occupations
    assert split("Mal., Bärenw.") == (["Mal.", "Bärenw."], "")
    assert split("Schnd., Spitg. 153") == (["Schnd."], "Spitg. 153")
    assert split("Schnd, Spitg 153") == (["Schnd."], "Spitg 153")
    assert split("Blah, Schnd., X") == (["Schnd."], "Blah, X")
    assert split("Mod. u. Lingère") == (["Mod.", "Lingère"], "")

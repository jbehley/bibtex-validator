#!/bin/python3
import re
import sys
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from typing_extensions import Annotated

import bibtexparser
import requests
import typer
from bibtexparser.model import Entry, String


# journal specific required fields:
JOURNALS_FIELDS = {
    "arxiv": ["author", "title", "journal", "volume", "year"],
    "ral": ["author", "title", "journal", "volume", "number", "pages", "year"],
    "pami": ["author", "title", "journal", "volume", "number", "pages", "year"],
    "ijrr": ["author", "title", "journal", "volume", "number", "pages", "year"],
    "tro": ["author", "title", "journal", "volume", "number", "pages", "year"],
    "ar": ["author", "title", "journal", "volume", "pages", "year"],
    "tmlr": ["author", "title", "journal", "year"],
}

MANDATORY_FIELDS = {
    "article": ["author", "title", "journal", "volume", "year"],  # some journals have no pages, issue, etc.
    "inproceedings": ["author", "title", "booktitle", "year"],
    "phdthesis": ["author", "title", "school", "year"],
    "book": ["author", "title", "publisher", "year"],
}

OPTIONAL_FIELDS = {
    "article": ["url", "codeurl", "videourl", "pages", "number", "abstract", "keywords"],
    "inproceedings": ["url", "codeurl", "videourl", "abstract", "keywords"],
    "phdthesis": ["url", "keywords", "abstract"],
    "book": ["volume", "edition", "url", "keywords", "abstract"],
}

WARNINGS = {
    "W001": "Missing 'url'. Please add 'url' to PDF or upload PDF to paper repository if possible.",
    "W002": "Missing 'pages' for article. Add 'pages = {XX--YY}' to entry if possible.",
    "W003": "Missing 'number' for article. Please add issue, i.e., 'number' to entry if possible.",
    "W004": "Title capitalization will be lost. Use {{...}} to keep capitalization.",
    "W005": "Use 'author' instead of 'authors'.",
}

ERRORS = {
    "E000": "Undefined BibTeX string: {string}.",
    "E001": "Irrelevant field '{field}'. Remove field from entry.",
    "E002": "Missing field '{field}' for entry. Required fields: {required_fields}.",
    "E003": "Wrong BibTeX key format '{key}'. Use '<author><year><venue>' for BibTeX keys, where <year> has 4 digits.",
    "E004": "Invalid 'url' to download pdf. Please provide direct url to PDF.",
    "E006": "Wrong format for 'volume' of arXiv article. Should be 'arXiv:XXXX.YYYYY'.",
    "E007": "Use '--' instead of '-' for page range.",
    "E008": "Irrelevant field 'pages' for arXiv preprint.",
    "E009": "Irrelevant field 'number' for arXiv preprint.",
    "E010": "Use existing @string variable for booktitle/journal. Should be '{string}'.",
}


class BibTeXString:
    """Explicit representation of a bibtex string."""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: str) -> bool:
        return self.value == other


@dataclass
class Message:
    """representation of a error or warning message."""

    code: str
    lineno: int
    text: str


@dataclass
class ValidationResult:
    """data class for a validation result."""

    error_code: int
    errors: List[Message]
    warnings: List[Message]


def check_fields(entry: Entry, **_) -> Tuple[List[Message], List[Message]]:
    """check entry for required and optional fields based on the type of the bibtex entry."""
    errors = []
    warnings = []

    entry_fields = [f.key for f in entry.fields]

    if str(entry.entry_type) in MANDATORY_FIELDS and str(entry.entry_type) in OPTIONAL_FIELDS:
        required_fields = MANDATORY_FIELDS[str(entry.entry_type)]
        optional_fields = OPTIONAL_FIELDS[str(entry.entry_type)]

        if str(entry.entry_type) == "article" and "journal" in entry_fields:
            if isinstance(entry.fields_dict["journal"].value, BibTeXString):
                journal_string = entry.fields_dict["journal"].value.key
                required_fields = JOURNALS_FIELDS.get(journal_string, required_fields)

        if not set(required_fields).issubset(entry_fields):
            missing_fields = set(required_fields) - set(entry_fields)

            if "author" in missing_fields and "authors" in entry_fields:
                missing_fields = missing_fields - set(["author"])

            for field in missing_fields:
                errors.append(
                    Message(
                        "E002",
                        entry.start_line + 1,
                        ERRORS["E002"].format(field=field, required_fields=required_fields),
                    )
                )

        if str(entry.entry_type) == "article" and "journal" in entry_fields:
            if entry.fields_dict["journal"].value == "arXiv preprint":
                if "pages" in entry_fields:
                    errors.append(Message("E008", entry.start_line + 1, ERRORS["E008"]))
                if "number" in entry_fields:
                    errors.append(Message("E009", entry.start_line + 1, ERRORS["E009"]))
                if "volume" in entry_fields:
                    if re.match(r"arXiv:\d{4}.\d{4,5}", entry.fields_dict["volume"].value) is None:
                        errors.append(Message("E006", entry.fields_dict["volume"].start_line + 1, ERRORS["E006"]))

            else:
                if "pages" not in entry_fields and "pages" not in required_fields:
                    warnings.append(Message("W002", entry.start_line + 1, WARNINGS["W002"]))
                if not "number" in entry_fields and "number" not in required_fields:
                    warnings.append(Message("W003", entry.start_line + 1, WARNINGS["W003"]))

        irrelevant_fields = set(entry_fields) - set(required_fields) - set(optional_fields) - set(["authors"])
        for field in irrelevant_fields:
            errors.append(Message("E001", entry.fields_dict[field].start_line + 1, ERRORS["E001"].format(field=field)))

    if "pages" in entry_fields and str(entry.entry_type) != "inproceedings":
        # FIXME: for arXiv articles: don't emit error.
        if re.match(r"[0-9]+-[0-9]+", entry.fields_dict["pages"].value):
            errors.append(Message("E007", entry.fields_dict["pages"].start_line + 1, ERRORS["E007"]))

    if "authors" in entry_fields:
        warnings.append(Message("W005", entry.fields_dict["authors"].start_line + 1, WARNINGS["W005"]))

    if "title" in entry_fields:
        raw_line = entry.raw.split("\n")[entry.fields_dict["title"].start_line - entry.start_line]
        if re.search(r"{{[\w\W]+}}", raw_line) is None:
            if entry.fields_dict["title"].value[1:].lower() != entry.fields_dict["title"].value[1:]:
                warnings.append(Message("W004", entry.fields_dict["title"].start_line + 1, WARNINGS["W004"]))

    return (errors, warnings)


def check_bibtex_key(entry: Entry, **_) -> Tuple[List[Message], List[Message]]:
    """check consistency of bibtex key based on the type of the bibtex entry."""
    errors = []
    warnings = []
    if re.match(r"[A-Za-z-]+[0-9]{4}[3A-Za-z-]+", entry.key) is None:
        errors.append(Message("E003", entry.start_line + 1, ERRORS["E003"].format(key=entry.key)))

    return (errors, warnings)


def check_url(entry: Entry, **kwargs) -> Tuple[List[Message], List[Message]]:
    """check if url points to a valid, downloadable PDF."""
    errors = []
    warnings = []

    entry_fields = [f.key for f in entry.fields]

    if "url" not in entry_fields:
        warnings.append(Message("W001", entry.start_line + 1, WARNINGS["W001"]))
    else:
        url = str(entry.fields_dict["url"].value)

        if url.endswith(".pdf") or url.startswith("proceedings:"):
            pass
        elif url == "":
            errors.append(Message("E004", entry.fields_dict["url"].start_line + 1, ERRORS["E004"]))
        else:
            if kwargs["check_pdf_download"]:
                # try downloading the document.
                try:
                    request = requests.head(entry.fields_dict["url"].value, timeout=3.0)
                    if "content-type" not in request.headers or request.headers["content-type"] != "application/pdf":
                        errors.append(Message("E004", entry.fields_dict["url"].start_line + 1, ERRORS["E004"]))
                except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
                    errors.append(Message("E004", entry.fields_dict["url"].start_line + 1, ERRORS["E004"]))

    return (errors, warnings)


def validate_bibtex(bibtex_string: str) -> ValidationResult:
    """validate given bibtex_string.

    Args:
        bibtex_string[str]: file content of a bibtex file.
    """
    bib_database = bibtexparser.parse_string(bibtex_string)
    validation_functions = [check_fields, check_bibtex_key, check_url]

    errors: List[Message] = []
    warnings: List[Message] = []

    text2string = {s.value: s.key for s in bib_database.strings}

    # make field values something that we can use in the validation for strings.
    for entry in bib_database.entries:
        for field in entry.fields:
            if field.key not in ("booktitle", "journal"):
                continue
            raw_line = entry.raw.split("\n")[field.start_line - entry.start_line]
            if re.search(r"[\"{}]+", raw_line) is None:
                match = re.search(r"=\s*([\w]+)", raw_line)

                if match.group(1) not in bib_database.strings_dict:
                    errors.append(Message("E000", field.start_line + 1, ERRORS["E000"].format(string=match.group(1))))
                else:
                    field.value = BibTeXString(match.group(1), bib_database.strings_dict[match.group(1)].value)
            elif match := re.search(r"\"([\w\W]+)\"|{([\w\W]+)}", raw_line):
                matched_text = match.group(1) or match.group(2)
                if matched_text in text2string:
                    errors.append(
                        Message(
                            "E010",
                            field.start_line + 1,
                            ERRORS["E010"].format(string=text2string[matched_text]),
                        )
                    )

    check_pdf_download = len(bib_database.entries) < 25

    for entry in bib_database.entries:
        for fn in validation_functions:
            e, w = fn(entry, check_pdf_download=check_pdf_download)
            errors.extend(e)
            warnings.extend(w)

    errors = sorted(errors, key=lambda e: e.lineno)

    return ValidationResult(1 if len(errors) > 0 else 0, errors, warnings)


def main(filename: str, warnings: Annotated[Optional[bool], typer.Option(help="Show Warnings.")] = True):
    """run the validator with the bibtex of the given filename"""
    with open(filename, encoding="utf8") as file:
        file_content = file.read()
        result = validate_bibtex(file_content)

        all_messages = result.errors
        if warnings:
            all_messages = sorted([*result.errors, *result.warnings], key=lambda msg: msg.lineno)

        for msg in all_messages:
            pos = 0
            if match := re.search(r"[A-Za-z0-9_@]", file_content.split("\n")[msg.lineno - 1]):
                pos = match.start() + 1
            # fixme: errors should go to a different stream.
            print(f"{filename}:{msg.lineno}:{pos}: {msg.code}: {msg.text}", file=sys.stdout)

        print(f"{len(result.errors)} errors, {len(result.warnings)} warnings.")

        raise typer.Exit(code=result.error_code)


def run():  # pragma: no cover
    """run the program via Typer."""
    typer.run(main)


if __name__ == "__main__":  # pragma: no cover
    typer.run(main)

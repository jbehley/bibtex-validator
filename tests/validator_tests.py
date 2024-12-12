import io
import os
import unittest
from contextlib import redirect_stdout

from typer import Exit

from src.bibtex_validator.validator import main, validate_bibtex, BibTeXString

# FIXME: better check that specific code is in the warnings/errors.


class TestValidator(unittest.TestCase):
    def test_bibtex_string(self):
        new_string = BibTeXString("ral", "IEEE Robotics \& Automation Letters (RA-L)")

        self.assertEqual(new_string.key, "ral")
        self.assertEqual(str(new_string), "IEEE Robotics \& Automation Letters (RA-L)")
        self.assertTrue(new_string == "IEEE Robotics \& Automation Letters (RA-L)")
        self.assertFalse(new_string != "IEEE Robotics \& Automation Letters (RA-L)")
        self.assertFalse(new_string == "wrong")

    def test_entrypoint(self):
        with redirect_stdout(io.StringIO()) as f:
            try:
                self.assertRaises(main("tests/inputs/passing/passing.bib"), Exit)
            except Exit:
                pass
        self.assertEqual("0 errors, 0 warnings.\n", f.getvalue())

        with redirect_stdout(io.StringIO()) as f:
            try:
                self.assertRaises(main("tests/inputs/errors/E003.bib"), Exit)
            except Exit:
                pass

        self.assertEqual("1 errors, 0 warnings.", f.getvalue().split("\n")[-2])

    def test_passing(self):
        """test cases that should be successful as bibtex does not contain any errors or warnings."""
        testcase_dir = "tests/inputs/passing"
        for filename in os.listdir(testcase_dir):
            with open(os.path.join(testcase_dir, filename), encoding="utf8") as file:
                with self.subTest(f"{filename}"):
                    result = validate_bibtex(file.read())

                    self.assertEqual(result.error_code, 0)
                    self.assertEqual(len(result.errors), 0)
                    self.assertEqual(len(result.warnings), 0)

    def test_warnings(self):
        """test cases that should lead to a warning (i.e., some ambiguous cases are producing a warning.)"""
        testcase_dir = "tests/inputs/warning"
        for filename in os.listdir(testcase_dir):
            expected_code = os.path.splitext(filename)[0].split("_")[0]
            with open(os.path.join(testcase_dir, filename), encoding="utf8") as file:
                with self.subTest(f"{filename}"):
                    result = validate_bibtex(file.read())

                    self.assertEqual(result.error_code, 0)
                    self.assertEqual(
                        len(result.warnings), 1, f"{expected_code}: should produce a single warning!\n Output: {result}"
                    )

                    self.assertEqual(result.warnings[0].code, expected_code)

    def test_errors(self):
        """test cases that should lead to an error (i.e., mandatory inconsistencies in bibtex entries)."""
        testcase_dir = "tests/inputs/errors"
        for filename in os.listdir(testcase_dir):
            expected_code = os.path.splitext(filename)[0].split("_")[0]
            with open(os.path.join(testcase_dir, filename), encoding="utf8") as file:
                with self.subTest(f"{filename}"):
                    result = validate_bibtex(file.read())

                    self.assertEqual(result.error_code, 1)
                    self.assertEqual(
                        len(result.errors), 1, f"{expected_code}: should produce an error!\n Output: {result}"
                    )

                    self.assertEqual(result.errors[0].code, expected_code)

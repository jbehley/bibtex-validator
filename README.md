# :mag: BibTeX Validator

Checking an BibTeX file for consistency and our style requirements. The checks a valid BibTeX file and produces warnings and errors. 
Warnings are optional changes or suggestions, while errors need to be fixed.

For small bibliographies, i.e., less than 25 entries, the script will also check if urls lead to an actual PDF.

## Setup

```bash
pip install -U git+ssh://git@github.com/jbehley/bibtex-validator.git
```

When you cloned the repository, then you can build the package via:

```bash
pip install -U .
```

## Usage

```bash
bibtex-validator example/references.bib
```

This will produce the following output:
```bash
example/references.bib:5:1: E002: Missing field 'year' for entry. Required fields: ['author', 'title', 'booktitle', 'year'].
example/references.bib:14:3: W004: Title capitalization will be lost. Use {{...}} to keep capitalization.
example/references.bib:18:3: E007: Use '--' instead of '-' for page range.
example/references.bib:24:1: E002: Missing field 'number' for entry. Required fields: ['author', 'title', 'journal', 'volume', 'number', 'pages', 'year'].
example/references.bib:24:1: E002: Missing field 'pages' for entry. Required fields: ['author', 'title', 'journal', 'volume', 'number', 'pages', 'year'].
example/references.bib:29:3: E004: Invalid 'url' to download pdf. Please provide direct url to PDF.
example/references.bib:37:3: E010: Use existing @string variable for booktitle/journal. Should be 'arxiv'.
example/references.bib:38:3: E006: Wrong format for 'volume' of arXiv article. Should be 'arXiv:XXXX.YYYYY'.
7 errors, 1 warnings.
```

## Acknowledgment

    Good artists copy. Great artists steal. 
    -- Pablo Picasso

I took great inspiration from (internal) bibtex_parser by Meher Malladi and stole stuff from [KISS-ICP](https://github.com/PRBonn/kiss-icp) by Nacho.

And I hate black as it doesn't allow to have 2 space indentation!
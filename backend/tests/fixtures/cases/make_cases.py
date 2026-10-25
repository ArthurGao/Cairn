"""Generate the synthetic sample case. Every person, company and number here is fictional.

Run from backend/: `uv run python -m tests.fixtures.cases.make_cases`. Output is byte-stable
(reportlab `invariant=1`, a seeded noise image), so re-running produces no git diff.

`DOCS` is the single source of the page text: tests check that every quote in `facts.json`
occurs on its page here, and M2 checks that PDF text extraction returns the same text.
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

OUT = Path(__file__).parent / "aewv-sample"
LETTERS_OUT = Path(__file__).parent / "letters"

# filename -> pages -> lines
DOCS: dict[str, list[list[str]]] = {
    "questionnaire.pdf": [
        [
            "Client intake questionnaire (sample)",
            "Full name: Alex Sample",
            "Date of birth: 12/04/1990",
            "Current address: 12 Example Street, Hamilton 3200",
            "Living at this address since: 01/2021",
        ],
        [
            "Employment history",
            "Employer: Example Freight Ltd",
            "Role: Warehouse Supervisor",
            "Start date: 03/2022",
            "Documents to follow: police certificate",
        ],
    ],
    "employer-letter.pdf": [
        [
            "Example Freight Ltd",
            "To whom it may concern",
            "Alex Sample has been employed by Example Freight Ltd as Warehouse Supervisor",
            "since 1 June 2022. This is a permanent full-time position.",
            "Signed: P. Example, Operations Manager",
        ]
    ],
    "application-form.pdf": [
        [
            "Application for an Accredited Employer Work Visa (sample form)",
            "Family name: Sample   Given names: Alex",
            "Date of birth: 12 April 1990",
            "Residential address: 12 Example Street, Hamilton 3200, from January 2021",
        ],
        [
            "Current employer: Example Freight Ltd",
            "Job title: Warehouse Supervisor",
            "Employment start: June 2022",
            "Applicant signature: [signed]   Date: 20 October 2026",
        ],
    ],
    "tenancy.pdf": [
        [
            "Residential tenancy agreement",
            "Tenant: Alex Sample",
            "Premises: 12 Example Street, Hamilton 3200",
            "Tenancy start date: 1 May 2021",
            "Landlord: Sample Property Management Ltd",
        ]
    ],
    "cover-letter.pdf": [
        [
            "Cover letter: AEWV application for Alex Sample",
            "Enclosed: Appendix 1 passport; Appendix 2 application form; Appendix 3 job offer;",
            "Appendix 4 employer letter; Appendix 5 tenancy agreement; Appendix 6 questionnaire;",
            "Appendix 7 police certificate.",
        ]
    ],
}

# Synthetic INZ letters (design §8.8), kept out of `aewv-sample/` because they are not evidence.
# The PPI raises three concerns about the sample case: the start-date mismatch, the police
# certificate that never arrived, and the address date the tenancy does not support.
LETTERS: dict[str, list[list[str]]] = {
    "ppi-aewv.pdf": [
        [
            "Immigration New Zealand (sample letter - not a real document)",
            "Our reference: SAMPLE-0001",
            "24 October 2026",
            "Dear Alex Sample",
            "Re: Accredited Employer Work Visa application",
            "We are writing about your application for an Accredited Employer Work Visa.",
            "Before we decide it, you have the chance to comment on the following concerns.",
            "1. Your questionnaire gives your start date with Example Freight Ltd as 03/2022.",
            "Your employer's letter states you have been employed since 1 June 2022.",
            "2. Your application lists a police certificate, but none has been received.",
            "3. Your application form states you have lived at 12 Example Street since",
            "January 2021.",
        ],
        [
            "Please provide evidence of when you began living at this address.",
            "If you do not respond by 7 November 2026, we will decide your application on the",
            "information we hold.",
            "Yours sincerely",
            "A. Officer, Immigration Officer",
        ],
    ]
}

# What the fake transcriber returns for the passport image in M2.
PASSPORT_LINES = [
    "SAMPLE PASSPORT - NOT A REAL DOCUMENT",
    "Surname: SAMPLE",
    "Given names: ALEX",
    "Date of birth: 12 APR 1990",
    "Passport no: XS0000001",
    "Date of expiry: 01 MAR 2031",
]


def write_pdf(path: Path, pages: list[list[str]]) -> None:
    canvas = Canvas(str(path), pagesize=A4, invariant=1)
    canvas.setTitle(path.stem)
    for lines in pages:
        y = 800.0
        for line in lines:
            canvas.drawString(56, y, line)
            y -= 22
        canvas.showPage()
    canvas.save()


def write_passport(path: Path) -> None:
    image = Image.new("RGB", (900, 360), "white")
    draw = ImageDraw.Draw(image)
    for n, line in enumerate(PASSPORT_LINES):
        draw.text((40, 30 + n * 50), line, fill="black", font_size=28)
    image.save(path, format="PNG", optimize=False)


def write_unreadable(path: Path) -> None:
    rng = random.Random(7)
    image = Image.new("L", (320, 240))
    image.putdata([rng.randrange(256) for _ in range(320 * 240)])
    image.save(path, format="JPEG", quality=40)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for filename, pages in DOCS.items():
        write_pdf(OUT / filename, pages)
    write_passport(OUT / "passport-scan.png")
    write_unreadable(OUT / "unreadable-photo.jpg")
    LETTERS_OUT.mkdir(exist_ok=True)
    for filename, pages in LETTERS.items():
        write_pdf(LETTERS_OUT / filename, pages)


if __name__ == "__main__":
    main()

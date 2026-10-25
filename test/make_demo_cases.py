"""Generate synthetic demo cases for manual testing in the web UI. Every person, company and
number here is fictional; no real person's documents are ever used (AGENTS.md rule 10).

Run from backend/ (it has reportlab and Pillow): `uv run python ../test/make_demo_cases.py`.
Writes one folder per case next to this script; upload a folder's files into a new case.

- `demo-conflicts/`: planted problems a check should report (listed in `PLANTED`).
- `demo-clean/`: the same kind of case with every fact agreeing and every item present.
"""

from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

HERE = Path(__file__).parent

# case -> filename -> pages -> lines
CASES: dict[str, dict[str, list[list[str]]]] = {
    "demo-conflicts": {
        "application-form.pdf": [
            [
                "Application for an Accredited Employer Work Visa (sample form)",
                "Family name: Example   Given names: Jordan",
                "Date of birth: 3 February 1988",
                "Passport number: XD0000042",
                "Residential address: 7 Placeholder Road, Tauranga 3110, from March 2020",
            ],
            [
                "Current employer: Demo Orchards Ltd",
                "Job title: Orchard Manager",
                "Employment start: 1 September 2023",
                "Applicant signature: [signed]   Date: 18 October 2026",
            ],
        ],
        "job-offer.pdf": [
            [
                "Demo Orchards Ltd - Offer of employment",
                "Employee: Jordon Example",
                "Position: Orchard Manager, permanent full-time, NZD 31.50 per hour",
                "Start date: 1 November 2023",
                "Employer signature: [signed] Q. Demo, Director",
                "Employee signature: ____________   Date: ________",
            ]
        ],
        "bank-statement.pdf": [
            [
                "Sample Bank - account statement (sample)",
                "Account holder: Jordan Example",
                "Address: 21 Fictional Avenue, Rotorua 3010",
                "Statement period: 1 June 2021 to 30 June 2021",
            ]
        ],
        "cover-letter.pdf": [
            [
                "Cover letter: AEWV application for Jordan Example",
                "Enclosed: Appendix 1 passport; Appendix 2 application form; Appendix 3 job offer;",
                "Appendix 4 bank statement; Appendix 5 police certificate (Australia).",
                "The client will send a medical certificate to follow.",
            ]
        ],
    },
    "demo-clean": {
        "application-form.pdf": [
            [
                "Application for an Accredited Employer Work Visa (sample form)",
                "Family name: Placeholder   Given names: Riley",
                "Date of birth: 9 July 1992",
                "Passport number: XC0000777",
                "Residential address: 3 Sample Lane, Nelson 7010, from August 2019",
            ],
            [
                "Current employer: Mock Engineering Ltd",
                "Job title: Maintenance Engineer",
                "Employment start: 14 February 2024",
                "Applicant signature: [signed]   Date: 12 October 2026",
            ],
        ],
        "job-offer.pdf": [
            [
                "Mock Engineering Ltd - Offer of employment",
                "Employee: Riley Placeholder",
                "Position: Maintenance Engineer, permanent full-time, NZD 38.00 per hour",
                "Start date: 14 February 2024",
                "Employer signature: [signed] S. Mock, Director",
                "Employee signature: [signed]   Date: 2 February 2024",
            ]
        ],
        "police-certificate.pdf": [
            [
                "Police certificate (sample, not a real document)",
                "Name: Riley Placeholder   Date of birth: 9 July 1992",
                "Country: New Zealand   Issued: 1 September 2026",
                "Result: no convictions recorded",
            ]
        ],
        "cover-letter.pdf": [
            [
                "Cover letter: AEWV application for Riley Placeholder",
                "Enclosed: Appendix 1 passport; Appendix 2 application form; Appendix 3 job offer;",
                "Appendix 4 police certificate (New Zealand).",
            ]
        ],
    },
}

PASSPORTS: dict[str, list[str]] = {
    "demo-conflicts": [
        "SAMPLE PASSPORT - NOT A REAL DOCUMENT",
        "Surname: EXAMPLE",
        "Given names: JORDAN",
        "Date of birth: 03 FEB 1989",
        "Passport no: XD0000042",
        "Date of expiry: 15 AUG 2030",
    ],
    "demo-clean": [
        "SAMPLE PASSPORT - NOT A REAL DOCUMENT",
        "Surname: PLACEHOLDER",
        "Given names: RILEY",
        "Date of birth: 09 JUL 1992",
        "Passport no: XC0000777",
        "Date of expiry: 30 NOV 2032",
    ],
}

# What a check of demo-conflicts should find (for reading the results, not asserted by code).
PLANTED = """Planted in demo-conflicts (all fictional):
- identity.date_of_birth: form 3 Feb 1988 vs passport 03 FEB 1989
- identity.name: job offer spells "Jordon", form and passport "Jordan"
- employment.period: form start 1 Sep 2023 vs job offer 1 Nov 2023
- address.period: form at 7 Placeholder Road from Mar 2020, bank statement June 2021 at
  21 Fictional Avenue
- pre-submission: job offer not signed by the employee; cover letter cites Appendix 5 police
  certificate, which is not in the case; medical certificate "to follow" is missing
demo-clean should have no conflicts; police certificate and signatures are present.
"""


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


def write_passport(path: Path, lines: list[str]) -> None:
    image = Image.new("RGB", (900, 360), "white")
    draw = ImageDraw.Draw(image)
    for n, line in enumerate(lines):
        draw.text((40, 30 + n * 50), line, fill="black", font_size=28)
    image.save(path, format="PNG", optimize=False)


def main() -> None:
    for case, docs in CASES.items():
        out = HERE / case
        out.mkdir(exist_ok=True)
        for filename, pages in docs.items():
            write_pdf(out / filename, pages)
        write_passport(out / "passport-scan.png", PASSPORTS[case])
    (HERE / "PLANTED.txt").write_text(PLANTED, encoding="utf-8")


if __name__ == "__main__":
    main()

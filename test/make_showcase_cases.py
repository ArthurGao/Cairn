"""Generate the showcase cases: four synthetic AEWV files, each built to show one thing Cairn
does, for walking a reviewer through the demo. Every person, company, address and number here is
fictional; no real person's documents are ever used (AGENTS.md rule 10).

Run from backend/ (it has reportlab and Pillow): `uv run python ../test/make_showcase_cases.py`.
Writes `showcase/<case>/` next to this script (git-ignored) and `showcase/SHOWCASE.md`, which
lists each case's label, what it shows and what a check should find.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

OUT = Path(__file__).parent / "showcase"
SAMPLE = "SAMPLE - fictional document for a software demo"

Pages = list[list[str]]

# case folder -> (label shown in the app, filename -> pages of lines, image name -> lines)
CASES: dict[str, tuple[str, dict[str, Pages], dict[str, list[str]]]] = {
    "1-ready-to-lodge": (
        "1 · Ready to lodge — Priya Sample, chef (AEWV): everything agrees, nothing missing",
        {
            "application-form.pdf": [
                [
                    "Accredited Employer Work Visa - application form (" + SAMPLE + ")",
                    "Family name: Sample   Given names: Priya",
                    "Date of birth: 21 April 1994",
                    "Passport number: XP4471208",
                    "Residential address: 12 Example Street, Christchurch 8011, since June 2022",
                ],
                [
                    "Employer: Harbourview Bistro Ltd",
                    "Job title: Chef",
                    "Employment start: March 2024",
                    "Applicant signature: [signed]   Date: 14 October 2026",
                ],
            ],
            "job-offer.pdf": [
                [
                    "Harbourview Bistro Ltd - offer of employment (" + SAMPLE + ")",
                    "Employee: Priya Sample",
                    "Position: Chef, permanent full-time, 40 hours a week, NZD 33.00 per hour",
                    "Start date: 18 March 2024",
                    "Employer signature: [signed] H. Bistro, Owner   Date: 1 March 2024",
                    "Employee signature: [signed]   Date: 4 March 2024",
                ]
            ],
            "police-certificate-india.pdf": [
                [
                    "Police clearance certificate - India (" + SAMPLE + ")",
                    "Name: Priya Sample   Date of birth: 21 April 1994",
                    "Issued: 2 September 2026",
                    "Result: no criminal record",
                ]
            ],
            "cover-letter.pdf": [
                [
                    "Cover letter - AEWV application for Priya Sample (" + SAMPLE + ")",
                    "Enclosed: Appendix 1 passport; Appendix 2 application form;",
                    "Appendix 3 offer of employment; Appendix 4 police certificate (India).",
                    "All documents are in English.",
                ]
            ],
        },
        {
            "passport-scan.png": [
                "PASSPORT (" + SAMPLE + ")",
                "Surname: SAMPLE",
                "Given names: PRIYA",
                "Date of birth: 21 APR 1994",
                "Passport no: XP4471208",
                "Date of expiry: 09 JAN 2033",
            ]
        },
    ),
    "2-conflicting-facts": (
        "2 · Facts that do not agree — Daniel Placeholder, builder (AEWV): 4 conflicts to resolve",
        {
            "application-form.pdf": [
                [
                    "Accredited Employer Work Visa - application form (" + SAMPLE + ")",
                    "Family name: Placeholder   Given names: Daniel",
                    "Date of birth: 14 May 1990",
                    "Passport number: XD5590321",
                    "Residential address: 8 Totara Road, Hamilton 3204, since January 2021",
                ],
                [
                    "Employer: Kauri Build Ltd",
                    "Job title: Carpenter",
                    "Employment start: 5 August 2024",
                    "Applicant signature: [signed]   Date: 20 October 2026",
                ],
            ],
            "employer-letter.pdf": [
                [
                    "Kauri Build Ltd - letter of employment (" + SAMPLE + ")",
                    "To whom it may concern",
                    "Danial Placeholder has worked for us as a carpenter since 5 September 2024.",
                    "He works 45 hours a week at NZD 35.50 per hour.",
                    "Signed: [signed] R. Kauri, Director",
                ]
            ],
            "bank-statement.pdf": [
                [
                    "Example Bank - account statement (" + SAMPLE + ")",
                    "Account holder: Daniel Placeholder",
                    "Statement period: 1 October 2022 to 31 October 2022",
                    "Address on 31 October 2022: Flat 2, 40 Harbour Quay, Wellington 6011",
                ]
            ],
            "cover-letter.pdf": [
                [
                    "Cover letter - AEWV application for Daniel Placeholder (" + SAMPLE + ")",
                    "Enclosed: Appendix 1 passport; Appendix 2 application form;",
                    "Appendix 3 employer letter; Appendix 4 bank statement.",
                ]
            ],
        },
        {
            "passport-scan.png": [
                "PASSPORT (" + SAMPLE + ")",
                "Surname: PLACEHOLDER",
                "Given names: DANIEL",
                "Date of birth: 14 MAY 1991",
                "Passport no: XD5590321",
                "Date of expiry: 22 FEB 2031",
            ]
        },
    ),
    "3-not-ready-to-lodge": (
        "3 · Not ready to lodge — Sofia Example, aged-care worker (AEWV): "
        "unsigned, missing, untranslated",
        {
            "application-form.pdf": [
                [
                    "Accredited Employer Work Visa - application form (" + SAMPLE + ")",
                    "Family name: Example   Given names: Sofia",
                    "Date of birth: 2 November 1996",
                    "Passport number: XC7710045",
                    "Residential address: 5 Kowhai Crescent, Palmerston North 4410, since May 2023",
                ],
                [
                    "Employer: Sunrise Care Home Ltd",
                    "Job title: Health care assistant",
                    "Employment start: 1 December 2026",
                    "Applicant signature: ____________   Date: ________",
                ],
            ],
            "job-offer.pdf": [
                [
                    "Sunrise Care Home Ltd - offer of employment (" + SAMPLE + ")",
                    "Employee: Sofia Example",
                    "Position: Health care assistant, permanent full-time, NZD 29.66 per hour",
                    "Start date: 1 December 2026",
                    "Employer signature: [signed] M. Sunrise, Manager   Date: 9 October 2026",
                    "Employee signature: ____________   Date: ________",
                ]
            ],
            "birth-certificate-spanish.pdf": [
                [
                    "Republica de Chile - Certificado de nacimiento (" + SAMPLE + ")",
                    "Nombre: Sofia Example",
                    "Fecha de nacimiento: 2 de noviembre de 1996",
                    "Lugar de nacimiento: Valparaiso",
                    "Este documento no incluye traduccion al ingles.",
                ]
            ],
            "cover-letter.pdf": [
                [
                    "Cover letter - AEWV application for Sofia Example (" + SAMPLE + ")",
                    "Enclosed: Appendix 1 passport; Appendix 2 application form;",
                    "Appendix 3 offer of employment; Appendix 4 birth certificate;",
                    "Appendix 5 police certificate (Chile); Appendix 6 recent payslip.",
                    "The client will send a medical certificate to follow.",
                ]
            ],
        },
        {
            "passport-scan.png": [
                "PASSPORT (" + SAMPLE + ")",
                "Surname: EXAMPLE",
                "Given names: SOFIA",
                "Date of birth: 02 NOV 1996",
                "Passport no: XC7710045",
                "Date of expiry: 30 JUN 2034",
            ]
        },
    ),
    "4-inz-letter-reply": (
        "4 · INZ letter, reply due 10 Nov 2026 — Daniel Placeholder (AEWV): "
        "concerns mapped to evidence",
        {},  # filled below: the case 2 documents, an English test result and the letter
        {},
    ),
}

NOTES = """# Adviser file notes - Priya Sample (SAMPLE - fictional)

- 14 October 2026: all documents received from the client; checked against the cover letter.
- Documents the client promised to send: none outstanding.
"""

ENGLISH_TEST: Pages = [
    [
        "English language test - test report form (" + SAMPLE + ")",
        "Candidate: Daniel Placeholder   Date of birth: 14 May 1990",
        "Test date: 7 June 2026",
        "Overall band score: 6.5 (listening 7.0, reading 6.5, writing 6.0, speaking 6.5)",
    ]
]

# The letter about case 4 (upload it as "INZ letter", then "Prepare reply").
LETTER: Pages = [
    [
        "Immigration New Zealand (" + SAMPLE + ")",
        "Our reference: SAMPLE-2026-0417",
        "27 October 2026",
        "Dear Daniel Placeholder",
        "Re: Accredited Employer Work Visa application - potentially prejudicial information",
        "Before we decide your application we want you to comment on the following.",
        "1. Your application form gives your date of birth as 14 May 1990. Your passport",
        "gives 14 May 1991.",
        "2. Your application form says you started with Kauri Build Ltd on 5 August 2024.",
        "Your employer's letter says 5 September 2024.",
        "3. Please provide evidence that you meet the English language requirement.",
    ],
    [
        "4. Please provide a police certificate from Australia, where you lived for more",
        "than 12 months.",
        "5. Please explain where you lived between January 2021 and October 2022.",
        "You must respond by 10 November 2026. If you do not respond, we will decide your",
        "application on the information we hold.",
        "Yours sincerely",
        "S. Officer, Immigration Officer",
    ],
]

EXPECTED = {
    "1-ready-to-lodge": [
        "What it shows: no false alarms. A clean file comes back clean, and every checklist item "
        "is checked with its source.",
        "Consistency check: 0 conflicts. The form's 'Employment start: March 2024' and the offer's "
        "'18 March 2024' agree at month precision, and the passport's SURNAME / GIVEN NAMES "
        "fields are the same name as 'Priya Sample', so neither is a conflict.",
        "Pre-submission check: every item 'checked', each with its source (the adviser's notes "
        "say nothing is outstanding from the client).",
    ],
    "2-conflicting-facts": [
        "What it shows: facts compared across every document, each conflict with both sources "
        "and a question to ask the client.",
        "Consistency check, 4 conflicts: date of birth (form 1990, passport scan 1991, read from "
        "the image); name ('Danial' in the employer letter); employment start (5 Aug vs 5 Sep "
        "2024); address (Hamilton since Jan 2021, but a Wellington bank statement in Oct 2022).",
        "Click any source to open the page with the quote highlighted.",
    ],
    "3-not-ready-to-lodge": [
        "What it shows: what would stop the file being lodged, item by item, and nothing glossed "
        "over.",
        "Pre-submission check, pending: forms not signed (the application form and the offer "
        "lack the applicant's signature); a document not in English without a translation "
        "(Spanish birth certificate); attachments cited but missing (Appendix 5 police "
        "certificate, Appendix 6 payslip); a medical certificate promised 'to follow'.",
        "The blurred payslip photo is reported as unreadable, never as clean.",
    ],
    "4-inz-letter-reply": [
        "What it shows: an INZ letter read for its deadline and every concern, each concern "
        "matched to what the file does and does not prove, and a draft email to the client.",
        "Upload the letter as 'INZ letter', then 'Prepare reply'.",
        "Deadline 10 November 2026, with the quote and the working days left.",
        "Concerns: date of birth (conflicting evidence); employment start (conflicting); English "
        "(supported by the test report, band 6.5); Australian police certificate (no evidence); "
        "where they lived Jan 2021 - Oct 2022 (only partly covered).",
    ],
}


def write_pdf(path: Path, pages: Pages) -> None:
    canvas = Canvas(str(path), pagesize=A4, invariant=1)
    canvas.setTitle(path.stem)
    for lines in pages:
        y = 800.0
        for line in lines:
            canvas.drawString(56, y, line)
            y -= 22
        canvas.showPage()
    canvas.save()


def write_scan(path: Path, lines: list[str], blur: float = 0.0) -> None:
    image = Image.new("RGB", (1000, 380), "white")
    draw = ImageDraw.Draw(image)
    for n, line in enumerate(lines):
        draw.text((40, 30 + n * 52), line, fill="black", font_size=28)
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(blur))
    image.save(path, format="PNG", optimize=False)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    _, docs2, scans2 = CASES["2-conflicting-facts"]
    CASES["4-inz-letter-reply"] = (
        CASES["4-inz-letter-reply"][0],
        {**docs2, "english-test-result.pdf": ENGLISH_TEST},
        scans2,
    )
    (OUT / "1-ready-to-lodge").mkdir(parents=True, exist_ok=True)
    (OUT / "1-ready-to-lodge" / "adviser-notes.md").write_text(NOTES, encoding="utf-8")
    guide = [
        "# Cairn showcase cases",
        "",
        "Synthetic AEWV files for the demo (every person, company and number is fictional).",
        "Create a case with the label below, upload the folder's files, run the checks named.",
        "",
    ]
    for folder, (label, docs, scans) in CASES.items():
        out = OUT / folder
        out.mkdir(exist_ok=True)
        for filename, pages in docs.items():
            write_pdf(out / filename, pages)
        for filename, lines in scans.items():
            write_scan(out / filename, lines)
        if folder == "3-not-ready-to-lodge":
            write_scan(out / "payslip-photo.png", ["PAYSLIP (" + SAMPLE + ")"] * 5, blur=9)
        guide += [f"## {label}", "", f"Folder: `{folder}/`", ""]
        guide += [f"- {line}" for line in EXPECTED[folder]] + [""]
    letters = OUT / "4-inz-letter"
    letters.mkdir(exist_ok=True)
    write_pdf(letters / "inz-ppi-letter.pdf", LETTER)
    (OUT / "SHOWCASE.md").write_text("\n".join(guide), encoding="utf-8")


if __name__ == "__main__":
    main()

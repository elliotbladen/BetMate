from datetime import datetime
import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.football.price_match import price_match

FIXTURES = [
    ("Lincoln", "Southampton"), ("Preston", "Blackburn"),
    ("Stoke", "Charlton"), ("Burnley", "Bristol City"),
    ("Millwall", "Bolton"), ("Portsmouth", "Cardiff"),
    ("QPR", "Middlesbrough"), ("Sheffield United", "Norwich"),
    ("West Brom", "Watford"), ("West Ham", "Derby"),
    ("Swansea", "Wrexham"), ("Birmingham", "Wolves"),
]

# Confirmed/clearly unavailable first-team players at the 2026-09-03 audit.
# Doubtful and stale entries are excluded because T5 treats each input as a
# full positional absence rather than a fractional availability probability.
ABSENCES = {
    "Lincoln": [("Ethan Bradley", "CM"), ("Tendayi Darikwa", "RB"), ("Aaron Collins", "ST")],
    "Southampton": [("Taylor Harwood-Bellis", "CB"), ("Caspar Jander", "CM")],
    "Stoke": [("Junior Tchamadeu", "RB"), ("Ato Ampah", "CM"),
              ("Lamine Cisse", "CM"), ("Svante Ingelsson", "CM"),
              ("Ben Gibson", "CB")],
    "Charlton": [("Nathaniel Chalobah", "DM"), ("Miles Leaburn", "ST")],
    "Millwall": [("Massimo Luongo", "CM"), ("Mihailo Ivanovic", "ST"),
                 ("Mathis Servais", "ST"), ("Femi Azeez", "RW"),
                 ("Zak Sturge", "LB")],
    "Bolton": [("Luca Stephenson", "CM")],
    "Sheffield United": [("Tahith Chong", "AM"), ("Ryan One", "ST")],
    "Norwich": [("Mirko Topic", "CM"), ("Lucien Mahovo", "LB"),
                ("Jovon Makama", "ST"), ("Edmond-Paris Maghoma", "CM"),
                ("Ali Ahmed", "CM"), ("Harry Darling", "CB"),
                ("Jose Cordoba", "CB")],
    "Swansea": [("Cameron Burgess", "CB"), ("Goncalo Franco", "CM"),
                ("Marko Stamenic", "CM")],
    "Wrexham": [("Liberato Cacace", "LB"), ("George Thomason", "CM"),
                ("Ben Sheaf", "CM")],
    "Birmingham": [("Marc Leonard", "CM"), ("Bright Osayi-Samuel", "RB")],
    "Wolves": [("Kieran Trippier", "RB"), ("Yerson Mosquera", "CB"),
               ("Rafiki Said", "ST"), ("Toti Gomes", "CB")],
}

for home, away in FIXTURES:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = price_match(
                home, away, as_of=datetime(2026, 9, 5),
                league="championship", matchweek=4,
                injuries_home=[position for _, position in ABSENCES.get(home, [])],
                injuries_away=[position for _, position in ABSENCES.get(away, [])],
            )
        fields = ["p_home", "p_draw", "p_away", "p_over25", "p_under25"]
        print("RESULT|" + home + "|" + away + "|" +
              "|".join(f"{result[key]:.6f}" for key in fields))
    except Exception as exc:
        print(f"ERROR|{home}|{away}|{exc!r}")

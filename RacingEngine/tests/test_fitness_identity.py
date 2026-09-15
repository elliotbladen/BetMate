import tempfile
from pathlib import Path
from RacingEngine.racing_engine.storage import RacingStore
from RacingEngine.racing_engine.fitness_identity import link_rows


def store():
    s = RacingStore(Path(tempfile.mkdtemp()) / "x.sqlite")
    s.connection.execute("INSERT INTO horses VALUES (?,?,?,?,?,?,?)", ("hrs_a", "Fast Horse", "fasthorse", "automatic", "{}", "now", "now"))
    s.connection.execute("INSERT INTO horses VALUES (?,?,?,?,?,?,?)", ("hrs_b", "Other Horse", "otherhorse", "automatic", "{}", "now", "now"))
    s.connection.execute("INSERT INTO horse_aliases VALUES (?,?,?,?,?,?,?)", ("rnsw", "F. Horse", "hrs_a", "Fast Horse", "automatic", "{}", "now"))
    s.connection.commit(); return s


def test_exact_alias_and_unresolved():
    s = store(); result = link_rows(s, [{"source":"rnsw", "horse_name":"F. Horse"}, {"source":"rnsw", "horse_name":"Unknown"}])
    assert result["linked_rows"][0]["horse_id"] == "hrs_a"
    assert result["quarantined_rows"][0]["quarantine_reason"] == "no_registry_match"


def test_ambiguous_is_quarantined():
    s = store(); s.connection.execute("INSERT INTO horse_aliases VALUES (?,?,?,?,?,?,?)", ("rnsw", "Same Name", "hrs_a", "Fast Horse", "automatic", "{}", "now"));
    s.connection.execute("INSERT INTO horse_aliases VALUES (?,?,?,?,?,?,?)", ("racing", "Same Name", "hrs_b", "Other Horse", "automatic", "{}", "now")); s.connection.commit()
    result = link_rows(s, [{"source":"rnsw", "horse_name":"Same Name"}])
    assert result["quarantined_rows"][0]["quarantine_reason"] == "multiple_horse_candidates"

from src.fact_checks import SQL_FILE, load_checks


def test_load_checks_splits_by_header():
    text = "-- preamble\n\n-- F01 | Page | First\nSELECT 1;\n\n-- F02 | Page | Second\nSELECT 2;\n"
    assert load_checks(text) == [("F01 | Page | First", "SELECT 1;"), ("F02 | Page | Second", "SELECT 2;")]


def test_fact_checks_file_has_one_read_query_per_fact():
    checks = load_checks(SQL_FILE.read_text(encoding="utf-8"))
    ids = [title.split(" |")[0] for title, _ in checks]
    assert len(ids) == len(set(ids)) >= 30
    for title, query in checks:
        code = [line for line in query.splitlines() if line.strip() and not line.lstrip().startswith("--")]
        assert code[0].split()[0].upper() in ("SELECT", "WITH"), title

import json
from pathlib import Path

import pytest

from travelbook.cli import main
from travelbook.stitch import (
    SKELETON_DIRS,
    StitchError,
    aggregate,
    create_skeleton,
    safe_filename,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE = EXAMPLES / "pyrenees.json"
EXAMPLE_PIECES = EXAMPLES / "pyrenees_pieces"


def test_example_pieces_reassemble_the_example():
    # the committed fragment directory must stitch back to pyrenees.json exactly
    assert aggregate(EXAMPLE_PIECES) == json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _fragment_dir(tmp_path, *, dir_names=None, with_td=True, with_default=True):
    """Split the pyrenees example into a fragment directory under ``tmp_path``.

    ``dir_names`` overrides the four array-folder names (to exercise the
    accepted alternate spellings)."""
    src = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    names = {
        "days": "days", "transport": "transports",
        "accommodations": "accommodations", "car_rentals": "car-rentals",
    }
    if dir_names:
        names.update(dir_names)
    root = tmp_path / "trip"
    root.mkdir()
    if with_td:
        (root / "travel_description.json").write_text(
            json.dumps(src["travel_description"]), encoding="utf-8")
    if with_default:
        (root / "default.json").write_text(json.dumps(src["default"]), encoding="utf-8")
    for key, folder in names.items():
        d = root / folder
        d.mkdir()
        for i, entry in enumerate(src[key], 1):
            (d / f"{i:02d}.json").write_text(json.dumps(entry), encoding="utf-8")
    return root, src


def test_aggregate_reproduces_the_example(tmp_path):
    root, src = _fragment_dir(tmp_path)
    assert aggregate(root) == src


def test_aggregate_orders_entries_by_filename(tmp_path):
    root, src = _fragment_dir(tmp_path)
    data = aggregate(root)
    assert [d["title"] for d in data["days"]] == [d["title"] for d in src["days"]]


def test_alternate_directory_spellings(tmp_path):
    # a dropped 'm' in accommodations and an underscore in car_rentals still load
    root, src = _fragment_dir(
        tmp_path,
        dir_names={"accommodations": "accomodations", "car_rentals": "car_rentals"},
    )
    data = aggregate(root)
    assert len(data["accommodations"]) == len(src["accommodations"])
    assert len(data["car_rentals"]) == len(src["car_rentals"])


def test_a_file_may_hold_an_array_of_entries(tmp_path):
    root, src = _fragment_dir(tmp_path)
    # collapse the three transport files into one array file
    tdir = root / "transports"
    for p in tdir.glob("*.json"):
        p.unlink()
    (tdir / "all.json").write_text(json.dumps(src["transport"]), encoding="utf-8")
    assert aggregate(root)["transport"] == src["transport"]


def test_prompt_used_when_no_travel_description(tmp_path):
    root, _ = _fragment_dir(tmp_path, with_td=False)
    answers = iter(["Prompted Trip", "", "", "", "#abc123", "A summary."])
    data = aggregate(root, ask=lambda _prompt: next(answers))
    assert data["travel_description"] == {
        "title": "Prompted Trip", "cover_color": "#abc123", "summary": "A summary."}


def test_prompt_reasks_for_required_title(tmp_path):
    root, _ = _fragment_dir(tmp_path, with_td=False)
    # blanks rejected until a title is given; later blanks skip optional fields
    answers = iter(["", "   ", "Finally"])
    data = aggregate(root, ask=lambda _prompt: next(answers, ""))
    assert data["travel_description"] == {"title": "Finally"}


def test_no_days_is_an_error(tmp_path):
    root, _ = _fragment_dir(tmp_path)
    for p in (root / "days").glob("*.json"):
        p.unlink()
    with pytest.raises(StitchError):
        aggregate(root)


def test_missing_directory_is_an_error(tmp_path):
    with pytest.raises(StitchError):
        aggregate(tmp_path / "nope")


def test_invalid_json_fragment_is_an_error(tmp_path):
    root, _ = _fragment_dir(tmp_path)
    (root / "days" / "01.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(StitchError):
        aggregate(root)


def test_safe_filename():
    assert safe_filename("Pyrenees Road Trip") == "Pyrenees Road Trip"
    assert safe_filename("A/B: trip?") == "A-B- trip-"
    assert safe_filename("   ") == "itinerary"


def test_cli_stitch_writes_titled_file(tmp_path, capsys):
    root, src = _fragment_dir(tmp_path)
    rc = main(["stitch", str(root)])
    assert rc == 0  # the example has warnings but no errors
    out = root / "Pyrenees Road Trip.json"
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == src
    assert "Wrote" in capsys.readouterr().out


def test_cli_stitch_missing_dir_returns_1(tmp_path, capsys):
    rc = main(["stitch", str(tmp_path / "nope")])
    assert rc == 1
    assert "error:" in capsys.readouterr().err


def test_create_skeleton_lays_out_dirs_and_stub(tmp_path):
    root = create_skeleton(tmp_path, "mytrip")
    assert root == tmp_path / "mytrip"
    for d in ("days", "transports", "accommodations", "car-rentals"):
        assert (root / d).is_dir()
    td = json.loads((root / "travel_description.json").read_text(encoding="utf-8"))
    assert td == {"title": "FIXME"}


def test_created_skeleton_dirs_are_read_by_stitch():
    # the folders create_skeleton lays down are exactly what aggregate reads back
    assert SKELETON_DIRS == ["days", "transports", "accommodations", "car-rentals"]


def test_create_skeleton_refuses_to_clobber(tmp_path):
    create_skeleton(tmp_path, "mytrip")
    with pytest.raises(StitchError):
        create_skeleton(tmp_path, "mytrip")


def test_cli_create_skeleton_then_stitch_roundtrip(tmp_path, capsys):
    rc = main(["create-skeleton", str(tmp_path), "mytrip"])
    assert rc == 0
    assert "Created skeleton" in capsys.readouterr().out
    root = tmp_path / "mytrip"

    # a freshly-scaffolded skeleton has no days yet → stitch reports an error
    assert main(["stitch", str(root)]) == 1

    # drop in one minimal day and it stitches successfully
    (root / "days" / "1.json").write_text(
        json.dumps({"title": "Day 1", "activities": [
            {"type": "place", "name": "Somewhere"}]}),
        encoding="utf-8")
    assert main(["stitch", str(root)]) == 0
    assert (root / "FIXME.json").exists()  # title stub drives the output name

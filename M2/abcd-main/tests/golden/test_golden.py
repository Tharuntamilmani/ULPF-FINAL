import os
import glob
import json
import pytest
from app.classifier.detector import Classifier
from app.registry.repository import ParserRepository
from app.registry.service import ParserRegistryService
from app.models.envelope import RawEventEnvelope

GOLDEN_DIR = os.path.dirname(__file__)


def get_golden_test_cases():
    test_cases = []
    subdirs = [
        d for d in os.listdir(GOLDEN_DIR) if os.path.isdir(os.path.join(GOLDEN_DIR, d))
    ]
    for sd in subdirs:
        dir_path = os.path.join(GOLDEN_DIR, sd)
        input_files = glob.glob(os.path.join(dir_path, "input_*.log"))
        for inf in input_files:
            basename = os.path.basename(inf).replace("input_", "").replace(".log", "")
            expf = os.path.join(dir_path, f"expected_{basename}.json")
            if os.path.exists(expf):
                test_cases.append((sd, inf, expf))
    return test_cases


@pytest.mark.parametrize("category,input_file,expected_file", get_golden_test_cases())
def test_golden_sample(category, input_file, expected_file):
    repo = ParserRepository()
    parsers_dir = os.path.join(os.path.dirname(__file__), "../../parsers")
    repo.load_from_directory(parsers_dir)
    service = ParserRegistryService(repo)
    classifier = Classifier()

    with open(input_file, "r", encoding="utf-8") as f:
        payload = f.read().strip()

    with open(expected_file, "r", encoding="utf-8") as f:
        expected = json.load(f)

    envelope = RawEventEnvelope(raw_event_id=f"golden_{category}", payload=payload)
    classification = classifier.classify(envelope)

    if "format" in expected:
        assert classification.format.lower() == expected["format"].lower()

    if "vendor" in expected:
        assert classification.vendor.lower() == expected["vendor"].lower()

    executable, defn = service.find_parser(classification, envelope.model_dump())
    assert executable is not None

    extracted = executable.parse(envelope.model_dump())
    for exp_k, exp_v in expected.get("fields", {}).items():
        assert exp_k in extracted, f"Missing field '{exp_k}' in extracted output"
        assert extracted[exp_k] == exp_v, (
            f"Mismatch for field '{exp_k}': got {extracted[exp_k]}, expected {exp_v}"
        )

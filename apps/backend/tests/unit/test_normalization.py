from datetime import timezone
from app.services.normalization import (
    compute_content_hash,
    normalize_date,
    extract_cvss_v3,
)


def test_compute_content_hash():
    data1 = {"a": 1, "b": {"c": 2}}
    data2 = {"b": {"c": 2}, "a": 1}
    # Should be identical despite dict order
    assert compute_content_hash(data1) == compute_content_hash(data2)


def test_normalize_date():
    assert normalize_date(None) is None

    # Naive date assumes UTC
    dt1 = normalize_date("2024-01-01T10:00:00")
    assert dt1.tzinfo == timezone.utc

    # Z timezone
    dt2 = normalize_date("2024-01-01T10:00:00Z")
    assert dt2.tzinfo == timezone.utc

    # Offset timezone
    dt3 = normalize_date("2024-01-01T10:00:00-05:00")
    assert dt3.tzinfo == timezone.utc
    assert dt3.hour == 15  # 10am EST is 3pm UTC

    # Invalid
    assert normalize_date("invalid") is None


def test_extract_cvss_v3():
    # NVD 3.1
    raw_nvd_31 = {
        "metrics": {
            "cvssMetricV31": [
                {
                    "cvssData": {
                        "baseScore": 9.8,
                        "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                    }
                }
            ]
        }
    }
    score, vector = extract_cvss_v3(raw_nvd_31)
    assert score == 9.8
    assert vector == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"

    # OSV format
    raw_osv = {
        "cvss_v3_score": 7.5,
        "cvss_v3_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
    }
    score, vector = extract_cvss_v3(raw_osv)
    assert score == 7.5
    assert vector == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H"

    # None
    score, vector = extract_cvss_v3({"other": 1})
    assert score is None
    assert vector is None

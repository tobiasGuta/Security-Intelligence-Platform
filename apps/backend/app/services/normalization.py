import hashlib
import json
import typing
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.vulnerability import (
    Vulnerability,
    VulnerabilitySourceRecord,
    VulnerabilityProvenance,
    VulnerabilityDisagreement,
)


def compute_content_hash(data: dict) -> str:
    """Computes a stable SHA-256 hash of a JSON-serializable dictionary."""
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def normalize_date(date_str: str | None) -> datetime | None:
    """Parses an ISO-8601 date string and ensures it is UTC."""
    if not date_str:
        return None
    try:
        # replace Z with +00:00 for python 3.10 and below compatibility (even though 3.11+ handles Z)
        date_str = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            # Assume UTC if naive
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC
            dt = dt.astimezone(timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def extract_cvss_v3(raw_data: dict) -> tuple[float | None, str | None]:
    """
    Attempts to parse CVSS v3 score and vector from common payload structures.
    Supports basic structures found in NVD or OSV.
    """
    # Try NVD format
    if "metrics" in raw_data and "cvssMetricV31" in raw_data["metrics"]:
        cvss = raw_data["metrics"]["cvssMetricV31"][0]["cvssData"]
        return float(cvss.get("baseScore")), cvss.get("vectorString")
    elif "metrics" in raw_data and "cvssMetricV30" in raw_data["metrics"]:
        cvss = raw_data["metrics"]["cvssMetricV30"][0]["cvssData"]
        return float(cvss.get("baseScore")), cvss.get("vectorString")

    # Try OSV or general flat format if present
    if "cvss_v3_score" in raw_data and "cvss_v3_vector" in raw_data:
        return float(raw_data["cvss_v3_score"]), raw_data.get("cvss_v3_vector")

    return None, None


async def ingest_vulnerability_record(
    db: AsyncSession,
    source_name: str,
    cve_id: str,
    raw_data: dict,
    published_at_str: str | None = None,
    description: str | None = None,
) -> Vulnerability:
    """
    Ingests a raw vulnerability record, normalizes it, handles deduplication,
    provenance, and disagreements.
    """
    content_hash = compute_content_hash(raw_data)

    # Check if this exact source record already exists (deduplication)
    existing_record_stmt = (
        select(VulnerabilitySourceRecord)
        .where(
            VulnerabilitySourceRecord.source_name == source_name,
            VulnerabilitySourceRecord.content_hash == content_hash,
        )
        .join(VulnerabilitySourceRecord.vulnerability)
        .where(Vulnerability.cve_id == cve_id)
    )
    existing_record = (await db.execute(existing_record_stmt)).scalars().first()

    if existing_record:
        # Duplicate record, skip
        stmt = (
            select(Vulnerability)
            .where(Vulnerability.id == existing_record.vulnerability_id)
            .options(
                selectinload(Vulnerability.source_records),
                selectinload(Vulnerability.provenances),
                selectinload(Vulnerability.disagreements),
            )
        )

        return typing.cast(Vulnerability, (await db.execute(stmt)).scalars().first())

    # Normalize fields
    published_dt = normalize_date(published_at_str)
    cvss_score, cvss_vector = extract_cvss_v3(raw_data)

    # Find or create Vulnerability
    stmt = (
        select(Vulnerability)
        .where(Vulnerability.cve_id == cve_id)
        .options(
            selectinload(Vulnerability.source_records),
            selectinload(Vulnerability.provenances),
            selectinload(Vulnerability.disagreements),
        )
    )
    vuln = (await db.execute(stmt)).scalars().first()

    if not vuln:
        vuln = Vulnerability(
            cve_id=cve_id,
            description=None,
            cvss_v3_score=None,
            cvss_v3_vector=None,
            published_at=None,
            source_records=[],
            provenances=[],
            disagreements=[],
        )
        db.add(vuln)
        await db.flush()  # get ID

    # Create the Source Record
    source_record = VulnerabilitySourceRecord(
        vulnerability_id=vuln.id,
        source_name=source_name,
        raw_data=raw_data,
        content_hash=content_hash,
    )
    db.add(source_record)
    await db.flush()
    vuln.source_records.append(source_record)

    # Provenance and Disagreement logic
    fields_to_check = {
        "description": description,
        "cvss_v3_score": cvss_score,
        "cvss_v3_vector": cvss_vector,
        "published_at": published_dt,
    }

    for field, new_value in fields_to_check.items():
        if new_value is None:
            continue

        current_prov = next(
            (p for p in vuln.provenances if p.field_name == field), None
        )
        if current_prov:
            current_value = getattr(vuln, field)
            is_different = current_value != new_value

            if field == "cvss_v3_score" and current_value is not None and new_value is not None:
                is_different = float(str(current_value)) != float(str(new_value))

            if is_different:
                disagreement = VulnerabilityDisagreement(
                    vulnerability_id=vuln.id,
                    source_record_id=source_record.id,
                    field_name=field,
                    conflicting_value={"value": str(new_value)}
                    if isinstance(new_value, datetime)
                    else {"value": new_value},
                )
                db.add(disagreement)
                vuln.disagreements.append(disagreement)
        else:
            # No provenance yet, so we become the provenance
            setattr(vuln, field, new_value)
            provenance = VulnerabilityProvenance(
                vulnerability_id=vuln.id,
                source_record_id=source_record.id,
                field_name=field,
            )
            db.add(provenance)
            vuln.provenances.append(provenance)

    await db.commit()
    return vuln

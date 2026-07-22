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
    VulnerabilityCvss,
    CvssVersion,
    ProcessingStatus,
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
        date_str = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def normalize_cve_id(cve_id: str) -> str:
    """Trims and uppercases a CVE ID."""
    return cve_id.strip().upper()


def extract_cvss_v3(raw_data: dict) -> tuple[float | None, str | None]:
    if "metrics" in raw_data and "cvssMetricV31" in raw_data["metrics"]:
        cvss = raw_data["metrics"]["cvssMetricV31"][0]["cvssData"]
        return float(cvss.get("baseScore")), cvss.get("vectorString")
    elif "metrics" in raw_data and "cvssMetricV30" in raw_data["metrics"]:
        cvss = raw_data["metrics"]["cvssMetricV30"][0]["cvssData"]
        return float(cvss.get("baseScore")), cvss.get("vectorString")

    if "cvss_v3_score" in raw_data and "cvss_v3_vector" in raw_data:
        return float(raw_data["cvss_v3_score"]), raw_data.get("cvss_v3_vector")

    return None, None


# Lower number = higher priority
SOURCE_PRIORITY = {
    "NVD": 10,
    "CISA_KEV": 20,
    "OSV": 30,
    "GITHUB": 40,
}


def get_source_priority(source_name: str) -> int:
    return SOURCE_PRIORITY.get(source_name.upper(), 100)


async def ingest_vulnerability_record(
    db: AsyncSession,
    source_name: str,
    cve_id: str,
    raw_data: dict,
) -> Vulnerability:
    """
    Ingests a raw vulnerability record, normalizes it, handles deduplication,
    provenance, and disagreements. Does NOT commit transaction.
    """
    cve_id = normalize_cve_id(cve_id)
    content_hash = compute_content_hash(raw_data)

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
        stmt = (
            select(Vulnerability)
            .where(Vulnerability.id == existing_record.vulnerability_id)
            .options(
                selectinload(Vulnerability.source_records),
                selectinload(Vulnerability.provenances),
                selectinload(Vulnerability.disagreements),
                selectinload(Vulnerability.cvss_assessments),
            )
        )
        return typing.cast(Vulnerability, (await db.execute(stmt)).scalars().first())

    # Extract fields from raw_data
    published_dt = normalize_date(raw_data.get("published_at"))
    description = raw_data.get("description")
    title = raw_data.get("title")
    cvss_score, cvss_vector = extract_cvss_v3(raw_data)

    stmt = (
        select(Vulnerability)
        .where(Vulnerability.cve_id == cve_id)
        .options(
            selectinload(Vulnerability.source_records),
            selectinload(Vulnerability.provenances),
            selectinload(Vulnerability.disagreements),
            selectinload(Vulnerability.cvss_assessments),
        )
    )
    vuln = (await db.execute(stmt)).scalars().first()

    if not vuln:
        vuln = Vulnerability(
            cve_id=cve_id,
            description=None,
            title=None,
            published_at=None,
            source_records=[],
            provenances=[],
            disagreements=[],
            cvss_assessments=[],
        )
        db.add(vuln)
        # We need the ID for the source record and provenance, so we must flush, but we won't commit.
        await db.flush()

    source_record = VulnerabilitySourceRecord(
        vulnerability_id=vuln.id,
        source_name=source_name,
        raw_data=raw_data,
        content_hash=content_hash,
        processing_status=ProcessingStatus.SUCCESS,
        is_current=True,
    )
    db.add(source_record)

    # Mark older records from same source as not current
    for sr in vuln.source_records:
        if sr.source_name == source_name:
            sr.is_current = False

    await db.flush()
    vuln.source_records.append(source_record)

    fields_to_check = {
        "description": description,
        "title": title,
        "published_at": published_dt,
    }

    new_priority = get_source_priority(source_name)

    for field, new_value in fields_to_check.items():
        if new_value is None:
            continue

        current_prov = next(
            (p for p in vuln.provenances if p.field_name == field), None
        )

        should_overwrite = False
        reason = None

        if current_prov:
            current_value = getattr(vuln, field)
            is_different = current_value != new_value

            if is_different:
                # Compare priorities
                existing_priority = (
                    get_source_priority(current_prov.source_record.source_name)
                    if getattr(current_prov, "source_record", None)
                    else 100
                )

                if new_priority < existing_priority:
                    should_overwrite = True
                    reason = f"Priority {new_priority} < {existing_priority}"
                elif new_priority == existing_priority:
                    # Same source, newer record wins
                    should_overwrite = True
                    reason = "Newer record from same source"
                else:
                    # Lower priority, log disagreement
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
            should_overwrite = True
            reason = "First record for field"

        if should_overwrite:
            setattr(vuln, field, new_value)

            if current_prov:
                # Log old canonical value as disagreement from the old source if we are overwriting
                old_val = getattr(vuln, field)
                if old_val is not None:
                    old_disagreement = VulnerabilityDisagreement(
                        vulnerability_id=vuln.id,
                        source_record_id=current_prov.source_record_id,
                        field_name=field,
                        conflicting_value={"value": str(old_val)}
                        if isinstance(old_val, datetime)
                        else {"value": old_val},
                    )
                    db.add(old_disagreement)
                    vuln.disagreements.append(old_disagreement)

                # Update provenance
                current_prov.source_record_id = source_record.id
                current_prov.selection_reason = reason
            else:
                provenance = VulnerabilityProvenance(
                    vulnerability_id=vuln.id,
                    source_record_id=source_record.id,
                    field_name=field,
                    selection_reason=reason,
                )
                db.add(provenance)
                vuln.provenances.append(provenance)

    # Handle CVSS in typed table
    if cvss_score is not None:
        cvss_assessment = VulnerabilityCvss(
            vulnerability_id=vuln.id,
            source_record_id=source_record.id,
            version=CvssVersion.V3_1,
            score=cvss_score,
            vector=cvss_vector,
        )
        db.add(cvss_assessment)
        vuln.cvss_assessments.append(cvss_assessment)

    return vuln

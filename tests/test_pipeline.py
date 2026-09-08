import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.findings import build_findings_export
from app.intelligence import extract_indicators
from app.models import Asset, IOC, Incident, RawDocument, Source
from app.pipeline import create_incidents, persist_iocs


class PipelineTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_models_share_the_database_base(self):
        self.assertEqual(
            {"assets", "sources", "raw_documents", "iocs", "incidents"},
            set(Base.metadata.tables),
        )

    def test_local_fixture_persists_iocs_and_deduplicates_incidents(self):
        source = Source(
            name="Local fixture",
            url="http://fixture.local/report",
            source_type="osint",
            use_tor=False,
        )
        asset = Asset(
            name="Example domain",
            identifier="example.com",
            asset_type="domain",
            criticality=4,
        )
        self.db.add_all([source, asset])
        self.db.flush()

        fixture = Path(__file__).parents[1] / "fixtures" / "sample.html"
        body = fixture.read_text(encoding="utf-8")
        text, indicators = extract_indicators(body)
        document = RawDocument(
            source_id=source.id,
            url=source.url,
            body_raw=body,
            body_text=text,
            content_hash="a" * 64,
            status="normalized",
        )
        self.db.add(document)
        self.db.flush()

        persist_iocs(self.db, document, indicators)
        created = create_incidents(self.db, document)
        self.db.commit()

        self.assertGreaterEqual(self.db.query(IOC).count(), 1)
        self.assertGreaterEqual(len(created), 1)
        self.assertEqual(self.db.query(Incident).count(), len(created))
        self.assertEqual(create_incidents(self.db, document), [])

        export = build_findings_export(
            self.db.query(Incident).all(), "2026-01-01T00:00:00+00:00"
        )
        self.assertEqual(export["schema_version"], "1.0")
        self.assertEqual(
            export["findings"][0]["finding_type"],
            "threat_intelligence.asset_indicator_match",
        )
        self.assertEqual(export["findings"][0]["severity"], "high")


if __name__ == "__main__":
    unittest.main()

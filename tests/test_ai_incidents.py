import importlib.util
import io
import json
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("incidents", ROOT / "tools" / "ai_incidents.py")
incidents = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(incidents)
ENGINE_SPEC = importlib.util.spec_from_file_location("incident_intelligence_v2", ROOT / "tools" / "incident_intelligence_v2.py")
engine = importlib.util.module_from_spec(ENGINE_SPEC)
ENGINE_SPEC.loader.exec_module(engine)
MANIFEST_SPEC = importlib.util.spec_from_file_location('incident_manifest', ROOT / 'tools' / 'build_incident_release_manifest.py')
manifest_tool = importlib.util.module_from_spec(MANIFEST_SPEC)
MANIFEST_SPEC.loader.exec_module(manifest_tool)


def record(source_id="source-1", title="Test incident"):
    return incidents.ManualOOFIncidentAdapter().normalize({
        "title": title,
        "eventType": "Incident",
        "severity": "High",
        "evidenceConfidence": "Verified",
        "publicationStatus": "Monitored",
        "source": {
            "sourceId": source_id,
            "publisher": "Test Authority",
            "url": f"https://example.test/{source_id}",
            "verificationStatus": "Verified",
        },
    })


class IncidentDomainTests(unittest.TestCase):
    def test_aiid_dates_do_not_invent_publication_or_retrieval(self):
        adapter = incidents.AIIDWeeklyExcelAdapter()
        item = adapter.normalize({'Incident ID': 999, 'title': 'Test incident', 'date': '2026-10-30', '_snapshotUrl': 'https://example.test/AIID_Excel_Export-20261102.xlsx'})
        source = item['sources'][0]
        self.assertEqual(item['occurredAt'], '2026-10-30')
        self.assertIsNone(item['reportedAt'])
        self.assertIsNone(source['publicationDate'])
        self.assertEqual(source['snapshotDate'], '2026-11-02T00:00:00Z')
        self.assertNotEqual(source['retrievedAt'], source['snapshotDate'])
        legacy = {**source, 'publicationDate': '2026-10-30', 'retrievedAt': '2026-11-02T00:00:00Z'}
        legacy.pop('snapshotDate')
        cleaned = incidents.public_source(legacy)
        self.assertIsNone(cleaned['publicationDate'])
        self.assertIsNone(cleaned['retrievedAt'])
        self.assertEqual(cleaned['snapshotDate'], '2026-11-02T00:00:00Z')
        self.assertEqual(legacy['publicationDate'], '2026-10-30')
        manual = {'sourceId': 'manual:1', 'publicationDate': '2026-10-31'}
        self.assertEqual(incidents.public_source(manual)['publicationDate'], '2026-10-31')
        item['sources'] = [legacy]
        snapshot = engine.evidence_snapshot(item)['sources'][0]
        self.assertIsNone(snapshot['publicationTime'])
        self.assertIsNone(snapshot['retrievalTime'])
        self.assertEqual(snapshot['snapshotTime'], '2026-11-02T00:00:00Z')

    def test_aiid_legacy_date_correction_does_not_enqueue_every_record(self):
        item = record()
        item['sources'] = [{'sourceId': 'aiid:1', 'sourceType': 'Official weekly data export', 'publicationDate': '2026-10-30'}]
        updated = {**item, 'sources': [{**item['sources'][0], 'publicationDate': None}]}
        self.assertEqual(incidents.source_record_fingerprint(item), incidents.source_record_fingerprint(updated))

    def test_pending_analysis_is_not_published_as_available(self):
        item = record()
        item['automatedAnalysis'] = {'analysisStatus': 'GOVERNANCE_ANALYSIS_PENDING'}
        self.assertFalse(incidents._list_projection(item)['assessment']['available'])
        item['automatedAnalysis']['analysisStatus'] = 'AUTOMATED_ANALYSIS_AVAILABLE'
        self.assertTrue(incidents._list_projection(item)['assessment']['available'])

    def test_public_search_includes_incident_id(self):
        item = record()
        self.assertIn(item['id'].casefold(), incidents._list_projection(item)['searchText'])

    def test_ega_requires_supported_physical_energy_context(self):
        for text in ('AI-altered gun photograph used to threaten a former partner',
                     'AI coding assistant uploaded developer repositories without consent',
                     'No evidence of an electricity grid incident'):
            self.assertFalse(engine.has_physical_energy_context({'title': text}))
        self.assertTrue(engine.has_physical_energy_context({'title': 'AI outage disrupted an electricity grid'}))
        layer = engine.KnowledgeLayer.__new__(engine.KnowledgeLayer)
        layer.architectures = {'ega-id': {'acronym': 'EGA', 'canonicalName': 'Energy Governance Architecture'},
                               'pga-id': {'acronym': 'PGA', 'canonicalName': 'Prediction Governance Architecture'}}
        layer.corpora = {'ega-id': {'incident': 1, 'photograph': 1}, 'pga-id': {'photograph': 1}}
        layer.document_frequency = {'incident': 1, 'photograph': 2}
        ranked = layer.rank({'title': 'AI-altered gun photograph used to threaten a former partner'})
        self.assertNotIn('ega', [item['architectureId'] for item in ranked])

    def test_release_manifest_rejects_modified_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            public = root / 'data/ai-incidents/public'
            public.mkdir(parents=True)
            (public / 'summary.json').write_text(json.dumps({'totalIncidents': 0, 'automatedAnalyses': 0}), encoding='utf-8')
            for name in ['incident-index.json', 'incident-search.json']:
                (public / name).write_text(json.dumps({'items': []}), encoding='utf-8')
            for name in ['sitemap.xml', 'search-index.json', 'data/oof-site-knowledge-graph.json', 'assets/js/ai-incidents/app.js', 'assets/js/ai-incidents/repository.js', 'assets/css/oof-ai-incidents.css', 'ai-incidents/index.html']:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('test', encoding='utf-8')
            with mock.patch.object(manifest_tool, 'ROOT', root), mock.patch.object(manifest_tool, 'PUBLIC', public), mock.patch.object(manifest_tool, 'OUTPUT', public / 'release-manifest.json'), mock.patch.object(sys, 'argv', ['manifest']), mock.patch('builtins.print'):
                manifest_tool.main()
                (root / 'sitemap.xml').write_text('altered', encoding='utf-8')
                with mock.patch.object(sys, 'argv', ['manifest', '--verify']), self.assertRaises(SystemExit):
                    manifest_tool.main()

    def test_source_retry_recovers_from_transient_network_error(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'content'
        with mock.patch.object(incidents.urllib.request, 'urlopen', side_effect=[URLError('temporary'), response]) as request, mock.patch.object(incidents.time, 'sleep') as sleep:
            self.assertEqual(incidents.AIIDWeeklyExcelAdapter._request('https://example.test/data'), b'content')
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_source_does_not_retry_permanent_http_error(self):
        error = HTTPError('https://example.test/data', 404, 'missing', None, None)
        with mock.patch.object(incidents.urllib.request, 'urlopen', side_effect=error) as request, mock.patch.object(incidents.time, 'sleep') as sleep:
            with self.assertRaises(HTTPError):
                incidents.AIIDWeeklyExcelAdapter._request('https://example.test/data')
        self.assertEqual(request.call_count, 1)
        sleep.assert_not_called()

    def test_sync_entrypoint_fails_when_any_source_fails(self):
        with mock.patch.object(sys, 'argv', ['ai_incidents.py', 'sync']), mock.patch.object(incidents, 'sync', return_value={'sourceErrors': [{'source': 'AIID'}]}), mock.patch('builtins.print'):
            self.assertEqual(incidents.main(), 1)

    def test_production_sync_generates_incident_pages_before_discovery(self):
        workflow = (ROOT / '.github/workflows/ai-incident-daily-sync.yml').read_text(encoding='utf-8')
        self.assertIn('schedule:', workflow)
        self.assertIn('cron:', workflow)
        self.assertLess(workflow.index('python tools/build_ai_incident_pages.py'), workflow.index('python tools/build_ai_compatibility.py'))
        self.assertIn('python tools/validate_ai_compatibility.py', workflow)

    def test_real_vehicle_case_does_not_infer_memory_from_united_states(self):
        store = json.loads((ROOT / 'data/ai-incidents/incident-store.json').read_text(encoding='utf-8'))
        item = next(item for item in store['incidents'] if item['id'] == 'OOF-AII-134071')
        classification = engine.system_failure_classification(item)
        labels = {component['componentId'] for component in classification['components']}
        self.assertIn('physical-execution-robotics', labels)
        self.assertNotIn('memory-state', labels)
        self.assertNotIn('agent-planning-delegation', labels)
        self.assertIn('Autonomous and driver-assistance vehicles', classification['systemDomains'])
        self.assertEqual(classification['candidateFailureMechanisms'], [])

    def test_real_cyber_case_does_not_publish_unrelated_prediction_question(self):
        store = json.loads((ROOT / 'data/ai-incidents/incident-store.json').read_text(encoding='utf-8'))
        item = next(item for item in store['incidents'] if item['id'] == 'OOF-AII-403576')
        result = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, 'test', '2026-11-03T00:00:00Z')
        self.assertNotIn('collective prediction', (result.get('incidentGovernanceInsight') or '').lower())

    def test_missing_event_date_is_not_filled_from_record_timestamp(self):
        item = record(title='Event with unknown date')
        item['occurredAt'] = None
        item['reportedAt'] = '2026-10-15T00:00:00Z'
        report = engine.original_oof_report(item, engine.evidence_snapshot(item))
        self.assertIsNone(report['eventDate'])
        self.assertEqual(report['sourceRecordTimestamp'], '2026-10-15')
        self.assertIn('not established', report['sourceRecordTimestampNote'])

    def test_candidate_mechanism_requires_explicit_source_phrase(self):
        item = record(title='AI agent tested in the United States')
        item['summary'] = 'An AI agent was evaluated; the technical cause was not reported.'
        self.assertEqual(engine.system_failure_classification(item)['candidateFailureMechanisms'], [])
        item['summary'] = 'A source alleged unauthorized access by an AI agent.'
        candidate = engine.system_failure_classification(item)['candidateFailureMechanisms'][0]
        self.assertEqual(candidate['label'], 'Unauthorized action')
        self.assertEqual(candidate['status'], 'CANDIDATE')
        self.assertIn('not confirmed', candidate['rationale'])
        self.assertTrue(candidate['evidenceReferences'])
        item['summary'] = 'The investigation found no evidence of unauthorized access by the AI agent.'
        self.assertEqual(engine.system_failure_classification(item)['candidateFailureMechanisms'], [])

    def test_patterns_require_shared_domain_component_and_mechanism(self):
        def projection(identity, domain, component, mechanism, status='Source-Reported'):
            return {'id': identity, 'assessment': {'evidenceStatus': status}, 'systemFailure': {
                'domains': [domain], 'components': [component], 'candidateMechanisms': [mechanism]}}
        items = [projection('1', 'AI agents', 'Execution', 'Unauthorized action'),
                 projection('2', 'AI agents', 'Execution', 'Incorrect classification'),
                 projection('3', 'Robotics', 'Execution', 'Unauthorized action')]
        self.assertEqual(incidents.build_candidate_patterns(items, 't')['patterns'], [])
        items.append(projection('4', 'AI agents', 'Execution', 'Unauthorized action', 'Contradicted / Disputed'))
        self.assertEqual(incidents.build_candidate_patterns(items, 't')['patterns'], [])
        items.append(projection('5', 'AI agents', 'Execution', 'Unauthorized action'))
        result = incidents.build_candidate_patterns(items, 't')
        self.assertEqual(result['patterns'][0]['supportingIncidentIds'], ['1', '5'])
        self.assertEqual(result['patterns'][0]['status'], 'CANDIDATE')
        self.assertIsNone(result['patterns'][0]['contradictoryIncidentIds'])
        self.assertEqual(result['patterns'][0]['patternId'], incidents.build_candidate_patterns(list(reversed(items)), 't')['patterns'][0]['patternId'])
        updated = incidents.build_candidate_patterns(items + [projection('6', 'AI agents', 'Execution', 'Unauthorized action')], 't2', result)
        self.assertEqual(updated['patterns'][0]['version'], 2)
        self.assertEqual(updated['patterns'][0]['history'][0]['supportingIncidentIds'], ['1', '5'])
        retired = incidents.build_candidate_patterns(items[:1], 't3', updated)
        self.assertEqual(retired['patterns'][0]['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(retired['patterns'][0]['history'][-1]['supportingIncidentIds'], ['1', '5', '6'])

    def test_unconfirmed_mechanism_withholds_specific_prevention(self):
        item = record(title='Vehicle incident')
        architecture = {'primaryArchitecture': {'governedMechanism': 'self', 'label': 'Example'}}
        classification = {'technicalMechanismStatus': 'NOT_CONFIRMED', 'components': []}
        evidence = {'corroboration': {'independentSourceCount': 1}}
        result = engine.prevention_guidance(item, architecture, [], classification, evidence)
        self.assertIn('before control selection', result['recommendedPreventiveControl'].lower())
        self.assertNotIn('for self', result['recommendedPreventiveControl'].lower())

    def test_supported_signal_produces_only_conditional_test_guidance(self):
        item = record(title='AI agent alleged unauthorized access')
        item['summary'] = 'A source alleged unauthorized access by an AI agent.'
        classification = engine.system_failure_classification(item)
        evidence = engine.evidence_snapshot(item)
        result = engine.prevention_guidance(item, {'primaryArchitecture': None}, [], classification, evidence)
        self.assertEqual(result['status'], 'EVIDENCE_LIMITED')
        self.assertIn('deny', result['recommendedPreventiveControl'].lower())
        self.assertIn('not a verified cause', result['evidenceLimitation'])
        self.assertTrue(result['supportingEvidence'])
        self.assertTrue(result['howCanProtectionBeVerified']['failureCondition'])

    def test_physical_classification_does_not_assume_human_review_is_safe(self):
        item = record(title='Autopilot misidentified road object')
        item['summary'] = 'A self-driving vehicle reportedly misidentified a traffic signal.'
        classification = engine.system_failure_classification(item)
        result = engine.prevention_guidance(item, {'primaryArchitecture': None}, [], classification, engine.evidence_snapshot(item))
        self.assertNotIn('qualified reviewer', result['recommendedPreventiveControl'].lower())
        self.assertNotIn('supportingEvidence', result)

    def test_stable_identity(self):
        self.assertEqual(record()["id"], record()["id"])

    def test_duplicate_sources_merge_into_one_incident(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = incidents.FileIncidentRepository(Path(temporary) / "store.json")
            first = record("source-1")
            second = record("source-2")
            second["id"] = incidents.stable_incident_id("source-2")
            repository.upsert_sources([first, second])
            stored = repository.list()
            self.assertEqual(len(stored), 1)
            self.assertEqual(len(stored[0]["sources"]), 2)

    def test_public_projection_rejects_unknown_architecture_identity(self):
        item = record()
        item["architectureRelevance"] = {
            "status": "ARCHITECTURE_IDENTIFIED",
            "classification": "Automated",
            "primaryArchitectureId": "invented",
            "secondaryArchitectureIds": [],
        }
        result = incidents.public_records([item])[0]
        self.assertEqual(result["architectureRelevance"]["status"], "ARCHITECTURE_REVIEW_REQUIRED")
        self.assertIsNone(result["architectureRelevance"]["primaryArchitectureId"])

    def test_aiid_snapshot_keeps_provenance_and_can_be_enriched(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Incidents"
        sheet.append(["AI Incident Database export"])
        sheet.append(["INCIDENT IDENTITY"])
        sheet.append(["Incident ID", "date", "title", "description", "deployer", "Country Code", "Location Region"])
        sheet.append([1702, datetime(2026, 9, 10), "Source title", "Source description", "Source organization", "US", "North America"])
        output = io.BytesIO()
        workbook.save(output)
        adapter = incidents.AIIDWeeklyExcelAdapter(
            workbook_bytes=output.getvalue(),
            snapshot_url="https://example.test/AIID_Excel_Export-20260921.xlsx",
        )
        raw = adapter.fetch_new_records(None)
        normalized = adapter.normalize(raw[0])
        enriched = incidents.enrich_incident(normalized)
        self.assertEqual(normalized["title"], "Source title")
        self.assertEqual(normalized["summary"], "Source description")
        self.assertEqual(normalized["countryCode"], "US")
        self.assertEqual(enriched["architectureRelevance"]["status"], "ARCHITECTURE_IDENTIFIED")
        self.assertEqual(enriched["architectureRelevance"]["primaryArchitectureId"], "aig")
        self.assertEqual(normalized["sources"][0]["url"], "https://incidentdatabase.ai/cite/1702")
        self.assertEqual(normalized["sources"][0]["snapshotDate"], "2026-09-21T00:00:00Z")
        self.assertNotEqual(normalized["sources"][0]["retrievedAt"], normalized["sources"][0]["snapshotDate"])

    def test_aiid_historical_cursor_progresses_without_repeating_old_batch(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Incidents'
        sheet.append(['AI Incident Database export'])
        sheet.append(['INCIDENT IDENTITY'])
        sheet.append(['Incident ID', 'date', 'title', 'Country Code'])
        for number in range(1, 126):
            sheet.append([number, datetime(2020, 1, 1), f'Incident {number}', None])
        output = io.BytesIO()
        workbook.save(output)
        first = incidents.AIIDWeeklyExcelAdapter(workbook_bytes=output.getvalue(), snapshot_url='https://example.test/snapshot.xlsx')
        first_rows = first.fetch_new_records(None)
        self.assertEqual(first.history_cursor, 16)
        self.assertEqual(len(first_rows), 110)
        second = incidents.AIIDWeeklyExcelAdapter(workbook_bytes=output.getvalue(), snapshot_url='https://example.test/snapshot.xlsx', history_cursor=first.history_cursor)
        second_rows = second.fetch_new_records(None)
        self.assertEqual(second.history_cursor, 6)
        self.assertTrue({row['Incident ID'] for row in first_rows if row['Incident ID'] < 26}.isdisjoint(
            {row['Incident ID'] for row in second_rows if row['Incident ID'] < 26}))

    def test_country_and_architecture_are_inferred_from_incident_context(self):
        item = record(title="License plate reader misread a plate in New Mexico")
        item["summary"] = "The automated system produced an incorrect match."
        item["country"] = None
        item["countryCode"] = None
        item["system"] = "Automated License Plate Reader"
        enriched = incidents.enrich_incident(item)
        self.assertEqual(enriched["countryCode"], "US")
        self.assertEqual(enriched["country"], "United States of America")
        self.assertEqual(enriched["architectureRelevance"]["primaryArchitectureId"], "validos")
        self.assertEqual(enriched["architectureRelevance"]["architectureIndexState"], "VALIDOS®")

    def test_unresolved_country_is_explicit_without_fabricating_location(self):
        item = record(title="Generic AI system incident")
        enriched = incidents.enrich_incident(item)
        self.assertEqual(enriched["country"], "Location not specified")
        self.assertIsNone(enriched["countryCode"])

    def test_country_names_prefer_sovereign_name_and_leave_ambiguous_names_unresolved(self):
        self.assertEqual(incidents._country_names()["AU"], "Australia")
        item = record(title="An incident was reported in Georgia")
        enriched = incidents.enrich_incident(item)
        self.assertEqual(enriched["country"], "Location not specified")
        self.assertIsNone(enriched["countryCode"])

    def test_v3_analysis_is_separate_versioned_and_never_implicitly_approved(self):
        original = (ROOT / "data" / "ai-incidents" / "incident-store.json").read_bytes()
        expected = len(incidents.public_records(incidents.FileIncidentRepository().list()))
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            analysis_path = temporary / "analysis.json"
            snapshot_path = temporary / "snapshot.json"
            first = engine.build(analysis_path=analysis_path, snapshot_path=snapshot_path, created_at="2026-10-02T12:00:00Z")
            analysis_after_first = analysis_path.read_bytes()
            snapshot_after_first = snapshot_path.read_bytes()
            report_path = temporary / "v3-backfill-report.json"
            report_after_first = report_path.read_bytes()
            second = engine.build(analysis_path=analysis_path, snapshot_path=snapshot_path, created_at="2026-10-02T13:00:00Z")
            assessments = json.loads(analysis_path.read_text(encoding="utf-8"))["assessments"]
            self.assertEqual(first["assessmentsCreated"], expected)
            self.assertEqual(second["assessmentsCreated"], 0)
            self.assertEqual(analysis_path.read_bytes(), analysis_after_first)
            self.assertEqual(snapshot_path.read_bytes(), snapshot_after_first)
            self.assertEqual(report_path.read_bytes(), report_after_first)
            self.assertTrue(all(item["analysisType"] == "Automated" for item in assessments))
            self.assertTrue(all(item["humanReview"]["status"] == "Not performed" for item in assessments))
            self.assertTrue(all(item["oofApproved"] is False for item in assessments))
            self.assertTrue(all(item["assessmentConfidence"] in {"High", "Moderate", "Limited", "Evidence Insufficient"} for item in assessments))
            self.assertTrue(all(1 <= len(item["governanceQuestions"]) <= 5 for item in assessments))
        self.assertEqual((ROOT / "data" / "ai-incidents" / "incident-store.json").read_bytes(), original)

    def test_v3_consumes_dynamic_knowledge_architecture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            objects = {
                "objects": [
                    {
                        "id": "OOF-KO-ARCH-TEST", "canonicalName": "TEST™ Identity Governance Architecture",
                        "acronym": "TEST", "artifactType": "Architecture", "authorityState": "CANONICAL_AUTHORITATIVE",
                        "canonicalUrl": "https://example.test/test", "governedSpace": "Identity and Origin",
                    },
                    {
                        "id": "OOF-KO-STD-TEST-1", "canonicalName": "Identity Provenance Standard",
                        "acronym": "IPS", "artifactType": "ParentStandard", "authorityState": "CANONICAL_AUTHORITATIVE",
                        "architectureId": "OOF-KO-ARCH-TEST", "governedSpace": "Identity provenance and impersonation",
                    },
                ]
            }
            (root / "objects-core.json").write_text(json.dumps(objects), encoding="utf-8")
            (root / "relationships.json").write_text(json.dumps({"relationships": []}), encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"buildId": "TEST-KNOWLEDGE-1"}), encoding="utf-8")
            knowledge = engine.KnowledgeLayer(root)
            ranked = knowledge.rank({"title": "Deepfake impersonation incident", "summary": "Identity was fabricated."})
            self.assertEqual(ranked[0]["architectureId"], "test")

    def test_v3_methodology_depth_is_evidence_gated_and_hierarchical(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            objects = {"objects": [
                {"id": "ARCH", "canonicalName": "Identity Architecture", "acronym": "ID", "artifactType": "Architecture", "authorityState": "CANONICAL_AUTHORITATIVE", "canonicalUrl": "https://example.test/arch"},
                {"id": "STD", "canonicalName": "Identity Provenance Standard", "artifactType": "ParentStandard", "authorityState": "CANONICAL_AUTHORITATIVE", "architectureId": "ARCH", "canonicalUrl": "https://example.test/std", "governedSpace": "identity provenance impersonation"},
                {"id": "MOD", "canonicalName": "Impersonation Evidence Module", "artifactType": "CoreModule", "authorityState": "CANONICAL_AUTHORITATIVE", "architectureId": "ARCH", "parentObjectId": "STD", "canonicalUrl": "https://example.test/mod", "governedSpace": "identity provenance impersonation evidence"},
            ]}
            (root / "objects-core.json").write_text(json.dumps(objects), encoding="utf-8")
            (root / "relationships.json").write_text(json.dumps({"relationships": []}), encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({"buildId": "TEST"}), encoding="utf-8")
            knowledge = engine.KnowledgeLayer(root)
            sparse = knowledge.references("ARCH", {"title": "Identity impersonation report"})
            rich = knowledge.references("ARCH", {
                "title": "Identity impersonation evidence report", "summary": "Identity provenance evidence showed impersonation.",
                "system": "Identity system", "technology": "identity evidence classifier", "organization": "Test operator",
            })
            self.assertEqual(sparse, [])
            self.assertEqual([item["artifactType"] for item in rich], ["ParentStandard", "CoreModule"])
            self.assertEqual(rich[1]["parentObjectId"], rich[0]["objectId"])

    def test_v3_assessment_exposes_complete_methodological_reasoning_chain(self):
        item = record(title="Deepfake impersonation caused a reported fraud")
        item["summary"] = "A cloned identity and voice were used to impersonate an executive."
        item["system"] = "Voice cloning system"
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-09T00:00:00Z")
        chain = assessment["methodologicalReasoningChain"]
        self.assertEqual(chain["incidentEvidence"], ["source-1"])
        self.assertEqual(chain["primaryArchitecture"], assessment["architectureAnalysis"]["primaryArchitecture"]["objectId"])
        self.assertIn(chain["deepestJustifiedLevel"], {"Architecture", "ParentStandard", "CoreModule"})
        self.assertEqual(chain["governanceQuestions"], assessment["governanceQuestions"])

    def test_v3_assignments_are_explainable_and_source_linked(self):
        latest = engine.latest_assessments()
        expected = len(incidents.public_records(incidents.FileIncidentRepository().list()))
        self.assertEqual(len(latest), expected)
        for assessment in latest.values():
            architecture = assessment["architectureAnalysis"]
            assignments = [architecture.get("primaryArchitecture"), *architecture.get("contributingArchitectures", [])]
            for assignment in filter(None, assignments):
                self.assertTrue(assignment["reasonForRelevance"])
                self.assertTrue(assignment["supportingEvidence"])

    def test_v3_assessment_separates_evidence_findings_and_gaps(self):
        item = record(title="Deepfake impersonation caused a reported fraud")
        item["summary"] = "A public report says a cloned voice was used to impersonate an executive."
        item["country"] = "United States of America"
        item["countryCode"] = "US"
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-03T00:00:00Z")
        self.assertEqual(assessment["assessmentLabel"], "Automated Preliminary Governance Assessment")
        self.assertIn(assessment["assessmentConfidence"], {"High", "Moderate", "Limited", "Evidence Insufficient"})
        self.assertTrue(assessment["incidentEvidence"]["reportedClaims"])
        self.assertTrue(assessment["incidentEvidence"]["knownFacts"])
        self.assertTrue(assessment["evidenceGaps"])
        self.assertFalse(assessment["oofApproved"])
        self.assertIn("not an official investigation", assessment["assessmentDisclosure"])

    def test_v3_normalization_removes_placeholders_and_parses_serialized_industry(self):
        item = record(title="Automated system report")
        item["system"] = "no"
        item["industry"] = '["public administration", "law enforcement"]'
        normalized, provenance = engine.normalized_incident_view(item)
        self.assertIsNone(normalized["system"])
        self.assertEqual(normalized["industry"], "public administration; law enforcement")
        self.assertFalse(provenance["sourceRecordModified"])
        self.assertEqual(item["system"], "no")
        self.assertEqual(item["industry"], '["public administration", "law enforcement"]')

    def test_v3_placeholder_values_never_reach_questions_or_evidence_terms(self):
        item = record(title="Automated reporting incident")
        item["summary"] = "A public report described an automated outcome."
        item["system"] = "no"
        item["industry"] = '["public administration"]'
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-11T00:00:00Z")
        questions = " ".join(assessment["governanceQuestions"]).casefold()
        terms = {
            term.casefold()
            for assignment in [assessment["architectureAnalysis"].get("primaryArchitecture"), *assessment["architectureAnalysis"].get("contributingArchitectures", [])]
            if assignment for term in assignment.get("matchedTerms", [])
        }
        self.assertNotIn("how no produced", questions)
        self.assertNotIn("no", terms)

    def test_v341_semantic_noise_values_are_not_used_as_generated_subjects(self):
        item = record(title="Semantic noise regression case")
        item["summary"] = "The source report uses ordinary prose that mentions yes and whether."
        item["system"] = "yes"
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-20T00:00:00Z")
        generated = " ".join([assessment["incidentGovernanceInsight"] or "", *assessment["governanceQuestions"]]).casefold()
        self.assertNotIn("how yes", generated)
        self.assertEqual(assessment["qualityOutcomes"]["semanticIntegrity"], "PASS")
        self.assertEqual(assessment["qualityOutcomes"]["publicationEligibility"], "PUBLISHABLE")

    def test_v3_exposes_three_independent_confidence_dimensions(self):
        item = record(title="Deepfake impersonation report")
        item["summary"] = "A cloned voice reportedly impersonated an executive."
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-11T00:00:00Z")
        self.assertEqual(set(assessment["confidenceDimensions"]), {
            "sourceCorroboration", "extractionCompleteness", "methodologicalAssignment",
        })
        self.assertFalse(assessment["sourceNormalization"]["sourceRecordModified"])

    def test_v34_adds_evidence_bounded_report_and_prevention_guidance(self):
        item = record(title="Deepfake impersonation report")
        item["summary"] = "A cloned voice reportedly impersonated an executive."
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-15T00:00:00Z")
        self.assertIn(assessment["evidenceSnapshot"]["publicEvidenceStatus"], {
            "Source-Reported", "Independently Corroborated", "Officially Documented",
            "Evidence Insufficient", "Contradicted / Disputed",
        })
        self.assertIn("catalogued by", assessment["oofIncidentReport"]["report"])
        self.assertNotIn(item['summary'], assessment['oofIncidentReport']['report'])
        self.assertTrue(assessment["preventionGuidance"]["recommendedPreventiveControl"])
        self.assertEqual(len(assessment["practicalChecklist"]), 4)
        self.assertFalse(assessment["oofApproved"])

    def test_v342_source_fingerprint_ignores_rolling_snapshot_metadata(self):
        first = record("stable-source", "Snapshot stability case")
        first["sources"][0]["datasetUrl"] = "https://example.test/AIID_Excel_Export-20261012.xlsx"
        first["sources"][0]["retrievedAt"] = "2026-10-12T00:00:00Z"
        refreshed = json.loads(json.dumps(first))
        refreshed["sources"][0]["datasetUrl"] = "https://example.test/AIID_Excel_Export-20261019.xlsx"
        refreshed["sources"][0]["retrievedAt"] = "2026-10-21T00:00:00Z"
        self.assertEqual(
            incidents.source_record_fingerprint(first),
            incidents.source_record_fingerprint(refreshed),
        )

    def test_v342_prevention_and_external_mappings_are_evidence_limited(self):
        item = record(title="Deepfake impersonation report")
        item["summary"] = "A cloned voice reportedly impersonated an executive."
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-21T00:00:00Z")
        prevention = assessment["preventionGuidance"]
        self.assertIn("couldThisHappenToYourSystem", prevention)
        self.assertIn("whatShouldBeImplemented", prevention)
        self.assertIn("howCanProtectionBeVerified", prevention)
        self.assertEqual(assessment["externalTechnicalMappings"]["status"], "NOT_MAPPED")
        self.assertEqual(assessment["externalTechnicalMappings"]["mappings"], [])
        self.assertEqual(assessment["systemFailureClassification"]["technicalMechanismStatus"], "NOT_CONFIRMED")

    def test_candidate_queue_is_persistent_deduplicated_and_daily_limited(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            queue_path = temporary / "queue.json"
            repository = incidents.FileIncidentRepository(temporary / "store.json")
            candidates = [record(f"source-{index}", f"Incident {index}") for index in range(12)]
            first = incidents.queue_candidates(candidates, repository.list(), queue_path)
            second = incidents.queue_candidates(candidates, repository.list(), queue_path)
            processed = incidents.process_candidate_queue(repository, limit=10, path=queue_path)
            self.assertEqual(first["added"], 12)
            self.assertEqual(second["added"], 0)
            self.assertEqual(processed["processed"], 10)
            self.assertEqual(processed["remaining"], 2)
            self.assertEqual(len(repository.list()), 10)

    def test_candidate_queue_limits_new_and_updates_independently(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            queue_path = temporary / "queue.json"
            repository = incidents.FileIncidentRepository(temporary / "store.json")
            originals = [record(f"existing-{index}", f"Existing {index}") for index in range(3)]
            repository.upsert_sources(originals)
            changes = [dict(item, summary="Changed source evidence") for item in originals]
            new = [record(f"new-{index}", f"New {index}") for index in range(3)]
            incidents.queue_candidates(changes + new, repository.list(), queue_path)
            result = incidents.process_candidate_queue(repository, limit=2, update_limit=1, path=queue_path)
            self.assertEqual((result["processedNew"], result["processedSourceChanges"]), (2, 1))
            self.assertEqual((result["created"], result["updated"], result["remaining"]), (2, 1, 3))
            remaining = incidents.read_json(queue_path, {})["candidates"]
            self.assertEqual(sum(item["candidateKind"] == "new" for item in remaining), 1)

    def test_candidate_queue_remains_available_after_processing_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            queue_path = Path(temporary) / "queue.json"
            incidents.queue_candidates([record("retry", "Retry")], [], queue_path)
            before = incidents.read_json(queue_path, {})['candidates']
            class BrokenRepository:
                def upsert_sources(self, items):
                    raise RuntimeError("interrupted")
            with self.assertRaises(RuntimeError):
                incidents.process_candidate_queue(BrokenRepository(), path=queue_path)
            self.assertEqual(incidents.read_json(queue_path, {})['candidates'], before)
            repository = incidents.FileIncidentRepository(Path(temporary) / 'store.json')
            retried = incidents.process_candidate_queue(repository, path=queue_path)
            self.assertEqual(retried['created'], 1)
            self.assertEqual(len(incidents.read_json(queue_path, {})['newIncidentBudget']['reservedIncidentIds']), 1)

    def test_daily_new_incident_budget_survives_repeated_runs(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            queue_path = temporary / 'queue.json'
            repository = incidents.FileIncidentRepository(temporary / 'store.json')
            candidates = [record(f'budget-{index}', f'Incident {index}') for index in range(12)]
            incidents.queue_candidates(candidates, [], queue_path)
            first = incidents.process_candidate_queue(repository, path=queue_path)
            second = incidents.process_candidate_queue(repository, path=queue_path)
            self.assertEqual(first['created'], 10)
            self.assertEqual(second['created'], 0)
            self.assertEqual(second['remaining'], 2)

    def test_identifier_collision_cannot_overwrite_an_unrelated_incident(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = incidents.FileIncidentRepository(Path(temporary) / 'store.json')
            original = record('original-source', 'Original incident')
            other = record('different-source', 'Unrelated incident')
            other['id'] = original['id']
            repository.upsert_sources([original])
            with self.assertRaisesRegex(ValueError, 'identifier collision'):
                repository.upsert_sources([other])
            self.assertEqual(repository.list()[0]['title'], original['title'])

    def test_oecd_candidates_are_attributed_and_held_for_review(self):
        page = '''<h3 class="title"><a href="/en/incidents/2026-11-10-1fad">Reported case</a></h3>
        <div class="incident-summary"><p><span>Source-generated summary.</span><span>[AI generated]</span></p></div>'''
        adapter = incidents.OECDIncidentAdapter(page=page)
        raw = adapter.fetch_new_records(None)
        item = adapter.normalize(raw[0])
        self.assertEqual(item['sources'][0]['sourceId'], 'oecd:2026-11-10-1fad')
        self.assertEqual(item['sources'][0]['sourceType'], 'OECD AI-generated summary')
        self.assertIsNone(item['occurredAt'])
        self.assertTrue(item['sourceReviewRequired'])
        self.assertNotIn('[AI generated]', item['summary'])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'queue.json'
            repository = incidents.FileIncidentRepository(Path(temporary) / 'store.json')
            incidents.queue_candidates([item], [], path)
            result = incidents.process_candidate_queue(repository, path=path)
            self.assertEqual(result['created'], 0)
            self.assertEqual(result['remaining'], 1)
            self.assertEqual(result['remainingSourceReview'], 1)
            self.assertEqual(result['remainingNew'], 0)
            self.assertEqual(incidents.read_json(path, {})['candidates'][0]['candidateKind'], 'source-review')
            incidents.review_source_candidate('oecd:2026-11-10-1fad', 'accept', 'reviewer', 'Reviewed source and possible duplicates', [], path)
            incidents.queue_candidates([item], [], path)
            queued = incidents.read_json(path, {})
            self.assertEqual(len(queued['candidates']), 1)
            self.assertEqual(queued['candidates'][0]['candidateKind'], 'new')
            self.assertFalse(queued['sourceReviewHistory'][0]['oofApproval'])
            self.assertEqual(incidents.process_candidate_queue(repository, path=path)['created'], 1)
            self.assertEqual(repository.list()[0]['publicationStatus'], 'Monitored')
            self.assertEqual(repository.list()[0]['verificationState'], 'Source Catalogued / OOF Not Assessed')
            self.assertEqual(len(incidents.public_records(repository.list())), 1)
            incidents.queue_candidates([item], repository.list(), path)
            self.assertEqual(len(incidents.read_json(path, {})['candidates']), 0)

    def test_oecd_review_rejects_identifier_collision(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'queue.json'
            existing = record('existing', 'Existing incident')
            other = record('oecd:case', 'Unrelated external incident')
            other['id'] = existing['id']
            other['sourceReviewRequired'] = True
            incidents.queue_candidates([other], [existing], path)
            with self.assertRaisesRegex(ValueError, 'collides'):
                incidents.review_source_candidate('oecd:case', 'accept', 'reviewer', 'Checked', [existing], path)

    def test_changed_reviewed_source_returns_to_review_before_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'queue.json'
            item = record('oecd:case', 'External incident')
            item['sourceReviewRequired'] = True
            incidents.queue_candidates([item], [], path)
            incidents.review_source_candidate('oecd:case', 'accept', 'reviewer', 'Checked', [], path)
            updated = dict(item, summary='Materially changed source evidence')
            incidents.queue_candidates([updated], [], path)
            queued = incidents.read_json(path, {})['candidates']
            self.assertEqual(len(queued), 1)
            self.assertEqual(queued[0]['candidateKind'], 'source-review')

    def test_queue_atomic_write_preserves_prior_data_on_replace_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'queue.json'
            incidents.write_atomic_json(path, {'candidates': [{'incidentId': 'existing'}]})
            before = path.read_bytes()
            with mock.patch.object(incidents.os, 'replace', side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):
                    incidents.write_atomic_json(path, {'candidates': []})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(temporary).glob('.incident-write-*.tmp')), [])

    def test_new_incident_sources_rotate_and_cursor_survives_refresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            queue_path = temporary / "queue.json"
            repository = incidents.FileIncidentRepository(temporary / "store.json")
            candidates = []
            for source in ("alpha", "beta"):
                for index in range(3):
                    item = record(f"{source}-{index}", f"Incident {source} {index}")
                    item["sources"][0]["sourceId"] = f"{source}:{index}"
                    candidates.append(item)
            incidents.queue_candidates(candidates, [], queue_path)
            first = incidents.process_candidate_queue(repository, limit=2, path=queue_path)
            self.assertEqual(first['prioritySource'], 'alpha')
            incidents.queue_candidates(candidates, repository.list(), queue_path)
            second = incidents.process_candidate_queue(repository, limit=2, path=queue_path)
            self.assertEqual(second['prioritySource'], 'beta')
            self.assertEqual((first['created'], second['created']), (2, 2))

    def test_country_geometry_codes_cover_france_without_duplicate_primary_codes(self):
        geojson = json.loads((ROOT / "assets" / "data" / "ne_50m_admin_0_countries.geojson").read_text(encoding="utf-8"))
        resolved = []
        for feature in geojson["features"]:
            properties = feature.get("properties") or {}
            primary = properties.get("ISO_A2") or properties.get("iso_a2")
            extended = properties.get("ISO_A2_EH") or properties.get("iso_a2_eh")
            code = extended if primary == "-99" else primary
            if code and code != "-99":
                resolved.append(str(code).upper())
        self.assertIn("FR", resolved)
        store = json.loads((ROOT / "data" / "ai-incidents" / "incident-store.json").read_text(encoding="utf-8"))
        incident_codes = {item.get("countryCode") for item in store["incidents"] if item.get("countryCode")}
        self.assertFalse(incident_codes - set(resolved))

    def test_v3_architecture_roles_and_findings_are_traceable(self):
        item = record(title="Autonomous deepfake agent made an incorrect prediction")
        item["summary"] = "An autonomous agent used a cloned identity and produced an incorrect predictive decision."
        item["system"] = "Autonomous predictive agent"
        assessment = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-03T00:00:00Z")
        architecture = assessment["architectureAnalysis"]
        assigned = [architecture.get("primaryArchitecture"), *architecture.get("contributingArchitectures", [])]
        assigned = [value for value in assigned if value]
        self.assertTrue(assigned)
        self.assertEqual(assigned[0]["role"], "Primary")
        self.assertTrue(all(value["whyItMattersHere"] and value["governanceFocus"] for value in assigned))
        self.assertTrue(all(finding["evidenceBasis"] and finding["architectureReference"] for finding in assessment["governanceFindings"]))

    def test_public_export_is_complete_lightweight_and_valid(self):
        result = incidents.validate_public_export()
        summary = incidents.read_json(incidents.PUBLIC_ROOT / "summary.json", {})
        index = incidents.read_json(incidents.PUBLIC_ROOT / "incident-index.json", {})
        first_page = incidents.read_json(incidents.PUBLIC_ROOT / "incidents-page-1.json", {})
        self.assertEqual(result["incidents"], summary["totalIncidents"])
        self.assertEqual(len(index["items"]), summary["totalIncidents"])
        self.assertLessEqual(len(first_page["items"]), 25)
        self.assertNotIn("automatedAnalysis", first_page["items"][0])
        self.assertTrue(first_page["items"][0]["detailUrl"].startswith("/ai-incidents/incidents/"))
        representative = index["items"][:20]
        self.assertEqual(len(representative), 20)
        for item in representative:
            detail = incidents.read_json(incidents.PUBLIC_ROOT / "incident-details" / f"{item['slug']}.json", {})
            self.assertEqual(detail["id"], item["id"])
            self.assertTrue(item["source"]["url"].startswith("https://"))
            primary = item.get("primaryArchitecture") or {}
            if primary.get("architectureId"):
                self.assertTrue(primary.get("label"))
                self.assertTrue(primary.get("canonicalUrl"))
        dates = [item.get("occurredAt") or item.get("reportedAt") or "" for item in representative]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_search_projection_is_compact_and_keeps_card_filtering_fields(self):
        projection = incidents._list_projection(incidents.public_records([record()])[0])
        search = incidents._search_projection(projection)
        self.assertNotIn("summary", search)
        self.assertNotIn("oofReport", search)
        self.assertEqual(search["id"], projection["id"])
        self.assertEqual(search["detailUrl"], projection["detailUrl"])
        self.assertIn("assessment", search)
        self.assertIn("systemFailure", search)
        self.assertIn("preventionPreview", search)

    def test_card_previews_are_evidence_bounded(self):
        item = record(title="Deepfake impersonation report")
        item["summary"] = "A cloned voice reportedly impersonated an executive."
        item["automatedAnalysis"] = engine.build_assessment(item, engine.KnowledgeLayer(), 1, None, "test", "2026-10-29T00:00:00Z")
        projection = incidents._list_projection(item)
        self.assertEqual(projection["systemFailure"]["mechanismStatus"], "NOT_CONFIRMED")
        self.assertTrue(projection["preventionPreview"]["applicability"])
        self.assertTrue(projection["preventionPreview"]["control"])
        self.assertTrue(projection["preventionPreview"]["verification"])

    def test_source_snapshot_freshness_uses_a_bounded_slo(self):
        current = incidents._source_snapshot_freshness(
            "https://example.test/AIID_Excel_Export-20261026.xlsx", "2026-10-27T00:00:00Z"
        )
        stale = incidents._source_snapshot_freshness(
            "https://example.test/AIID_Excel_Export-20261018.xlsx", "2026-10-27T00:00:00Z"
        )
        self.assertEqual(current["status"], "CURRENT")
        self.assertEqual(stale["status"], "STALE")
        self.assertEqual(stale["sloHours"], incidents.SOURCE_FRESHNESS_SLO_HOURS)

    def test_public_projection_hydrates_legacy_architecture_identity(self):
        projection = incidents._architecture_projection({"architectureId": "aig"})
        self.assertEqual(projection["label"], "AIG® - Governance Architecture")
        self.assertEqual(
            projection["canonicalUrl"],
            "https://originopenfoundation.org/content/aig/About%20AI%20Governance%20Architecture%20(AIG%C2%AE).html",
        )

    def test_incomplete_primary_architecture_blocks_publication(self):
        outcomes = engine.quality_outcomes({
            "assessmentIdentity": "test-assessment",
            "incidentId": "OOF-AII-TEST",
            "assessmentDisclosure": "Test disclosure",
            "architectureAnalysis": {"primaryArchitecture": {"architectureId": "aig"}},
            "evidenceSnapshot": {"sources": [{"url": "https://example.test/source"}], "publicEvidenceStatus": "Source-Reported"},
        })
        self.assertEqual(outcomes["methodologicalSupport"], "REVIEW REQUIRED")
        self.assertEqual(outcomes["publicationEligibility"], "PENDING")

    def test_public_export_rejects_primary_architecture_without_public_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            original_root = incidents.PUBLIC_ROOT
            try:
                incidents.PUBLIC_ROOT = Path(temporary)
                incidents.write_json(incidents.PUBLIC_ROOT / "summary.json", {"totalIncidents": 1})
                item = {
                    "id": "OOF-AII-TEST", "slug": "missing-architecture-identity", "title": "Missing architecture identity",
                    "detailUrl": "/ai-incidents/incidents/missing-architecture-identity/",
                    "source": {"url": "https://example.test/source"},
                    "primaryArchitecture": {"architectureId": "aig"},
                }
                incidents.write_json(incidents.PUBLIC_ROOT / "incident-index.json", {"items": [item]})
                incidents.write_json(
                    incidents.PUBLIC_ROOT / "incident-details" / "missing-architecture-identity.json",
                    {"id": "OOF-AII-TEST"},
                )
                with self.assertRaisesRegex(ValueError, "primary architecture aig is missing label, canonicalUrl"):
                    incidents.validate_public_export()
            finally:
                incidents.PUBLIC_ROOT = original_root

    def test_public_export_rejects_missing_detail_projection(self):
        with tempfile.TemporaryDirectory() as temporary:
            original_root = incidents.PUBLIC_ROOT
            try:
                incidents.PUBLIC_ROOT = Path(temporary)
                incidents.write_json(incidents.PUBLIC_ROOT / "summary.json", {"totalIncidents": 1})
                incidents.write_json(incidents.PUBLIC_ROOT / "incident-index.json", {"items": [{
                    "id": "OOF-AII-TEST", "slug": "missing", "title": "Missing detail",
                    "detailUrl": "/ai-incidents/incidents/missing/", "source": {"url": "https://example.test/source"},
                }]})
                with self.assertRaisesRegex(ValueError, "missing its public detail projection"):
                    incidents.validate_public_export()
            finally:
                incidents.PUBLIC_ROOT = original_root

    def test_public_export_rejects_duplicate_identity_and_malformed_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            original_root = incidents.PUBLIC_ROOT
            try:
                incidents.PUBLIC_ROOT = Path(temporary)
                bad = {
                    "id": "OOF-AII-DUPLICATE", "slug": "duplicate", "title": "Duplicate",
                    "detailUrl": "/ai-incidents/incidents/duplicate/", "source": {"url": "not-a-url"},
                }
                incidents.write_json(incidents.PUBLIC_ROOT / "summary.json", {"totalIncidents": 2})
                incidents.write_json(incidents.PUBLIC_ROOT / "incident-index.json", {"items": [bad, bad]})
                with self.assertRaisesRegex(ValueError, "duplicate incident IDs"):
                    incidents.validate_public_export()
            finally:
                incidents.PUBLIC_ROOT = original_root


if __name__ == "__main__":
    unittest.main()

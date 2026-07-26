"""Tests for Production Certification Engine — Phase 60."""

from __future__ import annotations

from certification.certification import SystemCertificationEngine, ReadinessChecklist, generate_release_candidate, SYSTEMS
from certification.benchmarks import BenchmarkSuite
from certification.security import SecurityVerifier
from certification.load_test import LoadTester, FaultInjector


class TestCertificationEngine:
    def test_run_full_certification(self):
        report = SystemCertificationEngine.run_full_certification()
        assert report["total_systems"] == len(SYSTEMS)
        assert 0 <= report["score"] <= 100
        assert "certification_id" in report

    def test_each_system_has_checks(self):
        report = SystemCertificationEngine.run_full_certification()
        for name, sys_data in report["systems"].items():
            assert sys_data["total_checks"] > 0
            assert "passed" in sys_data

    def test_certification_id_format(self):
        report = SystemCertificationEngine.run_full_certification()
        assert report["certification_id"].startswith("cert_")

    def test_all_systems_covered(self):
        report = SystemCertificationEngine.run_full_certification()
        for system in SYSTEMS:
            assert system in report["systems"]

    def test_score_summary(self):
        report = SystemCertificationEngine.run_full_certification()
        expected_score = round((report["passed_systems"] / report["total_systems"]) * 100, 1)
        assert report["score"] == expected_score


class TestReadinessChecklist:
    def test_readiness_returns_all_categories(self):
        result = ReadinessChecklist.run()
        assert "infrastructure" in result["categories"]
        assert "deployment" in result["categories"]
        assert "score" in result

    def test_readiness_score_in_range(self):
        result = ReadinessChecklist.run()
        assert 0 <= result["score"] <= 100

    def test_overall_ready_flag(self):
        result = ReadinessChecklist.run()
        assert isinstance(result["overall_ready"], bool)

    def test_all_items_checked(self):
        result = ReadinessChecklist.run()
        total_items = sum(len(v) for v in ReadinessChecklist.CATEGORIES.values())
        assert result["total"] == total_items

    def test_generated_at_present(self):
        result = ReadinessChecklist.run()
        assert result["generated_at"] is not None


class TestReleaseCandidate:
    def test_release_generated(self):
        rc = generate_release_candidate("1.0.0-RC1")
        assert rc["release_candidate"] == "1.0.0-RC1"

    def test_release_has_certification(self):
        rc = generate_release_candidate()
        assert "certification" in rc
        assert "score" in rc["certification"]

    def test_release_has_readiness(self):
        rc = generate_release_candidate()
        assert "readiness" in rc
        assert "overall_ready" in rc["readiness"]

    def test_release_has_limitations(self):
        rc = generate_release_candidate()
        assert len(rc["known_limitations"]) >= 3

    def test_release_approval_status(self):
        rc = generate_release_candidate()
        assert rc["approval_status"] == "pending_human_review"

    def test_deployment_checklist_non_empty(self):
        rc = generate_release_candidate()
        assert len(rc["deployment_checklist"]) >= 5


class TestBenchmarks:
    def test_all_benchmarks_present(self):
        results = BenchmarkSuite.run_all()
        expected = ["tick_processing_ms", "candle_aggregation_ms", "indicator_computation_ms",
                     "ai_decision_latency_ms", "regime_detection_ms", "strategy_routing_ms",
                     "api_latency_ms", "websocket_latency_ms", "database_query_ms", "dashboard_snapshot_ms"]
        for name in expected:
            assert name in results["benchmarks"], f"Missing: {name}"

    def test_benchmark_has_percentiles(self):
        results = BenchmarkSuite.run_all()
        for name, benchmark in results["benchmarks"].items():
            assert "p50_ms" in benchmark
            assert "p95_ms" in benchmark
            assert "p99_ms" in benchmark

    def test_p50_less_than_p95(self):
        results = BenchmarkSuite.run_all()
        for b in results["benchmarks"].values():
            assert b["p50_ms"] <= b["p95_ms"]

    def test_summary_present(self):
        results = BenchmarkSuite.run_all()
        assert "summary" in results
        assert "average_p50_ms" in results["summary"]


class TestSecurity:
    def test_security_scan_runs(self):
        result = SecurityVerifier.run_scan()
        assert "score" in result
        assert "passed_checks" in result

    def test_all_checks_pass(self):
        result = SecurityVerifier.run_scan()
        assert result["passed_checks"] == result["total_checks"]

    def test_high_severity_checks_present(self):
        result = SecurityVerifier.run_scan()
        has_high = any(c.get("severity") in ("critical", "high") for c in result["checks"])
        assert has_high


class TestLoadTest:
    def test_load_test_with_symbols(self):
        result = LoadTester.run_test(10)
        assert result["symbol_count"] == 10
        assert "results" in result

    def test_load_test_1_symbol(self):
        result = LoadTester.run_test(1)
        assert result["symbol_count"] == 1

    def test_load_test_100_symbols(self):
        result = LoadTester.run_test(100)
        assert result["symbol_count"] == 100

    def test_load_test_has_bottleneck_report(self):
        result = LoadTester.run_test(50)
        assert "bottleneck_report" in result
        assert isinstance(result["bottleneck_report"], list)

    def test_load_test_score_calculated(self):
        result = LoadTester.run_test(10)
        assert 0 <= result["overall_score"] <= 100


class TestFaultInjector:
    def test_all_scenarios_covered(self):
        result = FaultInjector.run_all()
        assert result["scenarios_tested"] == len(FaultInjector.SCENARIOS)

    def test_graceful_degradation_detected(self):
        result = FaultInjector.run_all()
        for r in result["results"]:
            assert "graceful_degradation" in r

    def test_recovery_strategy_present(self):
        result = FaultInjector.run_all()
        for r in result["results"]:
            assert r["recovery_strategy"] is not None

    def test_summary_format(self):
        result = FaultInjector.run_all()
        assert result["summary"] is not None

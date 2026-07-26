"""Production Certification API routes — Phase 60 endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException

from certification.certification import SystemCertificationEngine, ReadinessChecklist, generate_release_candidate
from certification.benchmarks import BenchmarkSuite
from certification.security import SecurityVerifier
from certification.load_test import LoadTester, FaultInjector

router = APIRouter(tags=["certification"])


@router.get("/api/certification/status")
async def certification_status():
    """Get overall certification status."""
    return {"status": "certification_ready", "version": "1.0.0-RC1", "phase": "production_certification"}


@router.get("/api/certification/report")
async def certification_report():
    """Run full certification and return report."""
    report = SystemCertificationEngine.run_full_certification()
    return report


@router.get("/api/certification/benchmarks")
async def certification_benchmarks():
    """Get performance benchmark results."""
    return BenchmarkSuite.run_all()


@router.get("/api/certification/security")
async def certification_security():
    """Get security scan results."""
    return SecurityVerifier.run_scan()


@router.get("/api/certification/load")
async def certification_load(symbols: int = Query(10, ge=1, le=100)):
    """Run load test with specified symbol count."""
    return LoadTester.run_test(symbols)


@router.get("/api/certification/recovery")
async def certification_recovery():
    """Run fault injection and recovery tests."""
    return FaultInjector.run_all()


@router.get("/api/certification/readiness")
async def certification_readiness():
    """Get production readiness checklist results."""
    return ReadinessChecklist.run()


@router.get("/api/certification/release")
async def certification_release(version: str = Query("1.0.0-RC1")):
    """Generate release candidate report."""
    return generate_release_candidate(version)


@router.post("/api/certification/run")
async def certification_run():
    """Execute full certification suite."""
    return SystemCertificationEngine.run_full_certification()


@router.post("/api/certification/benchmark")
async def certification_run_benchmark():
    """Execute performance benchmarks."""
    return BenchmarkSuite.run_all()


@router.post("/api/certification/load-test")
async def certification_run_load_test(symbols: int = Query(50, ge=1, le=100)):
    """Execute load test."""
    return LoadTester.run_test(symbols)


@router.post("/api/certification/security-scan")
async def certification_security_scan():
    """Execute security scan."""
    return SecurityVerifier.run_scan()


@router.post("/api/certification/recovery-test")
async def certification_recovery_test():
    """Execute fault injection tests."""
    return FaultInjector.run_all()


@router.post("/api/certification/generate-release")
async def certification_generate_release(version: str = Query("1.0.0-RC1")):
    """Generate release candidate."""
    return generate_release_candidate(version)

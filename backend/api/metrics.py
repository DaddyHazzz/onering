from fastapi import APIRouter, Response

from backend.core.metrics import METRICS


router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics_endpoint():
    payload = METRICS.export_prometheus()
    return Response(content=payload, media_type="text/plain")

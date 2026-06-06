from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import Response
from datetime import datetime
import io
import csv

from app.models.schemas import (
    NodeID,
    RealTimeRecord,
    FDEIResult,
    ForecastResult,
    HistoricalDataPoint,
    Alert,
    SystemSettings
)
from app.repositories.dynamodb_repo import DynamoDBRepository
from app.services.auth_service import AuthService, User

router = APIRouter(prefix="/api", tags=["data"])
db_repo = DynamoDBRepository()

@router.get("/data/realtime", response_model=list[RealTimeRecord])
def get_realtime(current_user: User = Depends(AuthService.get_current_user)):
    try:
        return db_repo.fetch_latest_data()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

@router.get("/data/fdei", response_model=list[FDEIResult])
def get_fdei(current_user: User = Depends(AuthService.get_current_user)):
    try:
        return db_repo.fetch_fdei_latest()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FDEI calculation failed: {str(e)}"
        )

@router.get("/data/forecast", response_model=list[ForecastResult])
def get_forecast(current_user: User = Depends(AuthService.get_current_user)):
    try:
        return db_repo.fetch_latest_forecast()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast query failed: {str(e)}"
        )

@router.get("/data/historical", response_model=list[HistoricalDataPoint])
def get_historical(
    node_id: NodeID = Query(..., description="Node ID (Node01 or Node02)"),
    sensor_type: str = Query(..., description="Sensor parameter (ph, co2, tds, turbidity, temp, fdei)"),
    start_time: str = Query(..., description="Start time ISO8601 format"),
    end_time: str = Query(..., description="End time ISO8601 format"),
    current_user: User = Depends(AuthService.get_current_user)
):
    try:
        # Parse ISO8601 string
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use ISO8601 (e.g. 2026-05-26T15:00:00Z). Error: {str(e)}"
        )

    try:
        return db_repo.fetch_historical_range(node_id, sensor_type, start_dt, end_dt)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Historical data query failed: {str(e)}"
        )

@router.get("/data/export/csv")
def get_export_csv(
    node_id: NodeID = Query(..., description="Node ID (Node01 or Node02)"),
    sensor_type: str = Query(..., description="Sensor parameter (ph, co2, tds, turbidity, temp, fdei)"),
    start_time: str = Query(..., description="Start time ISO8601 format"),
    end_time: str = Query(..., description="End time ISO8601 format"),
    current_user: User = Depends(AuthService.get_current_user)
):
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Error: {str(e)}"
        )

    try:
        data = db_repo.fetch_historical_range(node_id, sensor_type, start_dt, end_dt)

        # Write to in-memory CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        writer.writerow(["node_id", "sensor_type", "value", "unit", "timestamp"])

        for point in data:
            writer.writerow([
                point.node_id.value,
                point.sensor_type,
                point.value,
                point.unit,
                point.timestamp.isoformat()
            ])

        csv_data = output.getvalue()
        output.close()

        filename = f"fog_monitor_{node_id.value}_{sensor_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"

        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV export failed: {str(e)}"
        )

@router.get("/data/alerts", response_model=list[Alert])
def get_alerts(current_user: User = Depends(AuthService.get_current_user)):
    try:
        return db_repo.fetch_alerts()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alerts query failed: {str(e)}"
        )

# ------------------------------------------------------------------
# System Settings
# ------------------------------------------------------------------

@router.get("/settings", response_model=SystemSettings)
def get_settings(current_user: User = Depends(AuthService.get_current_user)):
    try:
        data = db_repo.fetch_settings()
        return SystemSettings(**data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Settings query failed: {str(e)}"
        )

@router.post("/settings", response_model=SystemSettings)
def update_settings(
    body: SystemSettings,
    current_user: User = Depends(AuthService.get_current_user)
):
    try:
        data = db_repo.update_settings(
            fog_day0=body.fog_day0,
            fdei_alert_threshold=body.fdei_alert_threshold
        )
        return SystemSettings(**data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Settings update failed: {str(e)}"
        )

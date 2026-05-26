from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import Response
from datetime import datetime
import io
import csv

from app.models.schemas import (
    NodeID,
    RealTimeRecord,
    WQIResult,
    ForecastResult,
    HistoricalDataPoint,
    Alert
)
from app.repositories.dynamodb_repo import DynamoDBRepository
from app.services.auth_service import AuthService, User

router = APIRouter(prefix="/api/data", tags=["data"])
db_repo = DynamoDBRepository()

@router.get("/realtime", response_model=list[RealTimeRecord])
def get_realtime(current_user: User = Depends(AuthService.get_current_user)):
    try:
        return db_repo.fetch_latest_data()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )

@router.get("/wqi", response_model=list[WQIResult])
def get_wqi(current_user: User = Depends(AuthService.get_current_user)):
    try:
        return db_repo.fetch_latest_wqi()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"WQI calculation failed: {str(e)}"
        )

@router.get("/forecast", response_model=list[ForecastResult])
def get_forecast(current_user: User = Depends(AuthService.get_current_user)):
    try:
        return db_repo.fetch_latest_forecast()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast query failed: {str(e)}"
        )

@router.get("/historical", response_model=list[HistoricalDataPoint])
def get_historical(
    node_id: NodeID = Query(..., description="Node ID (Node01 or Node02)"),
    sensor_type: str = Query(..., description="Sensor parameter (ph, co2, tds, turbidity, temp)"),
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

@router.get("/export/csv")
def get_export_csv(
    node_id: NodeID = Query(..., description="Node ID (Node01 or Node02)"),
    sensor_type: str = Query(..., description="Sensor parameter (ph, co2, tds, turbidity, temp)"),
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
        
        filename = f"water_quality_{node_id.value}_{sensor_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        
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

@router.get("/alerts", response_model=list[Alert])
def get_alerts(current_user: User = Depends(AuthService.get_current_user)):
    try:
        return db_repo.fetch_alerts()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alerts query failed: {str(e)}"
        )

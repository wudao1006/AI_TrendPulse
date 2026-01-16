"""报警管理API"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert
from app.schemas import AlertResponse

router = APIRouter()


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    is_read: bool = Query(default=None),
    db: Session = Depends(get_db),
):
    """获取报警列表"""
    query = db.query(Alert).order_by(Alert.created_at.desc())

    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)

    alerts = query.limit(100).all()
    return [AlertResponse.model_validate(a) for a in alerts]


@router.put("/{alert_id}/read")
async def mark_alert_read(alert_id: UUID, db: Session = Depends(get_db)):
    """标记报警为已读"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="报警不存在")

    alert.is_read = True
    db.commit()

    return {"message": "已标记为已读"}


@router.put("/read-all")
async def mark_all_alerts_read(db: Session = Depends(get_db)):
    """标记所有报警为已读"""
    db.query(Alert).filter(Alert.is_read == False).update({"is_read": True})
    db.commit()

    return {"message": "已全部标记为已读"}

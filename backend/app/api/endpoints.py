import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import User, Internship, ResumeVersion, Application
from app.schemas.schemas import (
    UserProfileCreate,
    UserProfileResponse,
    InternshipResponse,
    ApplicationApprovalRequest,
)
from app.services.scheduler.tasks import scheduler_service
from app.services.applicator.engine import application_engine
from app.services.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# ==========================================
# Profile Endpoints
# ==========================================
@router.get("/profile", response_model=Optional[UserProfileResponse])
async def get_profile(db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.is_active == True).limit(1)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


@router.post("/profile", response_model=UserProfileResponse)
async def create_or_update_profile(payload: UserProfileCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if user:
        for field, value in payload.model_dump().items():
            setattr(user, field, value)
    else:
        user = User(**payload.model_dump())
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user


# ==========================================
# Internship & Scraper Endpoints
# ==========================================
@router.get("/internships", response_model=List[InternshipResponse])
async def list_internships(
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Internship).order_by(desc(Internship.match_score), desc(Internship.created_at))
    if status:
        stmt = stmt.where(Internship.status == status)
    if min_score is not None:
        stmt = stmt.where(Internship.match_score >= min_score)
    stmt = stmt.limit(limit)

    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/internships/trigger-scrape")
async def trigger_manual_scrape(background_tasks: BackgroundTasks):
    """Manually triggers an on-demand scraper run in the background."""
    background_tasks.add_task(scheduler_service.run_hourly_delta_sync)
    return {"status": "SUCCESS", "message": "Scraper task dispatched in background."}


# ==========================================
# Application & Real-Time Approval Endpoints
# ==========================================
@router.post("/applications/approve-and-apply")
async def approve_and_auto_apply(
    payload: ApplicationApprovalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Called from the real-time popup modal when user approves or edits suggestions."""
    stmt = select(ResumeVersion).where(ResumeVersion.id == payload.resume_version_id)
    res = await db.execute(stmt)
    resume_ver = res.scalar_one_or_none()

    if not resume_ver:
        raise HTTPException(status_code=404, detail="Resume version not found.")

    # Apply manual edits if provided by user in modal
    if payload.modified_bullet_diffs:
        resume_ver.bullet_diffs = [b.model_dump() for b in payload.modified_bullet_diffs]
        resume_ver.status = "MODIFIED"
    else:
        resume_ver.status = "APPROVED"

    if payload.modified_cover_letter:
        resume_ver.cover_letter_text = payload.modified_cover_letter

    if payload.modified_assessment_answers:
        resume_ver.custom_qa_answers = payload.modified_assessment_answers

    # Create Queued Application
    application = Application(
        user_id=resume_ver.user_id,
        internship_id=resume_ver.internship_id,
        resume_version_id=resume_ver.id,
        status="QUEUED",
        submitted_answers=resume_ver.custom_qa_answers or {},
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    if payload.auto_apply_now:
        # Dispatch Playwright headless applicator in background
        background_tasks.add_task(
            application_engine.apply_to_internship,
            db=db,
            application_id=str(application.id),
        )

    return {
        "status": "QUEUED",
        "application_id": str(application.id),
        "message": "Application approved and queued for auto-submission.",
    }


@router.post("/applications/skip/{internship_id}")
async def skip_internship(internship_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Internship).where(Internship.id == internship_id)
    res = await db.execute(stmt)
    internship = res.scalar_one_or_none()
    if not internship:
        raise HTTPException(status_code=404, detail="Internship not found")

    internship.status = "SKIPPED"
    await db.commit()
    return {"status": "SUCCESS", "message": f"Internship {internship.title} marked as skipped."}


# ==========================================
# WebSocket Route
# ==========================================
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Received ping from client: %s", data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

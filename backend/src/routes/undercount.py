from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.config.database import get_db
from src.models import UndercountStudy, UndercountRevision
from src.schemas.undercount import UndercountCreate, CapsUpdate, ApproveInput
from src.middlewares.auth import current_user, can_write, admin_only
from src.services import undercount
from src.services.audit import record
from src.utils.serialization import undercount_dict, revision_dict
router = APIRouter(prefix='/undercount')
@router.get('')
def listing(db=Depends(get_db), u=Depends(current_user)):
    studies = list(db.scalars(select(UndercountStudy).order_by(UndercountStudy.id.desc()).limit(100)))
    revs = {}
    if studies:
        current = {(s.id, s.revision) for s in studies}
        for r in db.scalars(select(UndercountRevision).where(UndercountRevision.study_id.in_([s.id for s in studies]))):
            if (r.study_id, r.revision) in current: revs[(r.study_id, r.revision)] = r
    return [undercount_dict(s, revs.get((s.id, s.revision))) for s in studies]
@router.post('', status_code=201)
def create(data: UndercountCreate, response: Response, db=Depends(get_db), u=Depends(can_write)):
    s, rev, fresh = undercount.create(db, data, u)
    if not fresh:
        response.status_code = 200 # 重试命中幂等键：返回已建核验单，不重复建单
        return undercount_dict(s, rev, full=True)
    record(db, u.email, 'undercount.create', {'id': s.id, 'zone': s.zone, 'dataset': s.dataset_id})
    try:
        db.commit()
    except IntegrityError: # 并发下同键落库：以先到的核验单为准
        db.rollback()
        response.status_code = 200
        s = undercount.find_by_key(db, data.idempotency_key)
        return undercount_dict(s, undercount.current_revision(db, s), full=True)
    undercount.enqueue(rev.id)
    return undercount_dict(s, rev, full=True)
@router.get('/{id}')
def detail(id: int, db=Depends(get_db), u=Depends(current_user)):
    s = undercount.get_study(db, id)
    return undercount_dict(s, undercount.current_revision(db, s), full=True)
@router.get('/{id}/revisions')
def revisions(id: int, db=Depends(get_db), u=Depends(current_user)):
    s = undercount.get_study(db, id)
    return [revision_dict(r) for r in db.scalars(select(UndercountRevision).where(UndercountRevision.study_id == s.id).order_by(UndercountRevision.revision.desc()))]
@router.put('/{id}/caps', status_code=201)
def update_caps(id: int, data: CapsUpdate, db=Depends(get_db), u=Depends(can_write)):
    s = undercount.lock_study(db, id)
    rev = undercount.update_caps(db, s, data, u)
    record(db, u.email, 'undercount.caps.update', {'id': s.id, 'revision': rev.revision})
    db.commit(); undercount.enqueue(rev.id)
    return revision_dict(rev)
@router.post('/{id}/approve')
def approve(id: int, data: ApproveInput, db=Depends(get_db), u=Depends(admin_only)):
    s = undercount.lock_study(db, id)
    rev = undercount.approve(db, s, data.revision, u)
    record(db, u.email, 'undercount.approve', {'id': s.id, 'revision': rev.revision})
    db.commit()
    return undercount_dict(s, rev, full=True)

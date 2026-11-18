import time
from fastapi import HTTPException
from redis import Redis
from sqlalchemy import select
from src.config.settings import REDIS_URL
from src.models import Dataset, UndercountStudy, UndercountRevision
from src.services.intervals import check_caps, zones_of
def find_by_key(db, key):
    return db.scalar(select(UndercountStudy).where(UndercountStudy.idempotency_key == key))
def get_study(db, id):
    s = db.get(UndercountStudy, id)
    if not s: raise HTTPException(404, '漏记核验单不存在')
    return s
def lock_study(db, id):
    s = db.scalar(select(UndercountStudy).where(UndercountStudy.id == id).with_for_update())
    if not s: raise HTTPException(404, '漏记核验单不存在')
    return s
def current_revision(db, study):
    return db.scalar(select(UndercountRevision).where(UndercountRevision.study_id == study.id, UndercountRevision.revision == study.revision))
def _validate(db, dataset_id, zone, caps, batch_cap):
    d = db.get(Dataset, dataset_id)
    if not d: raise HTTPException(404, '数据批次不存在')
    if zone != '全部' and zone not in zones_of(d.records): raise HTTPException(422, '未知展区')
    try:
        clean = check_caps(d.records, caps, batch_cap)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return d, clean
def create(db, data, user):
    existing = find_by_key(db, data.idempotency_key)
    if existing: return existing, current_revision(db, existing), False
    d, clean = _validate(db, data.dataset_id, data.zone, data.caps, data.batch_cap)
    name = data.name.strip()
    if len(name) < 2: raise HTTPException(422, '核验单名称去除空格后至少需要两个字符')
    s = UndercountStudy(name=name, dataset_id=d.id, dataset_checksum=d.checksum, zone=data.zone, idempotency_key=data.idempotency_key, revision=1, status='pending', created_by=user.id, created_at=time.time())
    db.add(s); db.flush()
    rev = UndercountRevision(study_id=s.id, revision=1, caps=clean, batch_cap=data.batch_cap, created_by=user.id, created_at=time.time())
    db.add(rev); db.flush()
    return s, rev, True
def update_caps(db, study, data, user):
    if data.base_revision != study.revision:
        raise HTTPException(409, '上限已被他人更新，请刷新后基于最新版本修改')
    d, clean = _validate(db, study.dataset_id, study.zone, data.caps, data.batch_cap)
    study.revision += 1
    study.status, study.direction, study.error = 'pending', '', ''
    rev = UndercountRevision(study_id=study.id, revision=study.revision, caps=clean, batch_cap=data.batch_cap, created_by=user.id, created_at=time.time())
    db.add(rev); db.flush()
    return rev
def approve(db, study, revision_no, user):
    rev = current_revision(db, study)
    if rev is None or revision_no != study.revision:
        raise HTTPException(409, '该结论已过期：上限已更新，请基于最新结论复核批准')
    if rev.status == 'failed':
        raise HTTPException(409, '该版本计算失败，请修正上限后重新登记')
    if rev.status != 'computed':
        raise HTTPException(409, '结论仍在待核验，待区间算出后再批准')
    if rev.direction == 'unclear':
        raise HTTPException(409, '区间含零、方向不明，不可批准')
    if not rev.approved:
        rev.approved, rev.approved_by, rev.approved_at = True, user.email, time.time()
    return rev
def enqueue(revision_id):
    try:
        r = Redis.from_url(REDIS_URL); r.rpush('undercount:queue', revision_id); r.close()
    except Exception:
        pass # SQL pending status is the durable fallback

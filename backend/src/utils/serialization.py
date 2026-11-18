import hashlib, json
def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
def dataset_dict(d):
    return {'id':d.id, 'name':d.name, 'source':d.source, 'rows':len(d.records), 'checksum':d.checksum, 'created_at':d.created_at}
def job_dict(j):
    return {k:getattr(j,k) for k in ['id','name','dataset_id','params','status','result','error','approved','created_at','finished_at']}
def report_dict(r):
    return {k:getattr(r,k) for k in ['id','name','job_id','destination','interval_seconds','next_run','enabled']}
def delivery_dict(d):
    return {k:getattr(d,k) for k in ['id','report_id','created_at','checksum','filename','destination']}
def undercount_dict(s, rev=None, full=False):
    d = {k:getattr(s,k) for k in ['id','name','dataset_id','dataset_checksum','zone','revision','status','direction','error','created_at']}
    d['approved'] = bool(rev and rev.approved)
    d['revision_status'] = rev.status if rev else ''
    d['batch_cap'] = rev.batch_cap if rev else 0
    if full and rev:
        d['caps'] = rev.caps
        d['conclusion'] = rev.conclusion
    return d
def revision_dict(r):
    return {k:getattr(r,k) for k in ['id','study_id','revision','caps','batch_cap','status','direction','conclusion','error','approved','approved_by','approved_at','created_at']}

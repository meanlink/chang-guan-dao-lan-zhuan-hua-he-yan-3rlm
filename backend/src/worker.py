import time, json, logging
from pathlib import Path
from sqlalchemy import select
from redis import Redis
from src.config.database import Session
from src.config.settings import REDIS_URL
from src.models import Job, Dataset, Report, UndercountStudy, UndercountRevision
from src.services.business import analyze
from src.services.intervals import interval_conclusion
from src.services.reports import deliver
from src.services.audit import record
logging.basicConfig(level=logging.INFO)
def execute(job_id):
    with Session() as db:
        j=db.get(Job,job_id)
        if not j or j.status!='queued':return
        j.status='running'; db.commit()
        try:
            d=db.get(Dataset,j.dataset_id)
            result=analyze(d.records,j.params)
            json.dumps(result,allow_nan=False)
            j.result=result;j.status='completed';j.finished_at=time.time()
            record(db,'worker','job.completed',{'id':j.id})
        except Exception as e:
            logging.exception('Analysis failed')
            j.status='failed';j.error=str(e)[:990];j.finished_at=time.time()
            record(db,'worker','job.failed',{'id':j.id,'error':j.error})
        db.commit()
def execute_undercount(revision_id):
    with Session() as db:
        rev=db.get(UndercountRevision,revision_id)
        if not rev or rev.status!='pending':return
        study=db.get(UndercountStudy,rev.study_id)
        try:
            d=db.get(Dataset,study.dataset_id)
            conclusion=interval_conclusion(d.records,study.zone,rev.caps,rev.batch_cap)
            json.dumps(conclusion,allow_nan=False)
            rev.conclusion=conclusion;rev.direction=conclusion['direction'];rev.status='computed'
            if study.revision==rev.revision:
                study.status='computed';study.direction=rev.direction;study.error=''
            record(db,'worker','undercount.computed',{'id':study.id,'revision':rev.revision,'direction':rev.direction})
        except Exception as e:
            logging.exception('Undercount analysis failed')
            rev.status='failed';rev.error=str(e)[:990]
            if study.revision==rev.revision:
                study.status='failed';study.error=rev.error
            record(db,'worker','undercount.failed',{'id':study.id,'revision':rev.revision,'error':rev.error})
        db.commit()
def tick():
    with Session() as db:
        queued=list(db.scalars(select(Job.id).where(Job.status=='queued').limit(3)))
    for job_id in queued:execute(job_id)
    with Session() as db:
        pending=list(db.scalars(select(UndercountRevision.id).where(UndercountRevision.status=='pending').limit(3)))
    for revision_id in pending:execute_undercount(revision_id)
    with Session() as db:
        for r in db.scalars(select(Report).where(Report.enabled==True,Report.next_run<=time.time())):
            d=deliver(db,r)
            if d:record(db,'worker','report.delivered',{'id':r.id,'delivery':d.id})
        db.commit()
def main():
    r=Redis.from_url(REDIS_URL,socket_timeout=3)
    # This Compose stack has a single worker. A crash must not strand its jobs.
    with Session() as db:
        for j in db.scalars(select(Job).where(Job.status=='running')):
            j.status='queued';record(db,'worker','job.recovered',{'id':j.id})
        db.commit()
    while True:
        Path('/tmp/heartbeat').touch()
        try:
            item=r.blpop(['analysis:queue','undercount:queue'],timeout=1)
            if item:
                if item[0]==b'undercount:queue':execute_undercount(int(item[1]))
                else:execute(int(item[1]))
            tick()
        except Exception:
            logging.exception('Worker retry');time.sleep(2)
if __name__=='__main__':main()

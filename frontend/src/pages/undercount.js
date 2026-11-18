import {datasets,undercount} from '../api/entities.js';
import {workspace} from '../stores/workspace.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {table} from '../components/common/table.js';
import {esc,fmt,date,notify} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';
import {UndercountStatus,Direction} from '../constants/enums.js';
let idemKey=(crypto.randomUUID?crypto.randomUUID():String(Date.now())+Math.random().toString(16).slice(2));
const draft={dataset_id:null,zone:'全部',caps:{}};
const stBadge=s=>'<span class="status '+esc(s)+'">'+esc(UndercountStatus[s]||s||'待核验')+'</span>';
const dirBadge=d=>d?'<span class="status dir-'+esc(d)+'">'+esc(Direction[d]||d)+'</span>':'<span class="status pending">待核验</span>';
const planCols=[{key:'record',label:'客流'},{key:'zone',label:'展区'},{key:'added',label:'补记人数'}];
function capsRows(records,caps){
 return records.map(r=>'<tr><td>'+esc(r.record)+'</td><td>'+esc(r.zone)+'</td><td>'+esc(r.arm)+'</td><td>'+esc(r.visitors)+'</td><td>'+esc(r.completed)+'</td><td><input type="number" min="0" step="1" data-cap="'+esc(r.record)+'" value="'+esc(caps[r.record]??0)+'"></td></tr>').join('');
}
function readCaps(container){
 const caps={};container.querySelectorAll('[data-cap]').forEach(i=>{const v=Number(i.value);caps[i.dataset.cap]=Number.isInteger(v)&&v>0?v:0;});return caps;
}
const positiveOnly=obj=>Object.fromEntries(Object.entries(obj).filter(([,v])=>v>0));
function endpointHtml(title,end){
 return '<div class="endpoint"><h3>'+esc(title)+'</h3><p class="hint">补记 '+end.added_total+' 人 · 此时 A 完成率 '+esc(fmt(end.rate_a))+'%、B 完成率 '+esc(fmt(end.rate_b))+'%</p>'+table(planCols,end.plan,'该端点无需补记。')+'</div>';
}
function detailHtml(sel,revisions,records){
 const c=sel.conclusion||{},computed=sel.revision_status==='computed'&&c.interval,writable=session.user.role!=='viewer';
 let body='';
 if(sel.revision_status==='failed')body='<section class="panel empty">该版本计算失败：'+esc(sel.error||'未知错误')+'。请修正上限后重新登记。</section>';
 else if(!computed)body='<section class="panel empty">待核验：后台正在按登记上限计算区间，稍后点击刷新查看。</section>';
 else{
  const approve=session.user.role==='admin'&&!sel.approved&&sel.direction!=='unclear'?'<button class="primary" id="approve-under">批准第 '+sel.revision+' 版结论</button>':'';
  body='<section class="result-lead"><p class="eyebrow">INTERVAL FINDING</p><h2>'+esc(c.summary)+'</h2><div class="metrics">'+c.metrics.map(m=>'<div><span>'+esc(m.label)+'</span><strong>'+esc(fmt(m.value))+'<small>'+esc(m.unit||'')+'</small></strong></div>').join('')+'</div></section>'
   +'<div class="two-columns"><section class="panel"><div class="section-title"><h2>下界端点 · 补记到 A</h2><span>完成率差最小</span></div>'+endpointHtml('区间下界怎么补记',c.endpoints.lower)+'</section><section class="panel"><div class="section-title"><h2>上界端点 · 补记到 B</h2><span>完成率差最大</span></div>'+endpointHtml('区间上界怎么补记',c.endpoints.upper)+'</section></div>'
   +(c.warnings||[]).map(v=>'<p class="warning">'+esc(v)+'</p>').join('')
   +'<section class="method-sheet compact"><p class="eyebrow">APPROVAL RULE</p><h3>批准口径</h3><p>'+esc(c.method)+'</p>'
   +(sel.approved?'<p class="approval">第 '+sel.revision+' 版结论已获业务批准。</p>':(sel.direction==='unclear'?'<p class="warning">区间含零、方向不明，不可批准；请收紧上限或补采数据。</p>':approve)||'')
   +'<p class="hint">上限更新会生成新版本；仅当前版本可批准，过期版本的批准请求会被拒绝，历史结论保留在下表备查。</p></section>';
 }
 const revRows=revisions.map(r=>({revision:'第 '+r.revision+' 版',status:UndercountStatus[r.status]||r.status,interval:r.conclusion&&r.conclusion.interval?'['+r.conclusion.interval.lower+', '+r.conclusion.interval.upper+']':'—',direction:Direction[r.direction]||'—',approved:r.approved?'已批准':'—',created_at:date(r.created_at)}));
 const revCols=[{key:'revision',label:'版本'},{key:'status',label:'状态'},{key:'interval',label:'区间（百分点）'},{key:'direction',label:'方向'},{key:'approved',label:'批准'},{key:'created_at',label:'登记时间'}];
 const edit=writable?'<section class="panel"><div class="section-title"><h2>更新漏记上限</h2><span>基于第 '+sel.revision+' 版 · 提交后生成新版本</span></div><form id="caps-form" data-revision="'+sel.revision+'"><label>全批漏记上限（人）<input type="number" name="batch_cap" min="0" step="1" required value="'+esc(sel.batch_cap)+'"></label><div class="caps-scroll"><table><thead><tr><th>客流</th><th>展区</th><th>方案</th><th>进区</th><th>完成</th><th>漏记上限</th></tr></thead><tbody>'+capsRows(records,sel.caps||{})+'</tbody></table></div><button type="submit" class="primary">保存上限并重新核验</button><p class="hint">客流与批次在接单时已固定（指纹 '+esc((sel.dataset_checksum||'').slice(0,18))+'…），此处仅调整上限。</p></form></section>':'';
 return '<div class="result-selector"><label>核验单<select id="select-under">'+workspace.unders.map(x=>'<option value="'+x.id+'" '+(x.id===sel.id?'selected':'')+'>'+esc(x.name)+' · '+esc(UndercountStatus[x.status]||x.status)+'</option>').join('')+'</select></label>'+stBadge(sel.status)+dirBadge(sel.direction)+'<span>第 '+sel.revision+' 版</span><span>'+date(sel.created_at)+'</span><span class="approval">'+(sel.approved?'已获业务批准':'待负责人复核')+'</span></div>'+body+edit+'<section class="panel"><div class="section-title"><h2>历史结论留查</h2><span>'+revisions.length+' 版</span></div>'+table(revCols,revRows)+'</section>';
}
export async function undercountPage(id){
 const [studies,dsets]=await Promise.all([undercount.list(),datasets.list()]);
 workspace.unders=studies;workspace.datasets=dsets;
 if(!draft.dataset_id&&dsets.length)draft.dataset_id=dsets[0].id;
 const sid=Number(id)||workspace.selectedUnder;
 let sel=studies.find(s=>s.id===sid)?await undercount.get(sid):(studies.length?await undercount.get(studies[0].id):null);
 if(sel)workspace.selectedUnder=sel.id;
 const draftDs=dsets.find(d=>d.id===Number(draft.dataset_id))||dsets[0];
 const draftRecords=draftDs?(await datasets.get(draftDs.id)).records:[];
 const zones=['全部',...new Set(draftRecords.map(r=>String(r.zone)))];
 if(!zones.includes(draft.zone))draft.zone='全部';
 const shown=draft.zone==='全部'?draftRecords:draftRecords.filter(r=>String(r.zone)===draft.zone);
 const create='<div class="section-title"><h2>登记漏记核验单</h2></div><form id="under-form"><label>核验单名称<input name="name" required minlength="2" value="漏记区间 · 复核登记"></label><label>数据批次<select name="dataset_id">'+dsets.map(d=>'<option value="'+d.id+'" '+(draftDs&&d.id===draftDs.id?'selected':'')+'>'+esc(d.name)+' · '+d.rows+' 条</option>').join('')+'</select></label><div class="parameter-grid"><label>分析展区<select name="zone">'+zones.map(z=>'<option '+(z===draft.zone?'selected':'')+'>'+esc(z)+'</option>').join('')+'</select></label><label>全批漏记上限（人）<input type="number" name="batch_cap" min="0" step="1" value="60" required></label></div><div class="fill-row"><label>统一填入<input type="number" id="fill-value" min="0" step="1" value="2"></label><button type="button" class="button small" id="fill-all">应用到全部客流</button></div><div class="caps-scroll" id="draft-caps"><table><thead><tr><th>客流</th><th>展区</th><th>方案</th><th>进区</th><th>完成</th><th>漏记上限</th></tr></thead><tbody>'+capsRows(shown,draft.caps)+'</tbody></table></div><button type="submit" class="primary" '+(session.user.role==='viewer'||!dsets.length?'disabled':'')+'>登记并计算区间 ↗</button><p class="hint">提交即固定客流批次与上限；网络重试使用同一幂等键，不会重复建单。观察员仅可查看。</p></form>';
 const list='<div class="section-title"><h2>核验单</h2><span>'+studies.length+' 单</span></div><div class="batch-list">'+studies.map(s=>'<button class="batch-item" data-under="'+s.id+'"><strong>'+esc(s.name)+'</strong><span>'+esc(UndercountStatus[s.status]||s.status)+' · 第 '+s.revision+' 版'+(s.direction?' · '+esc(Direction[s.direction]):'')+(s.approved?' · 已批准':'')+'</span><small>全批上限 '+esc(s.batch_cap)+' 人 · '+esc(s.zone)+'</small></button>').join('')+'</div>';
 let detail='<div class="empty">尚无核验单。在左侧登记每条客流与全批的漏记上限后生成。</div>';
 if(sel){
  const revs=await undercount.revisions(sel.id);
  const ds=await datasets.get(sel.dataset_id);
  const recs=sel.zone==='全部'?ds.records:ds.records.filter(r=>String(r.zone)===sel.zone);
  detail=detailHtml(sel,revs,recs);
 }
 return heading('04 / UNDERCOUNT','漏记区间核验','设备漏记完成人数时，登记每条客流与全批的漏记上限，核验两方案完成率差的上下界；区间含零即方向不明，仅同侧结论可批准。','<button class="button" id="refresh-under">刷新 ↻</button>')+'<div class="undercount-grid"><section class="panel">'+list+create+'</section><section>'+detail+'</section></div>';
}
export function bindUndercount(refresh){
 document.querySelector('#refresh-under')?.addEventListener('click',refresh);
 document.querySelector('#select-under')?.addEventListener('change',e=>{workspace.selectedUnder=Number(e.target.value);location.hash='#/undercount/'+e.target.value;});
 document.querySelectorAll('[data-under]').forEach(b=>b.onclick=()=>{workspace.selectedUnder=Number(b.dataset.under);location.hash='#/undercount/'+b.dataset.under;});
 const form=document.querySelector('#under-form');
 if(form){
  const rerender=async(collect)=>{if(collect)draft.caps={...draft.caps,...readCaps(form)};const d=await datasets.get(form.dataset_id.value);const rows=d.records.filter(r=>form.zone.value==='全部'||String(r.zone)===form.zone.value);document.querySelector('#draft-caps').innerHTML='<table><thead><tr><th>客流</th><th>展区</th><th>方案</th><th>进区</th><th>完成</th><th>漏记上限</th></tr></thead><tbody>'+capsRows(rows,draft.caps)+'</tbody></table>';};
  form.dataset_id.onchange=()=>{draft.dataset_id=Number(form.dataset_id.value);draft.caps={};rerender(false);};
  form.zone.onchange=()=>{draft.zone=form.zone.value;rerender(true);};
  document.querySelector('#fill-all')?.addEventListener('click',()=>{const v=document.querySelector('#fill-value').value;form.querySelectorAll('[data-cap]').forEach(i=>i.value=v);});
  submit(form,async f=>{draft.caps={...draft.caps,...readCaps(form)};const s=await undercount.create({name:f.get('name'),dataset_id:Number(f.get('dataset_id')),zone:f.get('zone'),batch_cap:Number(f.get('batch_cap')),caps:positiveOnly(draft.caps),idempotency_key:idemKey});idemKey=(crypto.randomUUID?crypto.randomUUID():String(Date.now())+Math.random().toString(16).slice(2));draft.caps={};workspace.selectedUnder=s.id;notify('核验单已登记，后台计算区间');location.hash='#/undercount/'+s.id;});
 }
 const capsForm=document.querySelector('#caps-form');
 if(capsForm)submit(capsForm,async f=>{const rev=await undercount.updateCaps(workspace.selectedUnder,{caps:positiveOnly(readCaps(capsForm)),batch_cap:Number(f.get('batch_cap')),base_revision:Number(capsForm.dataset.revision)});notify('上限已更新为第 '+rev.revision+' 版，后台重新核验');await refresh();});
 document.querySelector('#approve-under')?.addEventListener('click',async()=>{try{const s=await undercount.get(workspace.selectedUnder);await undercount.approve(s.id,s.revision);notify('已批准当前版本结论');await refresh();}catch(e){notify(e.message,true);}});
}

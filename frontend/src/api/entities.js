import {api} from './client.js';
export const datasets={list:()=>api('/datasets'),get:id=>api('/datasets/'+id),create:data=>api('/datasets',{method:'POST',body:JSON.stringify(data)})};
export const jobs={list:()=>api('/jobs'),get:id=>api('/jobs/'+id),create:data=>api('/jobs',{method:'POST',body:JSON.stringify(data)}),approve:id=>api('/jobs/'+id+'/approve',{method:'POST'})};
export const reports={list:()=>api('/reports'),create:data=>api('/reports',{method:'POST',body:JSON.stringify(data)}),toggle:id=>api('/reports/'+id+'/toggle',{method:'POST'}),deliveries:()=>api('/deliveries')};
export const undercount={list:()=>api('/undercount'),get:id=>api('/undercount/'+id),revisions:id=>api('/undercount/'+id+'/revisions'),create:data=>api('/undercount',{method:'POST',body:JSON.stringify(data)}),updateCaps:(id,data)=>api('/undercount/'+id+'/caps',{method:'PUT',body:JSON.stringify(data)}),approve:(id,revision)=>api('/undercount/'+id+'/approve',{method:'POST',body:JSON.stringify({revision})})};

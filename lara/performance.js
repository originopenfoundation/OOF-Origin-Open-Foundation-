'use strict';
const crypto=require('node:crypto');
const SAFE=/^(request_start|connection_ready|backend_response|knowledge_ready|authorization_ready|provider_start|provider_first_token|response_complete|render_complete)$/;
class PerformanceTrace {
  constructor({id=crypto.randomUUID(),now=()=>Date.now()}={}){this.id=id;this.now=now;this.started_at=this.now();this.marks=[];}
  mark(name){if(!SAFE.test(name))throw Error('Unsupported performance mark');const at=this.now();this.marks.push({name,elapsed_ms:Math.max(0,at-this.started_at)});return at;}
  summary(){const marks=Object.fromEntries(this.marks.map(mark=>[mark.name,mark.elapsed_ms]));return {correlation_id:this.id,total_ms:Math.max(0,this.now()-this.started_at),marks,contains_message_content:false};}
}
module.exports={PerformanceTrace};

'use strict';
const {WebsiteMonitor}=require('../lara/agents/website-monitor');
const baseUrl=process.env.LARA_MONITOR_BASE_URL||'https://originopenfoundation.org/';
const monitor=new WebsiteMonitor({baseUrl,maxPages:Math.max(1,Math.min(Number(process.env.LARA_MONITOR_MAX_PAGES)||20,100))});
monitor.inspect().then(report=>{console.log(JSON.stringify(report,null,2));process.exitCode=report.incidents.some(item=>item.severity==='high')?2:0;}).catch(error=>{console.error('Website monitor failed:',error.message);process.exitCode=1;});

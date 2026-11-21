'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { URL } = require('node:url');

const PORT = Number(process.env.PORT || 3000);
const ROOT = path.join(__dirname, 'public');
const MAX_INPUT = 2048;
const STATES = {
  email: {q0:'Start',q1:'Local atom',q2:'After local dot',q3:'After @',q4:'Domain label',q5:'Domain hyphen',q6:'Domain separator',q7:'Final/subdomain label',q8:'Domain hyphen',qA:'Accepted',qX:'Rejected'},
  url: {q0:'Start',q1:'Scheme',q2:'Authority delimiter',q3:'Hostname',q4:'Port',q5:'Path',q6:'Query',q7:'Fragment',qA:'Accepted',qX:'Rejected'}
};
const localChar = c => /^[A-Za-z0-9!#$%&'*+\-/=?^_`{|}~]$/.test(c);
const letterDigit = c => /^[A-Za-z0-9]$/.test(c);
const errorOut = (mode,input,trace,reason,index,rule) => {
  const at = Math.max(0, Math.min(index, input.length));
  trace.push({index:at, char: input[at] || '∎', from:trace.at(-1)?.to || 'q0', to:'qX', rule:rule||'Rejected'});
  return {mode,input,valid:false,status:'REJECTED',message:reason,reason,index:at,rule:rule||'Grammar violation',states:STATES[mode],trace,steps:trace.length,policy:'Educational ASCII grammar; syntax only, not deliverability, accessibility or safety.'};
};
function validateEmail(value){
  const input=String(value ?? ''); const trace=[];
  if(!input.length) return errorOut('email',input,trace,'Enter an email address.',0,'Nonempty input');
  if(input.length>254) return errorOut('email',input,trace,'Email exceeds the 254-character project limit.',254,'Maximum length');
  let state='q0', at=-1, domain='';
  for(let i=0;i<input.length;i++){
    const c=input[i]; let next='qX';
    if(state==='q0' && localChar(c)) next='q1';
    else if(state==='q1') next=localChar(c)?'q1':c==='.'?'q2':c==='@'?'q3':'qX';
    else if(state==='q2' && localChar(c)) next='q1';
    else if(state==='q3' && letterDigit(c)) next='q4';
    else if(state==='q4') next=letterDigit(c)?'q4':c==='-'?'q5':c==='.'?'q6':'qX';
    else if(state==='q5') next=letterDigit(c)?'q4':c==='-'?'q5':'qX';
    else if(state==='q6' && letterDigit(c)) next='q7';
    else if(state==='q7') next=letterDigit(c)?'q7':c==='-'?'q8':c==='.'?'q6':'qX';
    else if(state==='q8') next=letterDigit(c)?'q7':c==='-'?'q8':'qX';
    trace.push({index:i,char:c,from:state,to:next,rule:next==='qX'?'Unexpected character':STATES.email[next]});
    if(next==='qX') return { ...errorOut('email',input,trace.slice(0,-1),`Unexpected '${c}' at character ${i+1}.`,i,'Email DFA transition') };
    if(c==='@') at=i;
    state=next;
  }
  if(state!=='q7') return errorOut('email',input,trace,'Incomplete address: require a complete domain and suffix.',input.length,'Accepting state');
  domain=input.slice(at+1); const local=input.slice(0,at);
  if(local.length>64) return errorOut('email',input,trace,'Local part exceeds 64 characters.',64,'Local length');
  const labels=domain.split('.');
  if(labels.some(s=>s.length>63)) return errorOut('email',input,trace,'Domain label exceeds 63 characters.',at+1,'Domain label length');
  if(!/^[A-Za-z]{2,}$/.test(labels.at(-1))) return errorOut('email',input,trace,'Final domain label must contain at least two letters.',input.length-1,'Project suffix rule');
  trace.push({index:input.length,char:'∎',from:state,to:'qA',rule:'All grammar and length constraints satisfied'});
  return {mode:'email',input,valid:true,status:'ACCEPTED',message:'The address belongs to the defined regular language.',reason:null,index:null,rule:'EMAIL → LOCAL @ DOMAIN',parts:[{label:'Local part',value:local},{label:'Separator',value:'@'},{label:'Domain',value:domain}],states:STATES.email,trace,steps:trace.length,policy:'Syntax only — does not verify a mailbox exists.'};
}
function validateUrl(value){
  const input=String(value ?? ''); const trace=[];
  if(!input.length) return errorOut('url',input,trace,'Enter a URL.',0,'Nonempty input');
  if(input.length>MAX_INPUT) return errorOut('url',input,trace,'URL exceeds the 2048-character project limit.',MAX_INPUT,'Maximum length');
  const prefix=input.startsWith('https://')?'https://':input.startsWith('http://')?'http://':null;
  if(!prefix) return errorOut('url',input,trace,'An explicit http:// or https:// scheme is required.',0,'Scheme');
  for(let i=0;i<prefix.length;i++)trace.push({index:i,char:input[i],from:i===0?'q0':i<prefix.indexOf(':')?'q1':'q2',to:i<prefix.indexOf(':')?'q1':'q2',rule:'Scheme and :// delimiter'});
  const rest=input.slice(prefix.length); let authorityEnd=rest.search(/[/?#]/);if(authorityEnd===-1)authorityEnd=rest.length;
  const authority=rest.slice(0,authorityEnd), base=prefix.length;
  if(!authority) return errorOut('url',input,trace,'Hostname is required.',base,'Host');
  if(authority.includes('@')||authority.includes('[')||authority.includes(']'))return errorOut('url',input,trace,'Userinfo and IPv6 literals are not in this educational grammar.',base,'Host grammar');
  let hostname=authority,port='';
  if(authority.includes(':')) { const bits=authority.split(':'); if(bits.length!==2) return errorOut('url',input,trace,'Only one port separator is allowed.',base,'Port syntax'); [hostname,port]=bits; }
  for(let i=0;i<authority.length;i++) {const c=authority[i],state=c===':'?'q4':port&&i>authority.indexOf(':')?'q4':'q3';trace.push({index:base+i,char:c,from:trace.at(-1)?.to||'q2',to:state,rule:state==='q4'?'Port':'Hostname'});}
  const labelPattern=/^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/;
  const labels=hostname.split('.');
  const goodHost=hostname==='localhost'||(labels.length>=2&&labels.every(l=>l.length<=63&&labelPattern.test(l))&&/^[A-Za-z]{2,}$/.test(labels.at(-1)));
  if(!goodHost)return errorOut('url',input,trace,'Hostname does not match DOMAIN or localhost grammar.',base,'Host labels / suffix');
  if(port && (!/^\d+$/.test(port)||Number(port)<1||Number(port)>65535))return errorOut('url',input,trace,'Port must be an integer from 1 to 65535.',base+hostname.length+1,'Port range');
  if(authority.endsWith(':'))return errorOut('url',input,trace,'Port number cannot be empty.',base+hostname.length+1,'Port syntax');
  let section='q5',pathValue='',query='',fragment='';
  for(let i=base+authority.length;i<input.length;i++){
    const c=input[i];
    if(c==='#')section='q7';else if(c==='?'&&section!=='q7')section='q6';else if(c==='/'&&section==='q5')section='q5';
    else if(section==='q5' && i===base+authority.length && c!=='/')return errorOut('url',input,trace,'Path must begin with a slash.',i,'Path');
    if(/[\s\u0000-\u001F\u007F<>"{}|\\^`]/.test(c))return errorOut('url',input,trace,'URL contains an unsupported or unsafe character.',i,'Allowed URL characters');
    if(c==='%'){if(!/^[0-9a-fA-F]{2}$/.test(input.slice(i+1,i+3)))return errorOut('url',input,trace,'Percent encoding requires two hexadecimal digits.',i,'Percent encoding');}
    trace.push({index:i,char:c,from:trace.at(-1)?.to||'q3',to:section,rule:STATES.url[section]});
    if(section==='q5')pathValue+=c;else if(section==='q6')query+=c;else fragment+=c;
  }
  trace.push({index:input.length,char:'∎',from:trace.at(-1)?.to||'q3',to:'qA',rule:'All checks passed'});
  return {mode:'url',input,valid:true,status:'ACCEPTED',message:'The URL belongs to the defined regular language.',reason:null,index:null,rule:'URL → SCHEME :// HOST [PORT] [PATH] [QUERY] [FRAGMENT]',parts:[{label:'Scheme',value:prefix.slice(0,-3)},{label:'Hostname',value:hostname},{label:'Port',value:port||'Default'},{label:'Path',value:pathValue||'/'},{label:'Query',value:query.slice(1)||'—'},{label:'Fragment',value:fragment.slice(1)||'—'}],states:STATES.url,trace,steps:trace.length,policy:'Syntax only — does not request, visit or trust the destination.'};
}
const validate=(mode,input)=>mode==='url'?validateUrl(input):mode==='email'?validateEmail(input):null;
const testcaseData=[
['email','student@gmail.com',true],['email','a.b+tag@example.com',true],['email','user_name@example.co',true],['email','x@sub.domain.org',true],['email','a@localhost',false],['email','bad@@email.com',false],['email','bad..dots@example.com',false],['email','.start@example.com',false],['email','end.@example.com',false],['email','no-at-symbol.com',false],['email','user@example.c',false],['email','user@-example.com',false],['email','user@example-.com',false],['email','user@example.com.',false],['email','user name@example.com',false],['email','user@example.123',false],['email','user@example..com',false],['email','user+test@example.in',true],
['url','https://example.com',true],['url','http://localhost:3000',true],['url','https://example.com/path?q=1#section',true],['url','https://sub.example.co.in',true],['url','https://example.com/a%20b',true],['url','http://example.org:8080/docs',true],['url','www.example.com',false],['url','ftp://example.com',false],['url','https://',false],['url','https://-example.com',false],['url','https://example.com:99999',false],['url','https://example.com:abc',false],['url','https://example.com/%GG',false],['url','https://example.com/a b',false],['url','https://example..com',false],['url','https://user:pass@example.com',false],['url','https://example.com:',false],['url','https://example.com?x=1',true],['url','https://localhost',true]
];
function results(){return testcaseData.map(([mode,input,expected],i)=>{const result=validate(mode,input);return {id:i+1,mode,input,expected,actual:result.valid,passed:result.valid===expected,detail:result.message};});}
const mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.svg':'image/svg+xml','.ico':'image/x-icon','.json':'application/json; charset=utf-8'};
function serve(res,status,payload){res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(payload));}
function staticServe(req,res){const raw=new URL(req.url,'http://localhost').pathname;const relative=raw==='/'?'index.html':decodeURIComponent(raw).replace(/^\/+/, '');const target=path.resolve(ROOT,relative);if(!target.startsWith(ROOT+path.sep)&&target!==path.join(ROOT,'index.html'))return serve(res,403,{error:'Forbidden'});
fs.stat(target,(err,st)=>{if(err||!st.isFile()){res.writeHead(404);res.end('Not found');return;}res.writeHead(200,{'Content-Type':mime[path.extname(target)]||'application/octet-stream','Cache-Control':'public, max-age=300','X-Content-Type-Options':'nosniff'});fs.createReadStream(target).pipe(res);});}
const rates=new Map();
const server=http.createServer((req,res)=>{
res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','strict-origin-when-cross-origin');res.setHeader('X-Frame-Options','DENY');
res.setHeader('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'");
if(req.method==='GET'&&req.url==='/api/health')return serve(res,200,{status:'ok',name:'syntaxlab',version:'1.0.0'});
if(req.method==='GET'&&req.url==='/api/cases')return serve(res,200,{cases:results()});
if(req.url?.startsWith('/api/')&&req.method==='POST'){
const ip=req.socket.remoteAddress||'unknown',now=Date.now();let count=rates.get(ip);if(!count||now-count.start>60000){count={start:now,count:0};rates.set(ip,count);}if(++count.count>120)return serve(res,429,{error:'Rate limit exceeded'});
const expectedOrigin=`${req.headers['x-forwarded-proto']||'http'}://${req.headers.host}`;
if(req.headers.origin&&new URL(req.headers.origin).host!==req.headers.host)return serve(res,403,{error:'Cross-origin requests blocked'});
let body='';req.on('data',c=>{body+=c;if(body.length>140000){req.destroy();}});
req.on('end',()=>{let data;try{data=JSON.parse(body);}catch{return serve(res,400,{error:'Malformed JSON'});}
if(req.url==='/api/validate'){
if(typeof data.input!=='string'||data.input.length>MAX_INPUT||!['email','url'].includes(data.mode))return serve(res,400,{error:'Expected mode email|url and input string ≤2048 characters'});
return serve(res,200,validate(data.mode,data.input));
}
if(req.url==='/api/batch'){
if(!Array.isArray(data.items)||data.items.length>100)return serve(res,400,{error:'Batch must contain up to 100 inputs'});
const entries=[];for(const it of data.items){if(!it||!['email','url'].includes(it.mode)||typeof it.input!=='string'||it.input.length>MAX_INPUT)return serve(res,400,{error:'Invalid batch item'});let r=validate(it.mode,it.input);entries.push({mode:it.mode,input:it.input,valid:r.valid,message:r.message,steps:r.steps});}return serve(res,200,{total:entries.length,accepted:entries.filter(e=>e.valid).length,results:entries});
}return serve(res,404,{error:'Unknown endpoint'});
});return;
}
if(req.method==='GET'||req.method==='HEAD')return staticServe(req,res);return serve(res,405,{error:'Method not allowed'});
});
if(require.main===module)server.listen(PORT,'0.0.0.0',()=>console.log(`SyntaxLab listening on ${PORT}`));
module.exports={server,validate,validateEmail,validateUrl,results,testcaseData};
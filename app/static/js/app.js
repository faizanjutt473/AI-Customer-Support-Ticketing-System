const $=(s,r=document)=>r.querySelector(s),esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const AGENTS=["Ayesha Khan","Bilal Ahmed","Hina Malik","Usman Tariq","Sara Iqbal"];
const KB=[
{t:"How to request a refund",c:"Refund",b:"Refunds go back to the original payment method within 5–7 business days. Purchases are eligible within 30 days.",k:["refund","money back","return"]},
{t:"Fix a double charge",c:"Billing",b:"If you were charged twice, the duplicate is reversed automatically in 3 business days. Share both transaction IDs so we can confirm.",k:["twice","double","charged","payment"]},
{t:"Reset your password",c:"Technical",b:"Use 'Forgot password' on the login page. Reset links expire after 30 minutes. Locked accounts unlock after 15 minutes.",k:["password","login","locked","reset"]},
{t:"App crashes on startup",c:"Technical",b:"Update to the latest version, clear the cache and restart. If it still crashes, send the error code and device model.",k:["crash","error","bug","freeze","not working"]},
{t:"Update billing details",c:"Billing",b:"Go to Account > Billing to change your card, address or invoice email. Changes apply from the next invoice.",k:["card","billing","address","invoice"]},
{t:"Cancel a subscription",c:"Refund",b:"Cancel anytime from Account > Plan. Access continues until the end of the paid period.",k:["cancel","subscription"]}];
const seed=[
[1048,"Cannot login, account locked","Mehran Textiles","I have a client demo in an hour and my account is locked. This is unacceptable, fix it immediately!","Technical","Urgent","Angry","Open","Unassigned",1,"Today, 10:40"],
[1047,"Refund for annual plan","Noor Foods","Please refund my annual plan, I cancelled within a week of buying.","Refund","High","Neutral","In progress","Hina Malik",5,"Today, 09:55"],
[1046,"Charged twice for March invoice","Zain Traders","My card was charged twice for the March invoice. Please check the payment.","Billing","High","Negative","In progress","Ayesha Khan",3,"Today, 09:12"],
[1045,"App crashes on startup","Dr. Imran Clinic","The app crashes every time I open it after the update. Error code 502.","Technical","High","Neutral","Open","Bilal Ahmed",-1,"Yesterday"],
[1044,"Change invoice email","Pak Logistics","Please change our invoice email address to accounts@paklogistics.pk. Thank you!","Billing","Low","Positive","Closed","Sara Iqbal",20,"Yesterday"],
[1043,"Worst service, nobody replies","Rana Electronics","Terrible support. I am fed up, nobody replies to my payment issue. This is a scam.","Billing","Urgent","Angry","Open","Usman Tariq",0.5,"Yesterday"],
[1041,"Slow dashboard loading","Lahore Pharma","The dashboard is slow in the morning. Not urgent but please look into it.","Technical","Normal","Neutral","In progress","Bilal Ahmed",12,"2 days ago"],
[1040,"Cancel subscription","Hassan Studio","How do I cancel my subscription? Great product, but we are closing the studio.","Refund","Low","Positive","Closed","Hina Malik",30,"2 days ago"]
].map(a=>({id:a[0],subject:a[1],customer:a[2],msg:a[3],cat:a[4],pr:a[5],sent:a[6],status:a[7],agent:a[8],due:a[9],created:a[10],thread:[]}));
function ld(k,d){try{return JSON.parse(localStorage.getItem(k))||d}catch(e){return d}}
function sv(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
let tickets=ld("tk",seed),notes=ld("nt",[
{t:"Ticket #1048 flagged urgent: angry customer",s:"2 min ago",u:1,id:1048},{t:"SLA breach: ticket #1045 passed its deadline",s:"1 h ago",u:1,id:1045},{t:"Ticket #1047 assigned to you",s:"3 h ago",u:0,id:1047}]);
const saveT=()=>sv("tk",tickets),saveN=()=>sv("nt",notes);
/* Placeholder for the ML + RAG endpoints (replace with fetch('/api/analyze')) */
function analyze(txt){const s=txt.toLowerCase();
const kw={Billing:["invoice","billing","charged","payment","card"],Technical:["error","crash","bug","login","password","not working","slow","app"],Refund:["refund","money back","return","cancel"]};
let cat="Technical",best=0;for(const c in kw){const n=kw[c].filter(w=>s.includes(w)).length;if(n>best){best=n;cat=c}}
const an=["angry","worst","terrible","unacceptable","furious","scam","ridiculous","fed up"].filter(w=>s.includes(w)).length;
const sent=an>1?"Angry":an==1?"Negative":/thank|great|love/.test(s)?"Positive":"Neutral";
const pr=an>0||/urgent|asap|immediately|locked/.test(s)?"Urgent":best>1?"High":"Normal";
const kb=KB.map(a=>({a,n:a.k.filter(w=>s.includes(w)).length})).filter(x=>x.n).sort((x,y)=>y.n-x.n).slice(0,2).map(x=>x.a);
return{cat,pr,sent,conf:s.trim().length<8?0:Math.min(97,62+best*11),kb}}
const bd=(v,x)=>`<span class="b b-${(x||v).replace(" ","")}">${esc(v)}</span>`;
const stB=s=>bd(s,s=="In progress"?"Progress":s);
const sla=t=>t.status=="Closed"?bd("Met","OK"):t.due<0?bd("Breached","Breached"):t.due<=3?bd(t.due+"h left","Risk"):bd(Math.round(t.due)+"h left","OK");
function toast(m){const d=document.createElement("div");d.className="toast";d.textContent=m;$("#toast").append(d);setTimeout(()=>d.remove(),5000)}
const page=document.body.dataset.page;
function shell(){const m=$("#content"),un=notes.filter(n=>n.u).length;
const nav=[["dashboard","Dashboard"],["tickets","Tickets"],["new","New ticket"],["kb","Knowledge base"],["agents","Agents & SLA"],["notifications","Notifications"]];
const href={dashboard:"dashboard.html",tickets:"tickets.html",new:"ticket-new.html",kb:"knowledge-base.html",agents:"agents.html",notifications:"notifications.html"};
const w=document.createElement("div");w.className="wrap";
document.body.prepend(w);
w.innerHTML=`<header class="top"><button class="btn sec menu" aria-label="Open menu">Menu</button><div><h1>${esc(m.dataset.title)}</h1><p>${esc(m.dataset.sub||"")}</p></div><div class="sp"></div><a class="btn sec" href="ticket-new.html">+ New ticket</a></header>`;
w.append(m);
const s=document.createElement("aside");s.className="side";
s.innerHTML=`<a class="brand" href="dashboard.html"><i>S</i>SupportDesk AI</a><nav>${nav.map(n=>`<a href="${href[n[0]]}" class="${page==n[0]||(page=="detail"&&n[0]=="tickets")?"on":""}">${n[1]}${n[0]=="notifications"&&un?`<span class="cnt" id="nc">${un}</span>`:""}</a>`).join("")}</nav><div class="me"><b>Ayesha Khan</b><br>Support agent<br><a href="login.html">Sign out</a></div>`;
document.body.prepend(s);
$(".menu").onclick=()=>s.classList.toggle("open");
const t=document.createElement("div");t.id="toast";document.body.append(t);
/* Simulated real-time push; replace with Flask-SocketIO: socket.on('notification', ...) */
setTimeout(()=>{notes.unshift({t:"New urgent ticket #1049 from Faisal Mills",s:"just now",u:1,id:1048});saveN();toast("New urgent ticket #1049 from Faisal Mills");const c=$("#nc");if(c)c.textContent=notes.filter(n=>n.u).length},9000)}
const R={
dashboard(){const o=tickets.filter(t=>t.status!="Closed"),ur=o.filter(t=>t.pr=="Urgent"||t.sent=="Angry");
$("#stats").innerHTML=[["",o.length,"Open tickets"],["u",ur.length,"Urgent or angry customers"],["w",o.filter(t=>t.due<=3).length,"SLA at risk or breached"],["i","94%","SLA met this week"]].map(x=>`<div class="stat ${x[0]}"><b>${x[1]}</b><span>${x[2]}</span></div>`).join("");
const cs=["Billing","Technical","Refund"];$("#bars").innerHTML=cs.map(c=>{const n=tickets.filter(t=>t.cat==c).length;return`<div class="bar"><span>${c}</span><div class="t"><i style="width:${n/tickets.length*100}%"></i></div><b>${n}</b></div>`}).join("");
$("#risk").innerHTML=o.filter(t=>t.due<=3).sort((a,b)=>a.due-b.due).map(t=>`<div class="kv"><a href="ticket.html?id=${t.id}">#${t.id} ${esc(t.subject)}</a>${sla(t)}</div>`).join("")||"<p>No tickets at risk.</p>";
$("#urgent").innerHTML=`<thead><tr><th>ID</th><th>Subject</th><th>Customer</th><th>Priority</th><th>Sentiment</th><th>Agent</th></tr></thead><tbody>${ur.map(t=>`<tr class="row" data-id="${t.id}"><td>#${t.id}</td><td>${esc(t.subject)}</td><td>${esc(t.customer)}</td><td>${bd(t.pr)}</td><td>${bd(t.sent)}</td><td>${esc(t.agent)}</td></tr>`).join("")}</tbody>`},
tickets(){const f=()=>{const q=$("#q").value.toLowerCase(),s=$("#fs").value,c=$("#fc").value,p=$("#fp").value;
const l=tickets.filter(t=>(!q||(t.subject+t.customer+t.id).toLowerCase().includes(q))&&(!s||t.status==s)&&(!c||t.cat==c)&&(!p||t.pr==p));
$("#list").innerHTML=`<thead><tr><th>ID</th><th>Subject</th><th>Customer</th><th>Category</th><th>Priority</th><th>Sentiment</th><th>Status</th><th>SLA</th><th>Agent</th></tr></thead><tbody>${l.map(t=>`<tr class="row" data-id="${t.id}"><td>#${t.id}</td><td>${esc(t.subject)}</td><td>${esc(t.customer)}</td><td>${bd(t.cat)}</td><td>${bd(t.pr)}</td><td>${bd(t.sent)}</td><td>${stB(t.status)}</td><td>${sla(t)}</td><td>${esc(t.agent)}</td></tr>`).join("")||'<tr><td colspan="9">No tickets match these filters. Clear a filter to see more.</td></tr>'}</tbody>`;$("#cnt").textContent=l.length+" tickets"};
document.querySelectorAll(".filters input,.filters select").forEach(e=>e.oninput=f);f()},
new(){const m=()=>{const a=analyze($("#subject").value+" "+$("#message").value);$("#pc").innerHTML=a.conf?bd(a.cat):"Waiting for text…";$("#pp").innerHTML=a.conf?bd(a.pr):"–";$("#ps").innerHTML=a.conf?bd(a.sent):"–";$("#pf").textContent=a.conf?a.conf+"%":"–";return a};
$("#subject").oninput=$("#message").oninput=m;
$("#tf").onsubmit=e=>{e.preventDefault();const a=m(),id=Math.max(...tickets.map(t=>t.id))+1;
tickets.unshift({id,subject:$("#subject").value,customer:$("#cust").value,msg:$("#message").value,cat:a.cat,pr:a.pr,sent:a.sent,status:"Open",agent:"Unassigned",due:a.pr=="Urgent"?2:a.pr=="High"?8:24,created:"Just now",thread:[]});
saveT();location.href="ticket.html?id="+id}},
detail(){const id=+new URLSearchParams(location.search).get("id"),t=tickets.find(x=>x.id==id)||tickets[0];
const a=analyze(t.subject+" "+t.msg);
const draw=()=>{$("#thread").innerHTML=`<div class="msg c"><small>${esc(t.customer)} · ${t.created}</small>${esc(t.msg)}</div>`+t.thread.map(m=>`<div class="msg a"><small>${esc(m.by)} · ${m.at}</small>${esc(m.text)}</div>`).join("");
$("#tid").textContent="#"+t.id+" · "+t.subject;$("#st").innerHTML=stB(t.status);$("#sl").innerHTML=sla(t);$("#cl").style.display=t.status=="Closed"?"none":""};
draw();
$("#as").innerHTML=["Unassigned",...AGENTS].map(x=>`<option ${x==t.agent?"selected":""}>${x}</option>`).join("");
$("#as").onchange=e=>{t.agent=e.target.value;if(t.status=="Open"&&t.agent!="Unassigned")t.status="In progress";saveT();draw();toast("Assigned to "+t.agent)};
$("#cl").onclick=()=>{t.status="Closed";saveT();draw();toast("Ticket #"+t.id+" closed")};
$("#ai").innerHTML=`<div class="kv"><span>Category</span>${bd(t.cat)}</div><div class="kv"><span>Priority</span>${bd(t.pr)}</div><div class="kv"><span>Sentiment</span>${bd(t.sent)}</div><div class="kv"><span>Confidence</span><b>${a.conf||60}%</b></div>`+(t.sent=="Angry"?'<p style="margin-top:10px"><b>Flagged urgent:</b> customer sounds angry. Reply first.</p>':"");
const s=a.kb[0];$("#sg").innerHTML=s?`<div class="sug" id="sgt">${esc("Hi "+t.customer+", thanks for reaching out. "+s.b+" Let us know if you need anything else.")}</div><p style="font-size:13px;color:var(--muted)">Source: ${a.kb.map(k=>esc(k.t)).join(", ")}</p><button class="btn" id="use" type="button">Use this reply</button>`:"<p>No matching article found. Write a reply manually.</p>";
if(s)$("#use").onclick=()=>{$("#reply").value=$("#sgt").textContent;$("#reply").focus()};
$("#rf").onsubmit=e=>{e.preventDefault();const v=$("#reply").value.trim();if(!v)return;t.thread.push({by:"Ayesha Khan",text:v,at:"Just now"});if(t.status=="Open")t.status="In progress";saveT();$("#reply").value="";draw();toast("Reply sent")}},
kb(){const f=()=>{const q=$("#q").value.toLowerCase(),c=$("#fc").value;$("#kbl").innerHTML=KB.filter(a=>(!c||a.c==c)&&(!q||(a.t+a.b).toLowerCase().includes(q))).map(a=>`<article class="card">${bd(a.c)}<h2 style="margin-top:10px">${esc(a.t)}</h2><p>${esc(a.b)}</p></article>`).join("")||"<p>No articles found. Try another keyword.</p>"};
$("#q").oninput=$("#fc").oninput=f;f()},
agents(){const d=[[AGENTS[0],42,9,97,4.8],[AGENTS[1],37,12,93,4.5],[AGENTS[2],45,8,98,4.9],[AGENTS[3],28,18,84,4.1],[AGENTS[4],39,11,95,4.6]];
$("#ag").innerHTML=`<thead><tr><th>Agent</th><th>Resolved</th><th>Avg first reply</th><th>SLA met</th><th>CSAT</th></tr></thead><tbody>${d.map(r=>`<tr><td><b>${r[0]}</b></td><td>${r[1]}</td><td>${r[2]} min</td><td style="min-width:160px"><div class="bar" style="margin:0"><div class="t"><i style="width:${r[3]}%;background:${r[3]<90?"#C8321F":""}"></i></div><b>${r[3]}%</b></div></td><td>${r[4]} / 5</td></tr>`).join("")}</tbody>`;
$("#slab").innerHTML=[["Urgent","1 h","98%"],["High","4 h","95%"],["Normal","12 h","93%"],["Low","24 h","97%"]].map(x=>`<div class="kv"><span>${bd(x[0])} reply within ${x[1]}</span><b>${x[2]} met</b></div>`).join("")},
notifications(){const d=()=>{$("#nl").innerHTML=notes.map(n=>`<a class="nt ${n.u?"un":""}" href="ticket.html?id=${n.id}" style="text-decoration:none;color:inherit"><div><b>${esc(n.t)}</b><br><small style="color:var(--muted)">${n.s}</small></div></a>`).join("")};d();
$("#mr").onclick=()=>{notes.forEach(n=>n.u=0);saveN();d();const c=$("#nc");if(c)c.remove()}}};
if(page!="login"){shell();document.addEventListener("click",e=>{const r=e.target.closest("tr.row");if(r)location.href="ticket.html?id="+r.dataset.id});R[page]&&R[page]()}
else $("#lf").onsubmit=e=>{e.preventDefault();location.href="dashboard.html"};

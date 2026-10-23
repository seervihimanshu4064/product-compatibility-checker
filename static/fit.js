const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const CLS={"Compatible":"ok","Partially Compatible":"part","Incompatible":"bad"};const cls=s=>CLS[s]||"info";
const getDev=()=>{try{return JSON.parse(localStorage.getItem("myDevice"))}catch(e){return null}};
const setDev=d=>{try{d?localStorage.setItem("myDevice",JSON.stringify(d)):localStorage.removeItem("myDevice")}catch(e){}};
function chip(){const d=getDev(),c=$("#chip");c.textContent=d?`📱 Fits-check for: ${d.name} ✕`:"📱 Add your device";
 c.onclick=()=>{if(d){setDev(null);location.reload()}else{const q=prompt("Your device (e.g. iPhone 15)");if(q)fetch("/api/devices?q="+encodeURIComponent(q)).then(r=>r.json()).then(r=>{if(r[0]){setDev(r[0]);location.reload()}else alert("Device not found")})}}}
async function initListing(){chip();const d=getDev();if(!d)return;$("#hint").textContent=`Showing fit for ${d.name}.`;
 const all=await (await fetch("/api/fit_all?device="+d.id)).json();
 document.querySelectorAll(".card").forEach(c=>{const r=all[c.dataset.id],b=c.querySelector(".badge");if(!r)return;
  b.hidden=false;b.className="badge "+cls(r.status);b.textContent=r.status==="Compatible"?"✔ Fits your "+d.name:r.status==="Incompatible"?"✖ Doesn't fit your "+d.name:r.status==="Partially Compatible"?"! Partial fit ("+r.score+"%)":"? Check details"})}
function initProduct(id){chip();const inp=$("#dev"),dl=$("#dl");
 inp.oninput=async()=>{const r=await (await fetch("/api/devices?q="+encodeURIComponent(inp.value))).json();dl.innerHTML=r.map(x=>`<option value="${esc(x.name)}">`).join("")};
 inp.onkeydown=e=>{if(e.key==="Enter")run()};$("#chk").onclick=run;
 async function run(){const q=inp.value.trim();const d=await (await fetch(`/api/fit?accessory=${id}&q=${encodeURIComponent(q)}`)).json();
  if(d.device_id)setDev({id:d.device_id,name:d.device});chip();
  const w=$("#buywarn");w.innerHTML=!d.device?"":d.status==="Compatible"?`<div class="bg">✔ Fits your ${esc(d.device)}</div>`:d.status==="Incompatible"?`<div class="bw">✖ This won't work with your ${esc(d.device)}</div>`:`<div class="bw">! Check fit details before buying</div>`;
  $("#res").innerHTML=`<div class="verdict ${cls(d.status)}"><div class="pct">${d.score}%</div><div><div class="st">${esc(d.status)}${d.device?" with "+esc(d.device):""}</div></div></div>`+
  d.rules.map(r=>`<div class="rule"><b class="m ${r.result}">${r.result==="pass"?"✔ Match":r.result==="fail"?"✖ Conflict":"? Unknown"}</b><span><b>${esc(r.rule)}:</b> ${esc(r.detail)}</span></div>`).join("")+
  d.warnings.map(x=>`<div class="warn">${esc(x)}</div>`).join("")+
  (d.device&&d.status!=="Compatible"?`<h3>${d.alternatives.length?"These fit your "+esc(d.device):"No verified alternatives yet"}</h3>`+d.alternatives.map(a=>`<a class="alt" href="/product/${a.id}"><span class="em">${a.icon}</span><span>${esc(a.name)}</span><b>₹${a.price}</b></a>`).join(""):"")}
 const s=getDev();if(s){inp.value=s.name;run()}
 $("#cart").onclick=$("#now").onclick=()=>{const w=$("#buywarn .bw");if(!w||confirm("Our fit check says this may not work with your device. Continue anyway?"))alert("Demo store: added.")}}

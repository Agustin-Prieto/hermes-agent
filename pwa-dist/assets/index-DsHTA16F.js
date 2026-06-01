(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))i(s);new MutationObserver(s=>{for(const n of s)if(n.type==="childList")for(const r of n.addedNodes)r.tagName==="LINK"&&r.rel==="modulepreload"&&i(r)}).observe(document,{childList:!0,subtree:!0});function a(s){const n={};return s.integrity&&(n.integrity=s.integrity),s.referrerPolicy&&(n.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?n.credentials="include":s.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function i(s){if(s.ep)return;s.ep=!0;const n=a(s);fetch(s.href,n)}})();const E="finanzas-data";async function L(){try{const t=localStorage.getItem(E);if(t){const e=JSON.parse(t);if((Date.now()-e.ts)/1e3<300)return e.data}}catch{}return null}function N(t){try{localStorage.setItem(E,JSON.stringify({data:t,ts:Date.now()}))}catch{}}function D(){localStorage.removeItem(E)}const O="https://hermes-agent-production-802e.up.railway.app/api/sheets";async function C(t=!1){if(!t){const e=await L();if(e)return e}try{const e=await fetch(O,{cache:"no-cache"});if(!e.ok)throw new Error(`HTTP ${e.status}`);const a=await e.json();if(a.error)throw new Error(a.error);return N(a),a}catch(e){const a=await L();if(a)return a;throw e}}function o(t){return t==null||isNaN(t)?"$0":"$"+Math.round(t).toLocaleString("es-AR")}function _(t){return t==null||isNaN(t)?"0%":t+"%"}function P(t){return t>=100?"red":t>=50?"yellow":"green"}function H(t){if(!t)return null;const[e,a,i]=t.split("/").map(Number),s=new Date(i||2026,(a||1)-1,e||1);return Math.ceil((s-Date.now())/(1e3*60*60*24))}function u(t,e,a={}){return`
    <div class="card">
      ${t?`<div class="card-header">
        <div class="card-title">${t}</div>
        ${a.right||""}
      </div>`:""}
      ${e}
    </div>
  `}function b(t,e){return`
    <div class="progress-bar">
      <div class="progress-fill ${P(t)}" style="width:${Math.min(t,100)}%"></div>
    </div>
  `}function B(t){const e=P(t);return`<span class="semaforo ${e}"><span class="dot ${e}"></span> ${_(t)}</span>`}function S(t,e,a,i=""){return`
    <div class="stat-card">
      <div class="stat-icon">${t}</div>
      <div class="stat-label">${e}</div>
      <div class="stat-value ${i}">${a}</div>
    </div>
  `}function F(t,e,a,i,s){return`
    <div class="cat-row">
      <div class="cat-icon">${t}</div>
      <div class="cat-info">
        <div class="cat-name">${e}</div>
        <div class="cat-bar">${b(s)}</div>
        <div class="cat-meta">
          <span>${o(a)} / ${o(i)}</span>
          ${B(s)}
        </div>
      </div>
    </div>
  `}function R(t,e,a,i="red"){return`
    <div class="alert-banner" style="border-color:rgba(${i==="red"?"255,68,68":"255,204,0"},0.25);
      background:linear-gradient(135deg,rgba(${i==="red"?"255,68,68":"255,204,0"},0.12),rgba(${i==="red"?"255,68,68":"255,204,0"},0.05))">
      <div class="alert-title" style="color:var(--${i})">${t}</div>
      <div class="alert-body">${e}</div>
      ${a?`<div class="alert-meta">${a}</div>`:""}
    </div>
  `}function k(){return'<div class="skeleton skeleton-card"></div>'.repeat(5)}function f(t){return`
    <nav class="bottom-nav">
      ${[{id:"dashboard",icon:"🏠",label:"Home"},{id:"presupuesto",icon:"📊",label:"Gastos"},{id:"pagos-tc",icon:"💳",label:"TC"},{id:"inversiones",icon:"📈",label:"Invers."},{id:"metas",icon:"🎯",label:"Metas"}].map(a=>`
        <button class="nav-item ${t===a.id?"active":""}"
          data-nav="${a.id}" onclick="window.navigate('${a.id}')">
          <span class="nav-icon">${a.icon}</span>
          ${a.label}
        </button>
      `).join("")}
    </nav>
  `}const q="modulepreload",V=function(t,e){return new URL(t,e).href},z={},Y=function(e,a,i){let s=Promise.resolve();if(a&&a.length>0){const r=document.getElementsByTagName("link"),c=document.querySelector("meta[property=csp-nonce]"),h=(c==null?void 0:c.nonce)||(c==null?void 0:c.getAttribute("nonce"));s=Promise.allSettled(a.map(v=>{if(v=V(v,i),v in z)return;z[v]=!0;const m=v.endsWith(".css"),w=m?'[rel="stylesheet"]':"";if(!!i)for(let l=r.length-1;l>=0;l--){const g=r[l];if(g.href===v&&(!m||g.rel==="stylesheet"))return}else if(document.querySelector(`link[href="${v}"]${w}`))return;const p=document.createElement("link");if(p.rel=m?"stylesheet":q,m||(p.as="script"),p.crossOrigin="",p.href=v,h&&p.setAttribute("nonce",h),document.head.appendChild(p),m)return new Promise((l,g)=>{p.addEventListener("load",l),p.addEventListener("error",()=>g(new Error(`Unable to preload CSS for ${v}`)))})}))}function n(r){const c=new Event("vite:preloadError",{cancelable:!0});if(c.payload=r,window.dispatchEvent(c),!c.defaultPrevented)throw r}return s.then(r=>{for(const c of r||[])c.status==="rejected"&&n(c.reason);return e().catch(n)})};function J(t){var i;const e=((i=t.inversiones)==null?void 0:i[0])||{},a=t.dashboard||{};return`
    <div class="header">
      <div class="back-row" onclick="window.navigate('dashboard')">← Volver</div>
      <div class="header-title">📈 Inversiones</div>
    </div>
    <div class="main">
      ${u("🏦 FCI",`
        <div class="detail-row"><span class="detail-label">Capital actual</span><span class="detail-value" style="font-size:18px">${o(e.capital||a.capital_fci)}</span></div>
        <div class="detail-row"><span class="detail-label">Rendimiento último mes</span><span class="detail-value" style="color:var(--green)">+${o(e.rendimiento||0)} (${e.pct_rendimiento||0}%)</span></div>
      `)}

      ${u("📊 Proyección",`
        <div class="chart-container">
          <canvas id="fci-chart"></canvas>
        </div>
        <div class="detail-row"><span class="detail-label">Proyección Dic</span><span class="detail-value" style="color:var(--green)">${o(a.capital_fci*2.5)}</span></div>
      `)}

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
        ${[{icon:"🎁",label:"Aguinaldo Jun",value:"+$2,000,000"},{icon:"💵",label:"USD Jul",value:"+$1,650,000"}].map(s=>`
          <div class="stat-card">
            <div class="stat-icon">${s.icon}</div>
            <div class="stat-label">${s.label}</div>
            <div class="stat-value" style="color:var(--green);font-size:14px">${s.value}</div>
          </div>
        `).join("")}
      </div>
    </div>
    ${f("inversiones")}
  `}function G(t,e){requestAnimationFrame(()=>{const a=document.getElementById(t);a&&Y(async()=>{const{default:i}=await import("./chart-CnQqxsCx.js");return{default:i}},[],import.meta.url).then(({default:i})=>{new i(a,{type:"bar",data:{labels:["Jun","Jul","Ago","Sep","Oct","Nov","Dic"],datasets:[{label:"Proyección",data:[3,5.3,5.9,6.6,7.4,8,8.8],backgroundColor:"rgba(0,240,104,0.2)",borderColor:"#00f068",borderWidth:2,borderRadius:4}]},options:{responsive:!0,maintainAspectRatio:!1,plugins:{legend:{display:!1}},scales:{y:{ticks:{callback:s=>"$"+s.toFixed(1)+"M",color:"#888"},grid:{color:"#2a2a2a"}},x:{ticks:{color:"#888"},grid:{display:!1}}}}})}).catch(()=>{})})}function T(t){var x,p;const e=t.dashboard||{},a=t.presupuesto||[],i=e.prox_vencimiento||null,s=[S("💰","Ingresos",o(e.ingreso)),S("💳","Gastado",o(e.total_gastado)),S("🏦","FCI",o(e.capital_fci))].join("");let n="";if(i&&i.monto){const l=H(i.fecha),g=l!=null?l<=0?"🔴 VENCE HOY":`⏳ ${l} días`:"",M=((x=i.entidades)==null?void 0:x.join(" + "))||"TCs";n=R("🚨 Próximo vencimiento",`<strong>${M}</strong> — ${o(i.monto)}`,g,l!=null&&l<=3?"red":"yellow")}const r=e.tope_gasto?e.total_gastado/e.tope_gasto*100:0,c=u("🎯 Presupuesto del mes",`
    ${b(r)}
    <div style="display:flex;justify-content:space-between;font-size:13px;margin-top:4px;">
      <span>${o(e.total_gastado)} de ${o(e.tope_gasto)}</span>
      <span>${_(Math.round(r))}</span>
    </div>
  `),h=a.filter(l=>l.pct>=50).slice(0,4);let v="";h.length&&(v=u("🚦 Alertas",h.map(l=>`
      <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
        <span style="font-size:13px">${l.categoria}</span>
        <span style="color:var(--${P(l.pct)});font-size:13px">${_(l.pct)}</span>
      </div>
    `).join("")));const m=((p=t.inversiones)==null?void 0:p[0])||{},w=u("📈 FCI — Último mes",`
    <div class="detail-row"><span class="detail-label">Capital</span><span class="detail-value">${o(m.capital||e.capital_fci)}</span></div>
    <div class="detail-row"><span class="detail-label">Rendimiento</span><span class="detail-value" style="color:var(--green)">+${o(m.rendimiento||e.rendimiento_fci)}</span></div>
  `);return`
    <div class="header">
      <div class="header-title">💰 Panel Financiero</div>
      <div class="header-date">${new Date().toLocaleDateString("es-AR",{weekday:"short",day:"numeric",month:"long",year:"numeric"})}</div>
    </div>
    <div class="main" id="scroll-container">
      <div class="pull-indicator" id="pull-indicator">⬇️ Soltá para actualizar</div>
      <div class="stat-grid">${s}</div>
      ${n}
      ${c}
      ${v}
      ${w}
    </div>
    ${f("dashboard")}
  `}const U={Supermercado:"🛒",Delivery:"🍔",MercadoLibre:"🛍️",Comisiones:"🏦",Transporte:"🚇",Servicios:"🔌",Salud:"🩺",Entretenimiento:"🎮",Otros:"📦",Suscripciones:"📱",Indumentaria:"👕",Educación:"📚"};function K(t){const e=t.presupuesto||[],a=e.reduce((n,r)=>n+(r.presupuesto||0),0),i=e.reduce((n,r)=>n+(r.gastado||0),0),s=a?i/a*100:0;return`
    <div class="header">
      <div class="back-row" onclick="window.navigate('dashboard')">← Volver</div>
      <div class="header-title">📊 Presupuesto</div>
    </div>
    <div class="main">
      ${u("",`
        <div style="font-size:28px;font-weight:700">${o(a)}</div>
        ${b(s)}
        <div style="display:flex;justify-content:space-between;font-size:13px;color:var(--text-dim);margin-top:4px;">
          <span>Gastado: ${o(i)}</span>
          <span>Restan: ${o(a-i)}</span>
        </div>
      `)}

      ${u("Categorías",e.map(n=>F(U[n.categoria]||"📦",n.categoria,n.gastado,n.presupuesto,n.pct)).join(""))}
    </div>
    ${f("presupuesto")}
  `}function W(t){const e=t.tcs||[],a=e.reduce((s,n)=>s+(n.exigible||0),0),i=new Date;return i.getMonth(),i.getFullYear(),`
    <div class="header">
      <div class="back-row" onclick="window.navigate('dashboard')">← Volver</div>
      <div class="header-title">💳 Pagos TC</div>
    </div>
    <div class="main">
      ${u("Resumen",`
        <div style="font-size:28px;font-weight:700">${o(a)}</div>
        <div style="font-size:12px;color:var(--text-dim);margin-top:4px">Total exigible del período</div>
      `)}

      ${e.length?u("Próximos vencimientos",e.map(s=>{let n="";(s.cierre||s.vencimiento)&&(n=`<div style="font-size:11px;color:var(--text-dim);margin-top:2px">${`c${s.cierre} · v${s.vencimiento}`}${s.banco==="MercadoLibre"?" (débito)":""}</div>`);let r="";return s.exigible>1e5&&(r='<div style="font-size:12px;color:var(--red);margin-top:4px">⚠️ Monto elevado</div>'),`
          <div class="detail-row">
            <div>
              <div style="font-weight:600">🏦 ${s.banco}</div>
              ${n}
              ${r}
            </div>
            <div style="text-align:right">
              <div style="font-weight:700">${o(s.exigible)}</div>
            </div>
          </div>
        `}).join("")):'<div class="empty-state">No hay resúmenes disponibles</div>'}

      <div style="margin-top:12px">
        ${u("📅 Fechas de referencia",Object.entries(t.bancos_fechas||{}).map(([s,n])=>`<div class="detail-row"><span class="detail-label">${s}</span><span class="detail-value">c${n.cierre} · v${n.vencimiento}</span></div>`).join("")||'<div class="empty-state">Sin datos de fechas</div>')}
      </div>

      <div style="margin-top:12px">
        ${R("💡 Tip","Pagá con Lemon 🍋 para 2% cashback en todas las compras","")}
      </div>
    </div>
    ${f("pagos-tc")}
  `}function Q(t){const e=t.metas||[],a=e.reduce((i,s)=>i+(s.ahorrado||0),0);return`
    <div class="header">
      <div class="back-row" onclick="window.navigate('dashboard')">← Volver</div>
      <div class="header-title">🎯 Metas</div>
    </div>
    <div class="main">
      ${e.length?e.map(i=>`
        <div class="goal-card">
          <div class="goal-name">${i.nombre}</div>
          <div class="goal-meta">${i.estado||"En progreso"}</div>
          ${b(i.progreso)}
          <div class="goal-numbers">
            <span>${o(i.ahorrado)} / ${o(i.objetivo)}</span>
            <span>${i.progreso}%</span>
          </div>
        </div>
      `).join(""):'<div class="empty-state">No hay metas configuradas</div>'}

      <div class="divider"></div>
      ${X("",`
        <div style="text-align:center">
          <div style="font-size:12px;color:var(--text-dim);margin-bottom:4px">Total ahorrado</div>
          <div style="font-size:28px;font-weight:700;color:var(--green)">${o(a)}</div>
        </div>
      `)}
    </div>
    ${f("metas")}
  `}function X(t,e){return`
    <div class="card">
      
      ${e}
    </div>
  `}function Z(t){const e=t.salud||[],a=e.reduce((i,s)=>i+(s.costo_est||0),0);return`
    <div class="header">
      <div class="back-row" onclick="window.navigate('metas')">← Volver</div>
      <div class="header-title">🩺 Salud</div>
    </div>
    <div class="main">
      ${u("Resumen",`
        <div style="font-size:28px;font-weight:700">${o(a)}</div>
        <div style="font-size:12px;color:var(--text-dim);margin-top:4px">Costo estimado total pendiente</div>
      `)}

      ${e.length?e.map(i=>(i.estado==="Completado"||i.estado,`
          <div class="card" style="padding:14px">
            <div style="display:flex;justify-content:space-between;align-items:start">
              <div>
                <div style="font-weight:600;margin-bottom:4px">${i.profesional}</div>
                ${i.motivo?`<div style="font-size:12px;color:var(--text-dim);margin-bottom:4px">${i.motivo}</div>`:""}
                ${i.costo_est?`<div style="font-size:13px;color:var(--text)">💰 ${o(i.costo_est)}</div>`:""}
              </div>
              <span style="font-size:13px">${i.estado||"—"}</span>
            </div>
          </div>
        `)).join(""):'<div class="empty-state">No hay registros de salud</div>'}
    </div>
    ${f("metas")}
  `}function ee(t){const e=t.suscripciones||[],a=e.filter(s=>s.activo!==!1).reduce((s,n)=>s+(n.monto_mes||0),0),i=e.filter(s=>s.activo!==!1).reduce((s,n)=>s+(n.monto_anio||n.monto_mes*12||0),0);return`
    <div class="header">
      <div class="back-row" onclick="window.navigate('presupuesto')">← Volver</div>
      <div class="header-title">📱 Suscripciones</div>
    </div>
    <div class="main">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
        <div class="stat-card">
          <div class="stat-label">Total/mes</div>
          <div class="stat-value" style="font-size:18px">${o(a)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Total/año</div>
          <div class="stat-value" style="font-size:18px;color:var(--red)">${o(i)}</div>
        </div>
      </div>

      ${e.length?u("Servicios",e.map(s=>`
        <div class="sub-row">
          <div>
            <div class="sub-name">${s.servicio}</div>
            <div class="sub-meta">${s.activo!==!1?"✅ Activo":"❌ Inactivo"}</div>
          </div>
          <div style="text-align:right">
            <div class="sub-amount">${o(s.monto_mes)}/mes</div>
            ${s.monto_anio?`<div class="sub-meta">${o(s.monto_anio)}/año</div>`:""}
          </div>
        </div>
      `).join("")):'<div class="empty-state">No hay suscripciones registradas</div>'}
    </div>
    ${f("presupuesto")}
  `}let d={data:null,currentScreen:"dashboard",loading:!1};async function j(t=!1){if(d.loading)return;d.loading=!0;const e=document.getElementById("app");te(e);try{d.data=await C(t),$(d.currentScreen),I("✅ Datos actualizados")}catch(a){d.data?($(d.currentScreen),I("📡 Mostrando datos en caché")):e.innerHTML=`
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;padding:32px;text-align:center">
          <div style="font-size:48px;margin-bottom:16px">😵</div>
          <div style="font-size:16px;font-weight:600;margin-bottom:8px">Error al cargar datos</div>
          <div style="font-size:13px;color:var(--text-dim);margin-bottom:16px">${a.message||"Sin conexión"}</div>
          <button onclick="window.forceRefresh()" style="background:var(--green);color:#0d0d0d;border:none;border-radius:8px;padding:10px 24px;font-size:14px;font-weight:600;cursor:pointer">Reintentar</button>
        </div>
      `}d.loading=!1}function te(t){const e=t.querySelector(".bottom-nav");t.innerHTML=`
    <div class="header">
      <div class="header-title">💰 Panel Financiero</div>
      <div class="header-date">Cargando...</div>
    </div>
    <div class="main">
      ${k()}
      ${k()}
    </div>
    ${e?e.outerHTML:""}
  `}function $(t){d.currentScreen=t;const e=document.getElementById("app");if(!d.data)return;let a="";switch(t){case"dashboard":a=T(d.data);break;case"presupuesto":a=K(d.data);break;case"pagos-tc":a=W(d.data);break;case"inversiones":a=J(d.data);break;case"metas":a=Q(d.data);break;case"salud":a=Z(d.data);break;case"suscripciones":a=ee(d.data);break;default:a=T(d.data)}e.innerHTML=a,t==="inversiones"&&G("fci-chart");const i=e.querySelector(".main");i&&(i.scrollTop=0)}function I(t){let e=document.getElementById("toast");e||(e=document.createElement("div"),e.id="toast",document.body.appendChild(e)),e.textContent=t,e.classList.add("show"),clearTimeout(e._timeout),e._timeout=setTimeout(()=>e.classList.remove("show"),2500)}let A=0,y=!1;document.addEventListener("touchstart",t=>{const e=document.querySelector(".main");!e||e.scrollTop>0||(A=t.touches[0].clientY,y=!0)},{passive:!0});document.addEventListener("touchmove",t=>{if(!y)return;const e=document.querySelector(".main");if(!e||e.scrollTop>0)return;const a=t.touches[0].clientY-A,i=document.getElementById("pull-indicator");i&&(a>60?(i.textContent="⬆️ Soltá para actualizar",i.classList.add("show")):a>20?(i.textContent="⬇️ Tirá para actualizar",i.classList.add("show")):i.classList.remove("show"))},{passive:!0});document.addEventListener("touchend",()=>{if(!y)return;y=!1;const t=document.getElementById("pull-indicator");t!=null&&t.classList.contains("show")&&(t.textContent="🔄 Actualizando...",j(!0).then(()=>{t&&t.classList.remove("show")}))},{passive:!0});window.navigate=t=>{$(t)};window.forceRefresh=()=>{D(),j(!0)};(async function(){const e=document.getElementById("app");e.innerHTML=`
    <div class="header">
      <div class="header-title">💰 Panel Financiero</div>
      <div class="header-date">Cargando...</div>
    </div>
    <div class="main">
      ${k()}
    </div>
  `,d.data=await C(),$("dashboard"),setInterval(()=>C().then(a=>{d.data=a,$(d.currentScreen)}),3e5)})();

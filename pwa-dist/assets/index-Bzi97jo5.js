(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))s(i);new MutationObserver(i=>{for(const n of i)if(n.type==="childList")for(const d of n.addedNodes)d.tagName==="LINK"&&d.rel==="modulepreload"&&s(d)}).observe(document,{childList:!0,subtree:!0});function a(i){const n={};return i.integrity&&(n.integrity=i.integrity),i.referrerPolicy&&(n.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?n.credentials="include":i.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function s(i){if(i.ep)return;i.ep=!0;const n=a(i);fetch(i.href,n)}})();const E="finanzas-data";async function L(){try{const t=localStorage.getItem(E);if(t){const e=JSON.parse(t);if((Date.now()-e.ts)/1e3<300)return e.data}}catch{}return null}function H(t){try{localStorage.setItem(E,JSON.stringify({data:t,ts:Date.now()}))}catch{}}function M(){localStorage.removeItem(E)}const O="/api/sheets";async function C(t=!1){if(!t){const e=await L();if(e)return e}try{const e=await fetch(O,{cache:"no-cache"});if(!e.ok)throw new Error(`HTTP ${e.status}`);const a=await e.json();if(a.error)throw new Error(a.error);return H(a),a}catch(e){const a=await L();if(a)return a;throw e}}function r(t){return t==null||isNaN(t)?"$0":"$"+Math.round(t).toLocaleString("es-AR")}function _(t){return t==null||isNaN(t)?"0%":t+"%"}function P(t){return t>=100?"red":t>=50?"yellow":"green"}function D(t){if(!t)return null;const[e,a,s]=t.split("/").map(Number),i=new Date(s||2026,(a||1)-1,e||1);return Math.ceil((i-Date.now())/(1e3*60*60*24))}function p(t,e,a={}){return`
    <div class="card">
      ${t?`<div class="card-header">
        <div class="card-title">${t}</div>
        ${a.right||""}
      </div>`:""}
      ${e}
    </div>
  `}function x(t,e){return`
    <div class="progress-bar">
      <div class="progress-fill ${P(t)}" style="width:${Math.min(t,100)}%"></div>
    </div>
  `}function B(t){const e=P(t);return`<span class="semaforo ${e}"><span class="dot ${e}"></span> ${_(t)}</span>`}function S(t,e,a,s=""){return`
    <div class="stat-card">
      <div class="stat-icon">${t}</div>
      <div class="stat-label">${e}</div>
      <div class="stat-value ${s}">${a}</div>
    </div>
  `}function F(t,e,a,s,i){return`
    <div class="cat-row">
      <div class="cat-icon">${t}</div>
      <div class="cat-info">
        <div class="cat-name">${e}</div>
        <div class="cat-bar">${x(i)}</div>
        <div class="cat-meta">
          <span>${r(a)} / ${r(s)}</span>
          ${B(i)}
        </div>
      </div>
    </div>
  `}function R(t,e,a,s="red"){return`
    <div class="alert-banner" style="border-color:rgba(${s==="red"?"255,68,68":"255,204,0"},0.25);
      background:linear-gradient(135deg,rgba(${s==="red"?"255,68,68":"255,204,0"},0.12),rgba(${s==="red"?"255,68,68":"255,204,0"},0.05))">
      <div class="alert-title" style="color:var(--${s})">${t}</div>
      <div class="alert-body">${e}</div>
      ${a?`<div class="alert-meta">${a}</div>`:""}
    </div>
  `}function k(){return'<div class="skeleton skeleton-card"></div>'.repeat(5)}function g(t){return`
    <nav class="bottom-nav">
      ${[{id:"dashboard",icon:"🏠",label:"Home"},{id:"presupuesto",icon:"📊",label:"Gastos"},{id:"pagos-tc",icon:"💳",label:"TC"},{id:"inversiones",icon:"📈",label:"Invers."},{id:"metas",icon:"🎯",label:"Metas"}].map(a=>`
        <button class="nav-item ${t===a.id?"active":""}"
          data-nav="${a.id}" onclick="window.navigate('${a.id}')">
          <span class="nav-icon">${a.icon}</span>
          ${a.label}
        </button>
      `).join("")}
    </nav>
  `}const q="modulepreload",V=function(t,e){return new URL(t,e).href},z={},J=function(e,a,s){let i=Promise.resolve();if(a&&a.length>0){const d=document.getElementsByTagName("link"),o=document.querySelector("meta[property=csp-nonce]"),l=(o==null?void 0:o.nonce)||(o==null?void 0:o.getAttribute("nonce"));i=Promise.allSettled(a.map(u=>{if(u=V(u,s),u in z)return;z[u]=!0;const f=u.endsWith(".css"),$=f?'[rel="stylesheet"]':"";if(!!s)for(let v=d.length-1;v>=0;v--){const h=d[v];if(h.href===u&&(!f||h.rel==="stylesheet"))return}else if(document.querySelector(`link[href="${u}"]${$}`))return;const m=document.createElement("link");if(m.rel=f?"stylesheet":q,f||(m.as="script"),m.crossOrigin="",m.href=u,l&&m.setAttribute("nonce",l),document.head.appendChild(m),f)return new Promise((v,h)=>{m.addEventListener("load",v),m.addEventListener("error",()=>h(new Error(`Unable to preload CSS for ${u}`)))})}))}function n(d){const o=new Event("vite:preloadError",{cancelable:!0});if(o.payload=d,window.dispatchEvent(o),!o.defaultPrevented)throw d}return i.then(d=>{for(const o of d||[])o.status==="rejected"&&n(o.reason);return e().catch(n)})};function Y(t){var s;const e=((s=t.inversiones)==null?void 0:s[0])||{},a=t.dashboard||{};return`
    <div class="header">
      <div class="back-row" onclick="window.navigate('dashboard')">← Volver</div>
      <div class="header-title">📈 Inversiones</div>
    </div>
    <div class="main">
      ${p("🏦 FCI",`
        <div class="detail-row"><span class="detail-label">Capital actual</span><span class="detail-value" style="font-size:18px">${r(e.capital||a.capital_fci)}</span></div>
        <div class="detail-row"><span class="detail-label">Rendimiento último mes</span><span class="detail-value" style="color:var(--green)">+${r(e.rendimiento||0)} (${e.pct_rendimiento||0}%)</span></div>
      `)}

      ${p("📊 Proyección",`
        <div class="chart-container">
          <canvas id="fci-chart"></canvas>
        </div>
        <div class="detail-row"><span class="detail-label">Proyección Dic</span><span class="detail-value" style="color:var(--green)">${r(a.capital_fci*2.5)}</span></div>
      `)}

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
        ${[{icon:"🎁",label:"Aguinaldo Jun",value:"+$2,000,000"},{icon:"💵",label:"USD Jul",value:"+$1,650,000"}].map(i=>`
          <div class="stat-card">
            <div class="stat-icon">${i.icon}</div>
            <div class="stat-label">${i.label}</div>
            <div class="stat-value" style="color:var(--green);font-size:14px">${i.value}</div>
          </div>
        `).join("")}
      </div>
    </div>
    ${g("inversiones")}
  `}function G(t,e){requestAnimationFrame(()=>{const a=document.getElementById(t);a&&J(async()=>{const{default:s}=await import("./chart-CnQqxsCx.js");return{default:s}},[],import.meta.url).then(({default:s})=>{new s(a,{type:"bar",data:{labels:["Jun","Jul","Ago","Sep","Oct","Nov","Dic"],datasets:[{label:"Proyección",data:[3,5.3,5.9,6.6,7.4,8,8.8],backgroundColor:"rgba(0,240,104,0.2)",borderColor:"#00f068",borderWidth:2,borderRadius:4}]},options:{responsive:!0,maintainAspectRatio:!1,plugins:{legend:{display:!1}},scales:{y:{ticks:{callback:i=>"$"+i.toFixed(1)+"M",color:"#888"},grid:{color:"#2a2a2a"}},x:{ticks:{color:"#888"},grid:{display:!1}}}}})}).catch(()=>{})})}function T(t){var y,m;const e=t.dashboard||{},a=t.presupuesto||[],s=e.prox_vencimiento||null,i=[S("💰","Ingresos",r(e.ingreso)),S("💳","Gastado",r(e.total_gastado)),S("🏦","FCI",r(e.capital_fci))].join("");let n="";if(s&&s.monto){const v=D(s.fecha),h=v!=null?v<=0?"🔴 VENCE HOY":`⏳ ${v} días`:"",N=((y=s.entidades)==null?void 0:y.join(" + "))||"TCs";n=R("🚨 Próximo vencimiento",`<strong>${N}</strong> — ${r(s.monto)}`,h,v!=null&&v<=3?"red":"yellow")}const d=e.tope_gasto?e.total_gastado/e.tope_gasto*100:0,o=p("🎯 Presupuesto del mes",`
    ${x(d)}
    <div style="display:flex;justify-content:space-between;font-size:13px;margin-top:4px;">
      <span>${r(e.total_gastado)} de ${r(e.tope_gasto)}</span>
      <span>${_(Math.round(d))}</span>
    </div>
  `),l=a.filter(v=>v.pct>=50).slice(0,4);let u="";l.length&&(u=p("🚦 Alertas",l.map(v=>`
      <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)">
        <span style="font-size:13px">${v.categoria}</span>
        <span style="color:var(--${P(v.pct)});font-size:13px">${_(v.pct)}</span>
      </div>
    `).join("")));const f=((m=t.inversiones)==null?void 0:m[0])||{},$=p("📈 FCI — Último mes",`
    <div class="detail-row"><span class="detail-label">Capital</span><span class="detail-value">${r(f.capital||e.capital_fci)}</span></div>
    <div class="detail-row"><span class="detail-label">Rendimiento</span><span class="detail-value" style="color:var(--green)">+${r(f.rendimiento||e.rendimiento_fci)}</span></div>
  `);return`
    <div class="header">
      <div class="header-title">💰 Panel Financiero</div>
      <div class="header-date">${new Date().toLocaleDateString("es-AR",{weekday:"short",day:"numeric",month:"long",year:"numeric"})}</div>
    </div>
    <div class="main" id="scroll-container">
      <div class="pull-indicator" id="pull-indicator">⬇️ Soltá para actualizar</div>
      <div class="stat-grid">${i}</div>
      ${n}
      ${o}
      ${u}
      ${$}
    </div>
    ${g("dashboard")}
  `}const U={Supermercado:"🛒",Delivery:"🍔",MercadoLibre:"🛍️",Comisiones:"🏦",Transporte:"🚇",Servicios:"🔌",Salud:"🩺",Entretenimiento:"🎮",Otros:"📦",Suscripciones:"📱",Indumentaria:"👕",Educación:"📚"};function K(t){const e=t.presupuesto||[],a=e.reduce((n,d)=>n+(d.presupuesto||0),0),s=e.reduce((n,d)=>n+(d.gastado||0),0),i=a?s/a*100:0;return`
    <div class="header">
      <div class="back-row" onclick="window.navigate('dashboard')">← Volver</div>
      <div class="header-title">📊 Presupuesto</div>
    </div>
    <div class="main">
      ${p("",`
        <div style="font-size:28px;font-weight:700">${r(a)}</div>
        ${x(i)}
        <div style="display:flex;justify-content:space-between;font-size:13px;color:var(--text-dim);margin-top:4px;">
          <span>Gastado: ${r(s)}</span>
          <span>Restan: ${r(a-s)}</span>
        </div>
      `)}

      ${p("Categorías",e.map(n=>F(U[n.categoria]||"📦",n.categoria,n.gastado,n.presupuesto,n.pct)).join(""))}
    </div>
    ${g("presupuesto")}
  `}function W(t){const e=t.tcs||[],a=e.reduce((o,l)=>o+(l.exigible||0),0);let s="";e.length?s=e.map(o=>{const l=[];if(o.cierre||o.vencimiento){const $=o.cierre_date||o.cierre,y=o.vto_date||o.vencimiento;l.push(`cierre ${$} · vence ${y}`),o.banco==="MercadoLibre"&&l.push("(débito)")}const u=l.length?`<div style="font-size:11px;color:var(--text-dim);margin-top:2px">${l.join(" ")}</div>`:"",f=o.exigible>1e5?'<div style="font-size:12px;color:var(--red);margin-top:4px">⚠️ Monto elevado</div>':"";return`<div class="detail-row">
          <div>
            <div style="font-weight:600">🏦 ${o.banco}</div>
            ${u}
            ${f}
          </div>
          <div style="text-align:right">
            <div style="font-weight:700">${r(o.exigible)}</div>
          </div>
        </div>`}).join(""):s='<div class="empty-state">No hay resúmenes disponibles</div>';let i="";const n=t.bancos_fechas||{},d=Object.entries(n);return d.length?i=d.map(([o,l])=>`<div class="detail-row"><span class="detail-label">${o}</span><span class="detail-value">cierre ${l.cierre_date||l.cierre} · vence ${l.vto_date||l.vencimiento}</span></div>`).join(""):i='<div class="empty-state">Sin datos de fechas</div>',`
    <div class="header">
      <div class="back-row" onclick="window.navigate('dashboard')">← Volver</div>
      <div class="header-title">💳 Pagos TC</div>
    </div>
    <div class="main">
      ${p("Resumen",`
        <div style="font-size:28px;font-weight:700">${r(a)}</div>
        <div style="font-size:12px;color:var(--text-dim);margin-top:4px">Total exigible del período</div>
      `)}

      ${p("Próximos vencimientos",s)}

      <div style="margin-top:12px">
        ${p("📅 Fechas de referencia",i)}
      </div>

      <div style="margin-top:12px">
        ${R("💡 Tip","Pagá con Lemon 🍋 para 2% cashback en todas las compras","")}
      </div>
    </div>
    ${g("pagos-tc")}
  `}function Q(t){const e=t.metas||[],a=e.reduce((s,i)=>s+(i.ahorrado||0),0);return`
    <div class="header">
      <div class="back-row" onclick="window.navigate('dashboard')">← Volver</div>
      <div class="header-title">🎯 Metas</div>
    </div>
    <div class="main">
      ${e.length?e.map(s=>`
        <div class="goal-card">
          <div class="goal-name">${s.nombre}</div>
          <div class="goal-meta">${s.estado||"En progreso"}</div>
          ${x(s.progreso)}
          <div class="goal-numbers">
            <span>${r(s.ahorrado)} / ${r(s.objetivo)}</span>
            <span>${s.progreso}%</span>
          </div>
        </div>
      `).join(""):'<div class="empty-state">No hay metas configuradas</div>'}

      <div class="divider"></div>
      ${X("",`
        <div style="text-align:center">
          <div style="font-size:12px;color:var(--text-dim);margin-bottom:4px">Total ahorrado</div>
          <div style="font-size:28px;font-weight:700;color:var(--green)">${r(a)}</div>
        </div>
      `)}
    </div>
    ${g("metas")}
  `}function X(t,e){return`
    <div class="card">
      
      ${e}
    </div>
  `}function Z(t){const e=t.salud||[],a=e.reduce((s,i)=>s+(i.costo_est||0),0);return`
    <div class="header">
      <div class="back-row" onclick="window.navigate('metas')">← Volver</div>
      <div class="header-title">🩺 Salud</div>
    </div>
    <div class="main">
      ${p("Resumen",`
        <div style="font-size:28px;font-weight:700">${r(a)}</div>
        <div style="font-size:12px;color:var(--text-dim);margin-top:4px">Costo estimado total pendiente</div>
      `)}

      ${e.length?e.map(s=>(s.estado==="Completado"||s.estado,`
          <div class="card" style="padding:14px">
            <div style="display:flex;justify-content:space-between;align-items:start">
              <div>
                <div style="font-weight:600;margin-bottom:4px">${s.profesional}</div>
                ${s.motivo?`<div style="font-size:12px;color:var(--text-dim);margin-bottom:4px">${s.motivo}</div>`:""}
                ${s.costo_est?`<div style="font-size:13px;color:var(--text)">💰 ${r(s.costo_est)}</div>`:""}
              </div>
              <span style="font-size:13px">${s.estado||"—"}</span>
            </div>
          </div>
        `)).join(""):'<div class="empty-state">No hay registros de salud</div>'}
    </div>
    ${g("metas")}
  `}function ee(t){const e=t.suscripciones||[],a=e.filter(i=>i.activo!==!1).reduce((i,n)=>i+(n.monto_mes||0),0),s=e.filter(i=>i.activo!==!1).reduce((i,n)=>i+(n.monto_anio||n.monto_mes*12||0),0);return`
    <div class="header">
      <div class="back-row" onclick="window.navigate('presupuesto')">← Volver</div>
      <div class="header-title">📱 Suscripciones</div>
    </div>
    <div class="main">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
        <div class="stat-card">
          <div class="stat-label">Total/mes</div>
          <div class="stat-value" style="font-size:18px">${r(a)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Total/año</div>
          <div class="stat-value" style="font-size:18px;color:var(--red)">${r(s)}</div>
        </div>
      </div>

      ${e.length?p("Servicios",e.map(i=>`
        <div class="sub-row">
          <div>
            <div class="sub-name">${i.servicio}</div>
            <div class="sub-meta">${i.activo!==!1?"✅ Activo":"❌ Inactivo"}</div>
          </div>
          <div style="text-align:right">
            <div class="sub-amount">${r(i.monto_mes)}/mes</div>
            ${i.monto_anio?`<div class="sub-meta">${r(i.monto_anio)}/año</div>`:""}
          </div>
        </div>
      `).join("")):'<div class="empty-state">No hay suscripciones registradas</div>'}
    </div>
    ${g("presupuesto")}
  `}let c={data:null,currentScreen:"dashboard",loading:!1};async function j(t=!1){if(c.loading)return;c.loading=!0;const e=document.getElementById("app");te(e);try{c.data=await C(t),b(c.currentScreen),I("✅ Datos actualizados")}catch(a){c.data?(b(c.currentScreen),I("📡 Mostrando datos en caché")):e.innerHTML=`
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;padding:32px;text-align:center">
          <div style="font-size:48px;margin-bottom:16px">😵</div>
          <div style="font-size:16px;font-weight:600;margin-bottom:8px">Error al cargar datos</div>
          <div style="font-size:13px;color:var(--text-dim);margin-bottom:16px">${a.message||"Sin conexión"}</div>
          <button onclick="window.forceRefresh()" style="background:var(--green);color:#0d0d0d;border:none;border-radius:8px;padding:10px 24px;font-size:14px;font-weight:600;cursor:pointer">Reintentar</button>
        </div>
      `}c.loading=!1}function te(t){const e=t.querySelector(".bottom-nav");t.innerHTML=`
    <div class="header">
      <div class="header-title">💰 Panel Financiero</div>
      <div class="header-date">Cargando...</div>
    </div>
    <div class="main">
      ${k()}
      ${k()}
    </div>
    ${e?e.outerHTML:""}
  `}function b(t){c.currentScreen=t;const e=document.getElementById("app");if(!c.data)return;let a="";switch(t){case"dashboard":a=T(c.data);break;case"presupuesto":a=K(c.data);break;case"pagos-tc":a=W(c.data);break;case"inversiones":a=Y(c.data);break;case"metas":a=Q(c.data);break;case"salud":a=Z(c.data);break;case"suscripciones":a=ee(c.data);break;default:a=T(c.data)}e.innerHTML=a,t==="inversiones"&&G("fci-chart");const s=e.querySelector(".main");s&&(s.scrollTop=0)}function I(t){let e=document.getElementById("toast");e||(e=document.createElement("div"),e.id="toast",document.body.appendChild(e)),e.textContent=t,e.classList.add("show"),clearTimeout(e._timeout),e._timeout=setTimeout(()=>e.classList.remove("show"),2500)}let A=0,w=!1;document.addEventListener("touchstart",t=>{const e=document.querySelector(".main");!e||e.scrollTop>0||(A=t.touches[0].clientY,w=!0)},{passive:!0});document.addEventListener("touchmove",t=>{if(!w)return;const e=document.querySelector(".main");if(!e||e.scrollTop>0)return;const a=t.touches[0].clientY-A,s=document.getElementById("pull-indicator");s&&(a>60?(s.textContent="⬆️ Soltá para actualizar",s.classList.add("show")):a>20?(s.textContent="⬇️ Tirá para actualizar",s.classList.add("show")):s.classList.remove("show"))},{passive:!0});document.addEventListener("touchend",()=>{if(!w)return;w=!1;const t=document.getElementById("pull-indicator");t!=null&&t.classList.contains("show")&&(t.textContent="🔄 Actualizando...",j(!0).then(()=>{t&&t.classList.remove("show")}))},{passive:!0});window.navigate=t=>{b(t)};window.forceRefresh=()=>{M(),j(!0)};(async function(){const e=document.getElementById("app");e.innerHTML=`
    <div class="header">
      <div class="header-title">💰 Panel Financiero</div>
      <div class="header-date">Cargando...</div>
    </div>
    <div class="main">
      ${k()}
    </div>
  `,c.data=await C(),b("dashboard"),setInterval(()=>C().then(a=>{c.data=a,b(c.currentScreen)}),3e5)})();

// ================= /static/js/sidebar.js =================
(function(){
  const KEY='sidebarOpen';
  const sidebar=document.getElementById('sidebar');
  const content=document.getElementById('content-wrapper');
  const overlay=document.getElementById('sidebar-overlay');

  function getState(){ try{return localStorage.getItem(KEY)==='1';}catch(e){return false;} }
  function saveState(v){ try{localStorage.setItem(KEY, v?'1':'0');}catch(e){} }
  function apply(open){
    if(!sidebar) return;
    if(open){
      sidebar.classList.remove('sidebar-hidden');
      if(content) content.classList.add('content-shrunk');
      if(window.innerWidth<768 && overlay) overlay.classList.add('show');
    }else{
      sidebar.classList.add('sidebar-hidden');
      if(content) content.classList.remove('content-shrunk');
      if(overlay) overlay.classList.remove('show');
    }
  }
  function toggle(){
    const open=!sidebar.classList.contains('sidebar-hidden');
    saveState(!open); apply(!open);
  }
  apply(getState());
  if(overlay) overlay.addEventListener('click',()=>{saveState(false);apply(false);});
  window.addEventListener('resize',()=>apply(getState()));
  window.toggleSidebar=toggle;
})();




// ================= /static/css/base.css =================
:root{ --sidebar-width:16rem; }
html,body{ height:100%; }
.sidebar-hidden{ transform:translateX(100%); }
.content-container{ transition: transform .3s ease, margin-right .3s ease; position: relative; z-index:10; }
.content-shrunk{ transform:none; margin-right:var(--sidebar-width); opacity:1; }
@media (max-width:767px){ .content-shrunk{ margin-right:0; } }
#sidebar-overlay{ display:none; position:fixed; inset:0; background:rgba(0,0,0,.35); z-index:40; }
#sidebar-overlay.show{ display:block; }
.dark .sidebar{ border-left:2px solid #4B5563; }
.nav-item{ display:flex; align-items:center; padding:.5rem; border-radius:.5rem; }
.nav-item.active{ background-color:#065f46; }
.nav-item span{ color:#f3f4f6; }
.badge-active-company{ font-size:.75rem; padding:.125rem .5rem; border-radius:.5rem; background:#064e3b; color:#ecfdf5; }

// ================= /static/js/pages/add-project.js =================
(function(){
  async function prefill(){
    try{
      const u=new URL(window.location.href);
      const companyId=u.searchParams.get('company_id');
      if(!companyId) return;
      const r=await fetch('/projects/'+encodeURIComponent(companyId),{credentials:'include'});
      if(!r.ok) return;
      const data=await r.json();
      localStorage.setItem('activeCompanyId',companyId);
      const form=document.getElementById('project-form'); if(!form) return;
      function setField(name,value){
        const el=form.querySelector('[name="'+name+'"]');
        if(el && value!=null){ if(el.type==='radio'||el.type==='checkbox'){ const cand=form.querySelector('[name="'+name+'"][value="'+value+'"]'); if(cand) cand.checked=true; } else { el.value=value; } }
      }
      Object.keys(data).forEach(k=>setField(k,data[k]));
      if(data.company_id) setField('company_id',data.company_id);
      if(data.company_name) setField('company_name',data.company_name);
    }catch(e){ console.warn('Prefill error',e); }
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',prefill); else prefill();
})();

// ================= /static/js/pages/companies.js =================
(function(){
  function attach(){
    const tableBody=document.getElementById('company-table'); if(!tableBody) return;
    tableBody.addEventListener('click',function(e){
      const tr=e.target.closest('tr'); if(!tr) return;
      let cid=tr.getAttribute('data-company-id');
      if(!cid){ const first=tr.querySelector('td'); if(first) cid=(first.textContent||'').trim(); }
      if(cid){
        localStorage.setItem('activeCompanyId',cid);
        const modal=document.getElementById('section-modal');
        if(!modal){ window.location.href='/financial-details/'+encodeURIComponent(cid); }
      }
    });
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',attach); else attach();
})();

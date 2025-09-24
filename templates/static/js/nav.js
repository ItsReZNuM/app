// ================= /static/js/nav.js =================
(function(){
  const MENU_HOME={ title:'خانه', href:'/' , icon:'/static/icons/home.svg'};
  const BASE_MENU=[
    {title:'یادآوری‌ها',href:'/reminders',icon:'/static/icons/bell.svg'},
    {title:'ثبت شرکت',href:'/add-project',icon:'/static/icons/plus.svg'},
    {title:'لیست شرکت‌ها',href:'/companies',icon:'/static/icons/building.svg'},
    {title:'گزارش‌ها',href:'/reports',icon:'/static/icons/chart-bar.svg'},
    {title:'تنظیمات',href:'/settings',icon:'/static/icons/cog.svg'}
  ];
  function getActiveCompanyId(){ try{return localStorage.getItem('activeCompanyId')||null;}catch(e){return null;} }
  function setActiveCompanyIdFromURL(){
    try{
      const u=new URL(window.location.href);
      const qid=u.searchParams.get('company_id');
      if(qid) localStorage.setItem('activeCompanyId',qid);
      const m=window.location.pathname.match(/^\/financial-details\/([^\/?#]+)/);
      if(m&&m[1]) localStorage.setItem('activeCompanyId',m[1]);
    }catch(e){}
  }
  function isActive(href){
    const path=window.location.pathname;
    if(href==='/' ) return path==='/' ;
    if(href.startsWith('/financial-details')) return path.startsWith('/financial-details');
    try{ return new URL(href,window.location.origin).pathname===path; }catch(e){ return href===path; }
  }
  function buildMenu(){
    const ul=document.getElementById('sidebar-menu'); if(!ul) return;
    ul.innerHTML='';
    const path=window.location.pathname;
    const items=[];
    if(path!=='/') items.push(MENU_HOME);
    items.push(...BASE_MENU);
    const companyId=getActiveCompanyId();
    if(companyId){
      items.push({title:'بروزرسانی شرکت',href:'/add-project?company_id='+encodeURIComponent(companyId),icon:'/static/icons/pencil.svg'});
      items.push({title:'وضعیت مالی',href:'/financial-details/'+encodeURIComponent(companyId),icon:'/static/icons/chart-bar.svg'});
      items.push({title:'تضمین‌ها',href:'/guarantees?company_id='+encodeURIComponent(companyId),icon:'/static/icons/shield.svg'});
      items.push({title:'بیمه تامین اجتماعی',href:'/social-security?company_id='+encodeURIComponent(companyId),icon:'/static/icons/users.svg'});
      items.push({title:'گزارش',href:'/reports?company_id='+encodeURIComponent(companyId),icon:'/static/icons/file-text.svg'});
    }
    items.forEach(it=>{
      const li=document.createElement('li');
      const a=document.createElement('a');
      a.href=it.href;
      a.className='nav-item hover:bg-green-700'+(isActive(it.href)?' active':'');
      const img=document.createElement('img'); img.src=it.icon; img.alt=it.title; img.className='ml-2 w-5 h-5';
      const span=document.createElement('span'); span.textContent=it.title;
      a.appendChild(img); a.appendChild(span); li.appendChild(a); ul.appendChild(li);
    });
    const chip=document.getElementById('active-company-chip');
    if(chip){ const cid=getActiveCompanyId(); chip.textContent=cid?('شرکت فعال: '+cid):''; chip.style.display=cid?'inline-block':'none'; }
  }
  function init(){ setActiveCompanyIdFromURL(); buildMenu(); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
})();

// ================= /static/js/auth.js =================
(function(){
  async function guard(){
    try{
      const r=await fetch('/api/check-login',{credentials:'include'});
      if(!r.ok) window.location.replace('/login');
    }catch(e){ window.location.replace('/login'); }
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',guard); else guard();
})();

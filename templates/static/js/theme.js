// ================= /static/js/theme.js =================
(function(){
  const KEY='theme';
  function apply(){
    try{
      const v=localStorage.getItem(KEY)||'light';
      const root=document.documentElement;
      if(v==='dark') root.classList.add('dark'); else root.classList.remove('dark');
    }catch(e){}
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',apply); else apply();
  window.toggleTheme=function(){
    const v=(localStorage.getItem(KEY)||'light')==='light'?'dark':'light';
    localStorage.setItem(KEY,v); apply();
  }
})();
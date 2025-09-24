
(function () {
  async function prefill() {
    try {
      const u = new URL(window.location.href);
      const companyId = u.searchParams.get('company_id');
      if (!companyId) return;

      const r = await fetch('/projects/' + encodeURIComponent(companyId), {credentials: 'include'});
      if (!r.ok) return;
      const data = await r.json();
      // Persist selection too
      try { localStorage.setItem('activeCompanyId', companyId); } catch (e) {}

      const form = document.getElementById('project-form');
      if (!form) return;
      const setField = (name, value) => {
        const el = form.querySelector('[name="'+name+'"]');
        if (el && value != null) {
          if (el.type === 'radio' || el.type === 'checkbox') {
            const candidate = form.querySelector('[name="'+name+'"][value="'+value+'"]');
            if (candidate) candidate.checked = true;
          } else {
            el.value = value;
          }
        }
      };
      // Apply each field that matches input names
      Object.keys(data).forEach(k => setField(k, data[k]));
      // Ensure company_id & company_name if available
      if (data.company_id) setField('company_id', data.company_id);
      if (data.company_name) setField('company_name', data.company_name);
    } catch (e) {
      console.warn('Prefill error', e);
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', prefill);
  } else {
    prefill();
  }
})();

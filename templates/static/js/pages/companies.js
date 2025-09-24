
(function () {
  function attach() {
    const tableBody = document.getElementById('company-table');
    if (!tableBody) return;

    tableBody.addEventListener('click', function (e) {
      const tr = e.target.closest('tr');
      if (!tr) return;
      let cid = tr.getAttribute('data-company-id');
      if (!cid) {
        // Try first cell text as fallback
        const first = tr.querySelector('td');
        if (first) cid = (first.textContent || '').trim();
      }
      if (cid) {
        try { localStorage.setItem('activeCompanyId', cid); } catch (e) {}
        // If there is a modal present, let existing code open it.
        const modal = document.getElementById('section-modal');
        if (!modal) {
          // redirect to details as default
          window.location.href = '/financial-details/' + encodeURIComponent(cid);
        }
      }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attach);
  } else {
    attach();
  }
})();

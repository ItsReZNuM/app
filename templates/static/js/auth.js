
// Minimal auth guard used on protected pages
(function () {
  function guard() {
    fetch('/api/check-login', {credentials: 'include'})
      .then(async (r) => {
        if (!r.ok) {
          window.location.replace('/login');
        }
      })
      .catch(() => {
        // In local single-user mode, if API fails, keep user on page silently.
      });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', guard);
  } else {
    guard();
  }
})();

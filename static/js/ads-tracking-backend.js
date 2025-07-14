(function () {
  function getGclidFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('gclid');
  }

  function storeGclid(gclid) {
    if (gclid) {
      localStorage.setItem('gclid', gclid);
    }
  }

  function getStoredGclid() {
    return localStorage.getItem('gclid');
  }

  function getCsrfToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        return cookie.substring(name.length + 1);
      }
    }
    return null;
  }
  
  function getClientInfo() {
    try {
      const info = localStorage.getItem('client_info');
      return info ? JSON.parse(info) : {};
    } catch (err) {
      return {};
    }
  }

  function sendGclidToBackend(conversionName, gclid, page) {
    const csrfToken = getCsrfToken();
    if (!csrfToken || !gclid) return;

    fetch('/api/conversion-tracking/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({
        gclid: gclid,
        conversion_name: conversionName,
        page: page,
        client_info: getClientInfo(),
      })
    }).then(response => {
      if (!response.ok) {
        console.error('Conversion tracking failed:', response.status);
      }
    }).catch(err => {
      console.error('Conversion tracking error:', err);
    });
  }

  const gclidFromUrl = getGclidFromUrl();
  if (gclidFromUrl) {
    storeGclid(gclidFromUrl);
  }

  const finalGclid = gclidFromUrl || getStoredGclid();
  const pathname = window.location.pathname;

  if (finalGclid) {
    if (pathname.includes('/telefon-yonlendirme')) {
      sendGclidToBackend('Telefon Araması', finalGclid, pathname);
    } else if (pathname.includes('/whatsapp-yonlendirme')) {
      sendGclidToBackend('WhatsApp Mesajı', finalGclid, pathname);
    }
  }
})();

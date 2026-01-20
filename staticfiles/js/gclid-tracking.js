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

  // 1. URL'den gclid al
  const gclidFromUrl = getGclidFromUrl();

  // 2. URL'de varsa localStorage'a kaydet veya güncelle
  if (gclidFromUrl) {
    storeGclid(gclidFromUrl);
  }

  // 3. Yoksa localStorage'da zaten var mı kontrol et (şimdilik sadece kontrol, işlem yok)
  const existingGclid = getStoredGclid();
})();

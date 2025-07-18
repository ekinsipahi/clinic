document.addEventListener("DOMContentLoaded", function () {
  const containers = document.querySelectorAll('.comparison-container');

  containers.forEach((container) => {
    const slider = container.querySelector('.comparison-slider');

    if (slider) {
      // Normal input hareketi
      slider.addEventListener('input', (e) => {
        container.style.setProperty('--position', `${e.target.value}%`);
      });

      // Mobil sürükleme desteği
      slider.addEventListener('touchstart', (e) => {
        e.preventDefault();
      }, { passive: false });

      slider.addEventListener('touchmove', (e) => {
        e.preventDefault();
        if (e.touches.length > 0) {
          const rect = slider.getBoundingClientRect();
          const x = e.touches[0].clientX - rect.left;
          let percent = (x / rect.width) * 100;
          percent = Math.max(0, Math.min(100, percent));
          slider.value = percent;
          container.style.setProperty('--position', `${percent}%`);
        }
      }, { passive: false });
    } else {
      console.warn("Slider bulunamadı:", container);
    }
  });
});
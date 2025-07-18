document.addEventListener("DOMContentLoaded", function () {
  const containers = document.querySelectorAll('.comparison-container');

  containers.forEach((container) => {
    const slider = container.querySelector('.comparison-slider');
    if (slider) {
      slider.addEventListener('input', (e) => {
        container.style.setProperty('--position', `${e.target.value}%`);
      });
    } else {
      console.warn("Slider bulunamadı:", container);
    }
  });
});

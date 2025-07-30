  document.addEventListener("DOMContentLoaded", function () {
    const categoryButtons = document.querySelectorAll(".faq-category");
    const faqGroups = document.querySelectorAll(".faq-group");

    categoryButtons.forEach(button => {
      button.addEventListener("click", () => {
        const targetId = button.getAttribute("data-target");

        // Aktif olmayan tüm butonları gri yap
        categoryButtons.forEach(btn => {
          btn.classList.remove("text-blue-500");
          btn.classList.add("text-gray-500");
        });

        // Tıklanan butonu mavi yap
        button.classList.remove("text-gray-500");
        button.classList.add("text-blue-500");

        // Tüm faq gruplarını gizle
        faqGroups.forEach(group => {
          group.classList.add("hidden");
        });

        // Hedef grubu göster
        const targetGroup = document.getElementById(targetId);
        if (targetGroup) {
          targetGroup.classList.remove("hidden");
        }
      });
    });

    // Soru aç/kapa
    document.querySelectorAll(".faq-toggle").forEach(toggle => {
      toggle.addEventListener("click", () => {
        const content = toggle.nextElementSibling;
        const allContents = toggle.closest('.faq-group').querySelectorAll(".faq-content");

        allContents.forEach(c => {
          if (c !== content) c.classList.add("hidden");
        });

        content.classList.toggle("hidden");
      });
    });
  });
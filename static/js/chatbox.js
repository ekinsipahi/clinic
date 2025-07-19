const toggleChatboxBtn = document.querySelector(".js-chatbox-toggle");
const chatbox = document.querySelector(".js-chatbox");
const chatboxMsgDisplay = document.querySelector(".js-chatbox-display");
const chatboxForm = document.querySelector(".js-chatbox-form");
const chatboxAlert = document.getElementById("chatbox-alert");


const linkify = (text) => {
    return text.replace(/(https:\/\/[^\s\)\]\}]+)/g, url => {
        return `<a href="${url}" target="_blank" style="color:#2a6edb;">${url}</a>`;
    });
};

const createChatBubble = input => {
    const chatSection = document.createElement("p");
    chatSection.textContent = input;
    chatSection.classList.add("chatbox__display-chat");
    chatSection.style.marginBottom = "4px";
    chatboxMsgDisplay.appendChild(chatSection);


    chatSection.innerHTML = linkify(input);

    // Scroll en aşağıya insin
    chatSection.scrollIntoView({ behavior: "smooth" });
};

toggleChatboxBtn.addEventListener("click", () => {
    chatbox.classList.toggle("chatbox--is-visible");
    toggleChatboxBtn.innerHTML = chatbox.classList.contains("chatbox--is-visible")
        ? '<i class="fas fa-chevron-down"></i>'
        : '<i class="fas fa-chevron-up"></i>';
});

// Sohbet kutusu kapandığında zıplayan balonu geri göster
const observer = new MutationObserver(() => {
  const isVisible = chatbox.classList.contains("chatbox--is-visible");
  if (!isVisible) {
    chatboxAlert.style.display = "block";
  }
});

// chatbox elementindeki class değişimini izle
observer.observe(chatbox, { attributes: true, attributeFilter: ["class"] });


/* Normal kutucuk */
document.addEventListener("DOMContentLoaded", function () {
    const toggleChatboxBtn = document.querySelector(".chatbox__header");
    const chatbox = document.querySelector(".chatbox");

    if (!toggleChatboxBtn || !chatbox) {
        console.warn("Chatbox veya buton bulunamadı.");
        return;
    }

    const toggleChatbox = () => {
        chatbox.classList.toggle("chatbox--is-visible");
        // Chatbox açıldığında uyarı balonunu gizle
        if (chatboxAlert) {
            chatboxAlert.style.display = "none";
        }
    };

    // Hem mobil hem desktop için olayları destekle
    toggleChatboxBtn.addEventListener("click", toggleChatbox);
    toggleChatboxBtn.addEventListener("touchstart", (e) => {
        // iOS'ta çift tetiklenme riskine karşı sadece dokunmaya özel çağır
        e.preventDefault();
        toggleChatbox();
    }, { passive: false });
});


/* Zıplayan alert */
document.addEventListener("DOMContentLoaded", function () {
    const toggleChatboxBtn = document.querySelector(".js-chatbox-toggle");
    const chatbox = document.querySelector(".js-chatbox");
    const chatboxAlert = document.getElementById("chatbox-alert");

    if (!chatboxAlert || !chatbox || !toggleChatboxBtn) {
        console.warn("Gerekli elementler bulunamadı.");
        return;
    }

    const openChatbox = () => {
        if (!chatbox.classList.contains("chatbox--is-visible")) {
            chatbox.classList.add("chatbox--is-visible");
            toggleChatboxBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
        }
        chatboxAlert.style.display = "none";
    };

    // Masaüstü tıklama
    chatboxAlert.addEventListener("click", openChatbox);

    // Mobil dokunma
    chatboxAlert.addEventListener("touchstart", function (e) {
        e.preventDefault(); // scroll bozulmasın
        openChatbox();
    }, { passive: false });
});

// Mesaj geçmişini al veya başlat
let messages = JSON.parse(localStorage.getItem("chat_history")) || [
    {
        role: "system",
        content: `Sen Dr. Devrim Biriken Sipahi'nin dijital asistanısın.

Klinik, diş estetiğinde uzman ve doğal, diş kesilmeden yapılan işlemlerle yüksek hasta memnuniyeti sağlar.

Görevin:
- Kullanıcının neye ihtiyacı olduğunu anlamak
- Onu en uygun iletişim kanalına yönlendirmek

📞 “Hemen arayarak bilgi alabilir ve randevu oluşturabilirsiniz: +90 505 577 18 83”
💬 “WhatsApp’tan yazarsanız mesajınızı doğrudan Dr. Devrim’e iletebilirim.”

Kullanıcı seçim yaparsa:
- WhatsApp → 'action: whatsapp-yonlendirme'
- Telefon → 'action: telefon-yonlendirme'

Online randevu isteyenlere:
🔗 “Kolayca form doldurarak randevu oluşturabilirsiniz: https://www.devrimbirikensipahi.com.tr/randevu-al”

Kararsız veya araştırma aşamasındaysa:
📷 “Hocamızı ve hastaların yorumlarını daha yakından incelemek isterseniz Instagram hesabımıza göz atabilirsiniz: https://www.devrimbirikensipahi.com.tr/instagram-yonlendirme”

🦷 “Orada yüzlerce memnun hastanın dönüşüm hikayesini bulabilirsiniz. İnceleyip gönül rahatlığıyla karar verebilirsiniz.”

Kurallar:
- Asla kullanıcıdan isim, telefon veya özel bilgi isteme
- Samimi, sade ve güven verici konuş
- Nihai hedef: WhatsApp yazışması veya telefon görüşmesine yönlendirme`

    }
];

const getCSRFToken = () => {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
};




chatboxForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const inputElement = document.querySelector(".js-chatbox-input");
    const userInput = inputElement.value.trim();
    if (!userInput) return;

    createChatBubble("👤 Siz: " + userInput);
    messages.push({ role: "user", content: userInput });
    inputElement.value = "";

    // System mesajını sabit al
    const systemMessage = messages[0];
    // Son 8 kullanıcı/asistan mesajını al (sondan 8)
    const recentMessages = messages.slice(-8);
    // API'ye gidecek final mesaj listesi
    const messagesToSend = [systemMessage, ...recentMessages];

    try {
        const response = await fetch("/api/ai-agent/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken()
            },
            body: JSON.stringify({ messages: messagesToSend })
        });

        const data = await response.json();
        if (data.response) {
            createChatBubble("🤖 Asistan: " + data.response);
            messages.push({ role: "assistant", content: data.response });
            localStorage.setItem("chat_history", JSON.stringify(messages));

            // Gecikmeli yönlendirme sistemi
            if (data.response.includes("action: telefon-yonlendirme")) {
                setTimeout(() => {
                    createChatBubble("📞 Sizi telefon arama ekranına yönlendiriyorum...");
                    setTimeout(() => {
                        window.location.href = "/telefon-yonlendirme";
                    }, 1500); // 1.5 saniye sonra yönlendir
                }, 500); // 0.5 saniye sonra yanıtı göster
            } else if (data.response.includes("action: whatsapp-yonlendirme")) {
                setTimeout(() => {
                    createChatBubble("💬 Sizi WhatsApp’a yönlendiriyorum, oradan doğrudan mesaj atabilirsiniz.");
                    setTimeout(() => {
                        window.location.href = "/whatsapp-yonlendirme";
                    }, 1500);
                }, 500);
            }

        } else {
            createChatBubble("🤖 Asistan: Şu an bir hata oluştu.");
        }
    } catch (error) {
        createChatBubble("🤖 Asistan: Sunucuya ulaşılamıyor.");
    }
});

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

    // Kullanıcı girişi kontrolleri
    if (!userInput) return;

    if (userInput.length > 600) {
        alert("Mesajınız 600 karakteri geçemez.");
        return;
    }

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
        // 1. Öncelik: callme-lead-action varsa önce onu işle
        if (data.response && data.response.includes("action: callme-lead-action")) {
            const jsonMatch = data.response.match(/```json\s*({[\s\S]*?})\s*```/);
            if (jsonMatch && jsonMatch[1]) {
                createChatBubble("🤖 Asistan: Bilgilerinizi kaydediyorum, lütfen bekleyin...");
                try {
                    const parsed = JSON.parse(jsonMatch[1]);

                    const gclid = localStorage.getItem("gclid") || null;
                    const clientInfo = JSON.parse(localStorage.getItem("client_info") || "{}");
                    console.log("Gelen veriler:", parsed)
                    await fetch("/api/ai-callme-lead/", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getCSRFToken()
                        },
                        body: JSON.stringify({
                            name: parsed.name,
                            phone: parsed.phone,
                            message: parsed.message || "",
                            gclid: gclid,
                            client_info: clientInfo,
                            page: "AI Beni Ara Lead"
                        })
                    });

                    createChatBubble("📞 Bilgilerinizi başarıyla kaydettik. Sabah en kısa sürede sizinle iletişime geçilecektir.");

                    // 1 saniye beklet, sonra yönlendir
                    setTimeout(() => {
                        createChatBubble("🔁 Sizi teşekkür sayfasına yönlendiriyorum, lütfen bekleyin...");
                        setTimeout(() => {
                            window.location.href = "/tesekkur";
                        }, 1500);
                    }, 500);


                    messages.push({ role: "assistant", content: data.response });
                    localStorage.setItem("chat_history", JSON.stringify(messages));
                } catch (err) {
                    console.error("JSON parse hatası:", err);
                    createChatBubble("🤖 Asistan: Bilgileri işlerken bir hata oluştu.");
                }
            } else {
                console.warn("JSON formatı bulunamadı.");
                createChatBubble("🤖 Asistan: Lütfen bilgilerinizi tekrar paylaşır mısınız?");
            }

            // 2. Aksiyon içeriyorsa kontrol et: telefon ya da whatsapp yönlendirme
        } else if (data.response) {
            createChatBubble("🤖 Asistan: " + data.response);
            messages.push({ role: "assistant", content: data.response });
            localStorage.setItem("chat_history", JSON.stringify(messages));

            if (data.response.includes("action: telefon-yonlendirme")) {
                setTimeout(() => {
                    createChatBubble("📞 Sizi telefon arama ekranına yönlendiriyorum...");
                    setTimeout(() => {
                        window.location.href = "/telefon-yonlendirme";
                    }, 1500);
                }, 500);

            } else if (data.response.includes("action: whatsapp-yonlendirme")) {
                setTimeout(() => {
                    createChatBubble("💬 Sizi WhatsApp’a yönlendiriyorum, oradan doğrudan mesaj atabilirsiniz.");
                    setTimeout(() => {
                        window.location.href = "/whatsapp-yonlendirme";
                    }, 1500);
                }, 500);
            }

            // 3. data.response yoksa:
        } else {
            createChatBubble("🤖 Asistan: Şu an bir hata oluştu.");
        }
    } catch (error) {
        createChatBubble("🤖 Asistan: Sunucuya ulaşılamıyor.");
    }
});

// Karakter sayacı
document.addEventListener("DOMContentLoaded", () => {
    const inputEl = document.querySelector(".js-chatbox-input");
    const counterEl = document.querySelector(".char-counter");

    if (inputEl && counterEl) {
        inputEl.addEventListener("input", () => {
            const len = inputEl.value.length;
            counterEl.textContent = `${len} / 600`;

            if (len > 600) {
                counterEl.classList.add("text-red-600", "font-bold");
            } else {
                counterEl.classList.remove("text-red-600", "font-bold");
            }
        });
    }
});


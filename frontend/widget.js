/**
 * STAJ PROJESİ CHATBOT WIDGET MANTIĞI
 * 
 * Bu dosya chatbot widget'ının:
 * 1. Açılma/Kapanma animasyonlarını
 * 2. Kullanıcı ve bot mesajlarının ekrana eklenmesini
 * 3. Backend API (Zeynep & Diğer Arkadaşlar) entegrasyonunu
 * 4. Otomatik kaydırma ve yükleniyor efektlerini yönetir.
 */

// ==========================================
// CONFIG & BACKEND API AYARI
// ==========================================
// Zeynep'in hazırladığı Gemini Uyumlu Backend API Adresi:
//const BACKEND_API_URL = // LibreChat OpenAI Uyumlu Chat Endpoint'i
const BACKEND_API_URL = "http://localhost:8080/v1/chat/completions";

// ==========================================
// DOM ELEMENT SEÇİCİLERİ
// ==========================================
const chatToggleBtn = document.getElementById("chat-toggle-btn");
const chatWindow = document.getElementById("chat-window");
const closeChatBtn = document.getElementById("close-chat-btn");
const clearChatBtn = document.getElementById("clear-chat-btn");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const typingIndicator = document.getElementById("typing-indicator");
const unreadBadge = document.getElementById("unread-badge");
const chatIcon = document.querySelector(".chat-icon");
const closeIcon = document.querySelector(".close-icon");

let isChatOpen = false;

// ==========================================
// ETKİNLİK DİNLEYİCİLERİ (EVENT LISTENERS)
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    // Floating butona tıklama
    chatToggleBtn.addEventListener("click", toggleChat);

    // Kapatma butonuna tıklama
    closeChatBtn.addEventListener("click", toggleChat);

    // Sohbeti Temizle butonuna tıklama
    clearChatBtn.addEventListener("click", clearChat);

    // Form gönderme işlemi
    chatForm.addEventListener("submit", handleSendMessage);
});

// ==========================================
// 1. SOHBET PENCERESİ AÇ / KAPAT MANTIĞI
// ==========================================
function toggleChat() {
    isChatOpen = !isChatOpen;

    if (isChatOpen) {
        chatWindow.classList.remove("hidden");
        chatIcon.classList.add("hidden");
        closeIcon.classList.remove("hidden");
        unreadBadge.classList.add("hidden"); // Bildirim rozetini gizle
        chatInput.focus(); // Input'a odaklan
    } else {
        chatWindow.classList.add("hidden");
        chatIcon.classList.remove("hidden");
        closeIcon.classList.add("hidden");
    }
}

// ==========================================
// 2. MESAJ GÖNDERME İŞLEMİ
// ==========================================
async function handleSendMessage(event) {
    event.preventDefault();

    const userText = chatInput.value.trim();
    if (!userText) return;

    // Input alanını temizle
    chatInput.value = "";

    // 1. Kullanıcı mesajını ekrana ekle
    appendMessage(userText, "user");

    // 2. Öneri çipleri görünüyorsa gizle
    const suggestions = document.getElementById("suggestions");
    if (suggestions) suggestions.remove();

    // 3. Yazıyor... animasyonunu göster
    showTypingIndicator();

    // 4. Backend API'ye istek at (veya Demo Yanıtı üret)
    try {
        const botReply = await fetchBotResponse(userText);
        hideTypingIndicator();
        appendMessage(botReply, "bot");
    } catch (error) {
        console.error("Backend Baglanti Hatasi:", error);
        hideTypingIndicator();
        appendMessage(
            `⚠️ Bağlantı Kurulamadı: ${error.message}`,
            "bot"
        );
    }
}

// Öneri Butonlarına Tıklandığında Çağrılan Fonksiyon
function sendSuggestion(text) {
    chatInput.value = text;
    chatForm.dispatchEvent(new Event("submit", { cancelable: true }));
}

// ==========================================
// 3. BACKEND API İLE İLETİŞİM (GEMİNI & RAG BACKEND)
// ==========================================
async function fetchBotResponse(messageText) {
    try {
        const response = await fetch(BACKEND_API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                model: "gemini-1.5-flash",
                messages: [
                    { role: "user", content: messageText }
                ]
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(`Sunucu Hatası (${response.status}): ${errorData.message || response.statusText || 'Endpoint bulunamadı'}`);
        }

        const data = await response.json();
        if (data.choices && data.choices[0] && data.choices[0].message) {
            return data.choices[0].message.content;
        } else if (data.candidates && data.candidates[0] && data.candidates[0].content) {
            return data.candidates[0].content.parts[0].text;
        }
        return "Yanıt alınamadı.";

    } catch (err) {
        console.error("API Bağlantı Hatası:", err);
        return `⚠️ Bağlantı Kurulamadı: ${err.message}`;
    }
}

// DEMO YANITI ÜRETİCİ (Backend kapalıyken test etmek için)
function getDemoResponse(text) {
    return new Promise((resolve) => {
        setTimeout(() => {
            const lower = text.toLowerCase();
            if (lower.includes("merhaba") || lower.includes("selam")) {
                resolve("Merhaba! Size nasıl yardımcı olabilirim?");
            } else if (lower.includes("staj") || lower.includes("proje")) {
                resolve("Bu proje 3 kişilik ekibiniz tarafından geliştirilen akıllı bir Chatbot sistemidir!");
            } else if (lower.includes("iletişim")) {
                resolve("Ekip üyelerine veya sistem yöneticisine admin@stajprojesi.com adresinden ulaşabilirsiniz.");
            } else {
                resolve(`"${text}" sorunuz alındı! Backend RAG sisteminiz (Zeynep'in yazdığı API) bağlandığında burada gerçek yapay zeka cevabı gözükecektir! 🚀`);
            }
        }, 1200); // 1.2 saniye yapay bekleme süresi
    });
}

// ==========================================
// 4. MESAJ BALONCUKLARINI EKRANA EKLEME
// ==========================================
function appendMessage(text, sender) {
    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", sender === "user" ? "user-message" : "bot-message");

    const avatarDiv = document.createElement("div");
    avatarDiv.classList.add("message-avatar");
    avatarDiv.innerHTML = sender === "user" ? '<i class="fa-solid fa-user"></i>' : '<img src="bot-avatar.png?v=2" alt="Bot Avatar" class="bot-avatar-img">';

    const contentDiv = document.createElement("div");
    contentDiv.classList.add("message-content");

    // --- DEĞİŞİKLİK BURADA BAŞLIYOR ---
    if (sender === "bot") {
        // Bot mesajları için marked kütüphanesini kullanıp HTML olarak basıyoruz
        contentDiv.innerHTML = marked.parse(text); 
    } else {
        // Kullanıcı mesajları güvenlik için düz metin (text) olarak kalmaya devam ediyor
        const p = document.createElement("p");
        p.textContent = text;
        contentDiv.appendChild(p);
    }
    // --- DEĞİŞİKLİK BURADA BİTİYOR ---

    const timeSpan = document.createElement("span");
    timeSpan.classList.add("message-time");
    timeSpan.textContent = timeString;

    // SADECE bunu bırakın, 'p' ekleme satırını tamamen silin veya yoruma alın:
    contentDiv.appendChild(timeSpan); 

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    chatMessages.appendChild(messageDiv);

    // Otomatik En Aşağıya Kaydır
    scrollToBottom();
}


// ==========================================
// 5. YARDIMCI FONKSİYONLAR
// ==========================================
function showTypingIndicator() {
    typingIndicator.classList.remove("hidden");
    scrollToBottom();
}

function hideTypingIndicator() {
    typingIndicator.classList.add("hidden");
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function clearChat() {
    // Karşılama mesajı hariç tüm mesajları temizle
    chatMessages.innerHTML = `
        <div class="message bot-message">
            <div class="message-avatar">
                <img src="bot-avatar.png?v=2" alt="Bot Avatar" class="bot-avatar-img">
            </div>
            <div class="message-content">
                <p>Sohbet geçmişi temizlendi. Size başka nasıl yardımcı olabilirim? 😊</p>
                <span class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
        </div>
    `;
}

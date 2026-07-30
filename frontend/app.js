document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("toggle-btn");
  const chatCard = document.getElementById("chat-card");
  const sendBtn = document.getElementById("send-btn");
  const userInput = document.getElementById("user-input");
  const chatMessages = document.getElementById("chat-messages");

  // Live Render Backend Endpoint
  const BACKEND_URL = "https://spritle-bot.onrender.com/chat";
  let conversationHistory = [];

  // Toggle Collapse/Expand UI
  toggleBtn.addEventListener("click", () => {
    if (chatCard.style.display === "none") {
      chatCard.style.display = "flex";
      toggleBtn.querySelector("path").setAttribute("d", "M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z");
    } else {
      chatCard.style.display = "none";
      toggleBtn.querySelector("path").setAttribute("d", "M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z");
    }
  });

  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // Render User Bubble
    appendUserMessage(text);
    userInput.value = "";

    // Show Loading Bubble
    const loadingElem = appendBotMessage("...");

    try {
      const response = await fetch(BACKEND_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          conversation_history: conversationHistory
        })
      });

      const data = await response.json();
      const botReply = data.reply || "Thank you! We'll get back to you shortly.";

      loadingElem.innerText = botReply;

      // Update history array
      conversationHistory.push(`User: ${text}`);
      conversationHistory.push(`Bot: ${botReply}`);

    } catch (err) {
      loadingElem.innerText = "Error connecting to server. Please ensure backend is active.";
    }

    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function appendUserMessage(text) {
    const group = document.createElement("div");
    group.className = "message-group user-group";
    group.innerHTML = `<div class="chat-bubble user-bubble">${text}</div>`;
    chatMessages.appendChild(group);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function appendBotMessage(text) {
    const group = document.createElement("div");
    group.className = "message-group bot-group";
    group.innerHTML = `
      <span class="sender-name">Spritle Bot</span>
      <div class="chat-bubble bot-bubble">${text}</div>
    `;
    chatMessages.appendChild(group);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return group.querySelector(".bot-bubble");
  }

  sendBtn.addEventListener("click", sendMessage);
  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });
});

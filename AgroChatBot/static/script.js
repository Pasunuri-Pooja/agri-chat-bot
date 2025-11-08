//script.js

// document.addEventListener('DOMContentLoaded', () => {
//   console.log('script loaded');
//   const messages = document.getElementById('messages');
//   const input = document.getElementById('msg');
//   const sendBtn = document.getElementById('sendBtn');
//   function addMessage(who, text) {
//     const el = document.createElement('div');
//     el.className = 'message ' + who;
//     const bubble = document.createElement('div');
//     bubble.className = 'bubble';
//     bubble.textContent = text;
//     el.appendChild(bubble);
//     messages.appendChild(el);
//     messages.scrollTop = messages.scrollHeight;
//   }
//   async function sendMessage() {
//     const msg = input.value.trim();
//     if (!msg) return;
//     addMessage('user', msg);
//     input.value = '';
//     sendBtn.disabled = true;
//     try {
//       const res = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message: msg})});
//       if (!res.ok) throw new Error('Network response not ok');
//       const data = await res.json();
//       addMessage('bot', data.response || 'No response');
//     } catch (err) {
//       console.error(err);
//       addMessage('bot', 'Error connecting to server');
//     } finally {
//       sendBtn.disabled = false;
//       input.focus();
//     }
//   }
//   sendBtn && sendBtn.addEventListener('click', sendMessage);
//   input && input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
// });










// ✅ script.js (final version)
document.addEventListener("DOMContentLoaded", () => {
  console.log("Chat script initialized");

  const messages = document.getElementById("messages");
  const input = document.getElementById("msg");
  const sendBtn = document.getElementById("sendBtn");
  const attachBtn = document.getElementById("attachBtn");
  const fileInput = document.getElementById("file-input");

  function addMessage(sender, text) {
    const msgDiv = document.createElement("div");
    msgDiv.className = sender === "user" ? "message user" : "message bot";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    msgDiv.appendChild(bubble);

    messages.appendChild(msgDiv);
    messages.scrollTop = messages.scrollHeight;
  }

  async function sendMessage() {
    const text = input.value.trim();
    const file = fileInput.files[0];

    if (!text && !file) return;

    // Display user message immediately
    if (file) addMessage("user", `📎 Sent file: ${file.name}`);
    else addMessage("user", text);

    sendBtn.disabled = true;
    input.value = "";

    try {
      if (file) {
        // ✅ send file to /api/file-analyze
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("/api/file-analyze", {
          method: "POST",
          body: formData,
        });

        const data = await res.json();
        addMessage("bot", data.response || data.error || "Could not analyze file.");
        fileInput.value = "";

      } else {
        // ✅ send text to /api/chat
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });

        const data = await res.json();
        addMessage("bot", data.response || "No response received.");
      }

    } catch (err) {
      console.error("Chat error:", err);
      addMessage("bot", "⚠️ Error connecting to server.");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  // 🟢 Send on click
  sendBtn.addEventListener("click", sendMessage);

  // 🟢 Send on Enter key
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // 🟢 File attach button
  attachBtn.addEventListener("click", () => {
    fileInput.click();
  });
});

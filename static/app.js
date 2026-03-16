const queryInput = document.getElementById("query-input");
const submitBtn = document.getElementById("submit-btn");
const loading = document.getElementById("loading");
const categoryBadge = document.getElementById("category-badge");
const results = document.getElementById("results");
const chatSection = document.getElementById("chat-section");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatBtn = document.getElementById("chat-btn");

let lastRecommendation = null;
let chatHistory = [];

// --- Chips ---
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    queryInput.value = chip.dataset.query;
    submitQuery();
  });
});

// --- Submit ---
submitBtn.addEventListener("click", submitQuery);
queryInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") submitQuery();
});

async function submitQuery() {
  const text = queryInput.value.trim();
  if (!text) return;

  // Reset
  results.classList.add("hidden");
  chatSection.classList.add("hidden");
  categoryBadge.classList.add("hidden");
  chatMessages.innerHTML = "";
  chatHistory = [];
  loading.classList.remove("hidden");
  submitBtn.disabled = true;

  try {
    const res = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ part_type: text }),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.error || "Something went wrong");
      return;
    }

    const data = await res.json();
    lastRecommendation = data;
    renderResults(data);
  } catch (e) {
    alert("Failed to connect to server.");
  } finally {
    loading.classList.add("hidden");
    submitBtn.disabled = false;
  }
}

function renderResults(data) {
  // Category badge
  categoryBadge.innerHTML = `Matched category: <span>${data.matched_category}</span>`;
  categoryBadge.classList.remove("hidden");

  // Cards
  fillCard("card-recommended", data.recommended);
  fillCard("card-alternative", data.alternative);
  fillCard("card-avoid", data.avoid);

  // Context bar
  const ctx = data.context;
  document.getElementById("context-bar").textContent =
    `${ctx.total_historical_orders} historical orders analyzed across ${ctx.suppliers_evaluated} suppliers for ${ctx.part_category} parts`;

  results.classList.remove("hidden");
  chatSection.classList.remove("hidden");
}

function fillCard(id, entry) {
  const card = document.getElementById(id);
  if (!entry) {
    card.classList.add("hidden");
    return;
  }
  card.classList.remove("hidden");
  card.querySelector(".card-supplier").textContent = entry.supplier;
  card.querySelector(".card-reason").textContent = entry.reason;
  card.querySelector(".card-stats").innerHTML = `
    <div class="stat">
      <span class="stat-value">$${entry.unit_price_avg.toLocaleString()}</span>
      <span class="stat-label">Unit Price</span>
    </div>
    <div class="stat">
      <span class="stat-value">$${entry.effective_cost.toLocaleString()}</span>
      <span class="stat-label">True Cost (TCO)</span>
    </div>
    <div class="stat">
      <span class="stat-value">${entry.on_time_pct}%</span>
      <span class="stat-label">On-Time</span>
    </div>
    <div class="stat">
      <span class="stat-value">${entry.rejection_pct}%</span>
      <span class="stat-label">Rejection Rate</span>
    </div>
    <div class="stat">
      <span class="stat-value">${entry.total_orders}</span>
      <span class="stat-label">Orders</span>
    </div>
  `;
}

// --- Chat ---
chatBtn.addEventListener("click", sendChat);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat();
});

async function sendChat() {
  const text = chatInput.value.trim();
  if (!text) return;

  appendMsg("user", text);
  chatInput.value = "";
  chatBtn.disabled = true;

  chatHistory.push({ role: "user", content: text });

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: chatHistory.slice(0, -1),
        recommendation: lastRecommendation,
      }),
    });

    const data = await res.json();
    if (data.error) {
      appendMsg("assistant", "Error: " + data.error);
    } else {
      appendMsg("assistant", data.reply);
      chatHistory.push({ role: "assistant", content: data.reply });
    }
  } catch (e) {
    appendMsg("assistant", "Failed to connect to server.");
  } finally {
    chatBtn.disabled = false;
    chatInput.focus();
  }
}

function appendMsg(role, text) {
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

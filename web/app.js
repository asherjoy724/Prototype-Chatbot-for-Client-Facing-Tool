const state = {
  template: null,
  currentFieldId: null,
  currentSectionId: null,
  suggestions: [
    { label: "Company Information", message: "What goes in the Company Information section?" },
    { label: "Marketing Design", message: "What goes in the Marketing Design section?" },
    { label: "Role Design", message: "What goes in the Role Design section?" }
  ],
  sessionId: loadSessionId()
};

const chatLogEl = document.getElementById("chat-log");
const chatFormEl = document.getElementById("chat-form");
const suggestionBarEl = document.getElementById("suggestion-bar");
const welcomeTitleEl = document.getElementById("welcome-title");
const welcomeMessageEl = document.getElementById("welcome-message");
const assistantStatusEl = document.getElementById("assistant-status");
const messageInputEl = document.getElementById("message");
const sendButtonEl = chatFormEl.querySelector(".send-button");

bootstrap();

messageInputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (!messageInputEl.disabled) {
      chatFormEl.requestSubmit();
    }
  }
});

async function bootstrap() {
  renderSuggestions(state.suggestions);
  welcomeTitleEl.textContent = "How can I help you?";
  welcomeMessageEl.textContent = "";
  assistantStatusEl.textContent = "";

  try {
    const [templateResponse, bootstrapResponse] = await Promise.all([
      fetch("/api/template/client-intake-v1/schema"),
      fetch("/api/assistant/bootstrap")
    ]);

    state.template = await templateResponse.json();
    const assistant = await bootstrapResponse.json();
    assistantStatusEl.dataset.mode = assistant.assistant_mode || "";
  } catch (error) {
    console.error("Assistant bootstrap failed", error);
  }
}

chatFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(chatFormEl);
  const message = String(formData.get("message") || "").trim();

  if (!message) {
    return;
  }

  appendMessage("user", message);

  if (!state.template?.template_id) {
    appendMessage("assistant", {
      answer: "I’m not ready yet. Please refresh the page and try again.",
      title: "",
      supporting_points: [],
      checklist: [],
      related_fields: [],
      related_sections: [],
      citations: []
    });
    return;
  }

  const thinkingIndicator = appendThinkingIndicator();
  setComposerPending(true);

  try {
    const response = await fetch("/api/chat/message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        template_id: state.template.template_id,
        current_field_id: state.currentFieldId,
        current_section_id: state.currentSectionId,
        message,
        session_id: state.sessionId
      })
    });

    const payload = await response.json();
    state.sessionId = payload.session_id || state.sessionId;
    state.currentFieldId = payload.matched_context?.field_id || null;
    state.currentSectionId = payload.matched_context?.section_id || null;
    removeThinkingIndicator(thinkingIndicator);
    appendMessage("assistant", payload);
    chatFormEl.reset();
    messageInputEl.focus();
  } catch (error) {
    console.error("Assistant response failed", error);
    removeThinkingIndicator(thinkingIndicator);
    appendMessage("assistant", {
      answer: "I’m having trouble responding right now. Please try again.",
      title: "",
      supporting_points: [],
      checklist: [],
      related_fields: [],
      related_sections: [],
      citations: []
    });
  } finally {
    setComposerPending(false);
  }
});

function appendMessage(role, payload, citations = []) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  if (role === "user") {
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = payload;
    article.appendChild(bubble);
  } else {
    article.appendChild(buildAssistantCard(payload));
  }

  chatLogEl.appendChild(article);
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
}

function buildAssistantCard(payload) {
  const wrapper = document.createElement("div");
  wrapper.className = "assistant-card";

  const answer = document.createElement("p");
  answer.className = "bubble assistant-bubble";
  answer.textContent = payload.answer;
  wrapper.appendChild(answer);

  return wrapper;
}

function appendThinkingIndicator() {
  const article = document.createElement("article");
  article.className = "message assistant thinking-message";

  const bubble = document.createElement("div");
  bubble.className = "bubble assistant-bubble typing-bubble";
  bubble.setAttribute("aria-label", "LeadBot is typing");

  for (let index = 0; index < 3; index += 1) {
    const dot = document.createElement("span");
    dot.className = "typing-dot";
    dot.style.animationDelay = `${index * 0.18}s`;
    bubble.appendChild(dot);
  }

  article.appendChild(bubble);
  chatLogEl.appendChild(article);
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
  return article;
}

function removeThinkingIndicator(node) {
  if (node?.parentNode) {
    node.parentNode.removeChild(node);
  }
}

function setComposerPending(isPending) {
  messageInputEl.disabled = isPending;
  sendButtonEl.disabled = isPending;
}

function renderSuggestions(suggestions) {
  suggestionBarEl.innerHTML = "";
  suggestions.forEach((suggestion) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "suggestion-pill";
    button.textContent = suggestion.label;
    button.addEventListener("click", () => {
      messageInputEl.value = suggestion.message;
      messageInputEl.focus();
    });
    suggestionBarEl.appendChild(button);
  });
}

function loadSessionId() {
  const storageKey = "template-assistant-session-id";
  const existing = window.localStorage.getItem(storageKey);
  if (existing) {
    return existing;
  }

  const created = window.crypto.randomUUID();
  window.localStorage.setItem(storageKey, created);
  return created;
}

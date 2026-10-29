/**
 * FoodRescue AI - Main Client Interactions
 */

document.addEventListener('DOMContentLoaded', function () {
  // Notification mark as read
  const notifDropdown = document.getElementById('notificationDropdown');
  if (notifDropdown) {
    notifDropdown.addEventListener('show.bs.dropdown', function () {
      fetch('/api/notifications/mark-read', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      }).then(res => res.json())
        .then(data => {
          const badge = document.getElementById('notifBadge');
          if (badge) badge.style.display = 'none';
        }).catch(err => console.log('Notification mark read error:', err));
    });
  }

  // AI Assistant Chat Widget Interaction
  const aiChatForm = document.getElementById('aiChatForm');
  const aiChatInput = document.getElementById('aiChatInput');
  const aiChatMessages = document.getElementById('aiChatMessages');

  if (aiChatForm && aiChatInput && aiChatMessages) {
    aiChatForm.addEventListener('submit', function (e) {
      e.preventDefault();
      const prompt = aiChatInput.value.trim();
      if (!prompt) return;

      // Append user bubble
      const userBubble = document.createElement('div');
      userBubble.className = 'ai-chat-bubble-user text-end';
      userBubble.innerHTML = `<strong>You:</strong> ${escapeHtml(prompt)}`;
      aiChatMessages.appendChild(userBubble);
      aiChatInput.value = '';

      // Typing indicator
      const typingBubble = document.createElement('div');
      typingBubble.className = 'ai-chat-bubble-ai';
      typingBubble.id = 'aiTypingIndicator';
      typingBubble.innerHTML = '<i class="bi bi-robot me-1 text-success"></i> <em>Analyzing inventory and demand data...</em>';
      aiChatMessages.appendChild(typingBubble);
      aiChatMessages.scrollTop = aiChatMessages.scrollHeight;

      // API request
      fetch('/api/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt })
      })
      .then(res => res.json())
      .then(data => {
        const ind = document.getElementById('aiTypingIndicator');
        if (ind) ind.remove();

        const aiBubble = document.createElement('div');
        aiBubble.className = 'ai-chat-bubble-ai';
        aiBubble.innerHTML = formatMarkdown(data.response || 'No response generated.');
        aiChatMessages.appendChild(aiBubble);
        aiChatMessages.scrollTop = aiChatMessages.scrollHeight;
      })
      .catch(err => {
        const ind = document.getElementById('aiTypingIndicator');
        if (ind) ind.remove();
        const errBubble = document.createElement('div');
        errBubble.className = 'ai-chat-bubble-ai text-danger';
        errBubble.innerHTML = 'Error contacting AI assistant. Please try again.';
        aiChatMessages.appendChild(errBubble);
      });
    });
  }
});

// Quick helper to fill AI assistant prompt from suggestion buttons
function askAiPrompt(question) {
  const input = document.getElementById('aiChatInput');
  const form = document.getElementById('aiChatForm');
  if (input && form) {
    input.value = question;
    form.dispatchEvent(new Event('submit'));
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.innerText = text;
  return div.innerHTML;
}

function formatMarkdown(text) {
  // Simple clean markdown parser for bold, lists, and linebreaks
  let html = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n- /g, '<br>• ')
    .replace(/\n/g, '<br>');
  return html;
}

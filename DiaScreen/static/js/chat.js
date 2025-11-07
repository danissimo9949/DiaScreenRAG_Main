let currentSessionId = null;
    function getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    function autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    }

    function handleKeyDown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage(event);
        }
    }

    async function createNewChat() {
        try {
            document.querySelectorAll('.history-item').forEach(item => {
                item.classList.remove('active');
            });

            document.getElementById('chatMessages').innerHTML = `
                <div class="empty-chat text-center text-muted d-flex flex-column align-items-center justify-content-center h-100" id="emptyChat">
                    <h6 class="mb-2">Новий діалог</h6>
                    <p class="mb-0">Почніть розмову, задавши питання</p>
                </div>
            `;

            const response = await fetch('/chatAI/api/create-session/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();
            if (data.success) {
                currentSessionId = data.session_id;
                loadSessions();
            }
        } catch (error) {
            console.error('Помилка при створенні діалогу:', error);
        }
    }

    async function loadChat(sessionId) {
        try {
            document.querySelectorAll('.history-item').forEach(item => {
                item.classList.remove('active');
            });

            const item = document.querySelector(`[data-session-id="${sessionId}"]`);
            if (item) {
                item.classList.add('active');
            }

            currentSessionId = sessionId;

            const response = await fetch(`/chatAI/api/sessions/${sessionId}/messages/`);
            const data = await response.json();

            if (data.success) {
                const messagesContainer = document.getElementById('chatMessages');
                messagesContainer.innerHTML = '';

                if (data.messages.length === 0) {
                    messagesContainer.innerHTML = `
                        <div class="empty-chat text-center text-muted d-flex flex-column align-items-center justify-content-center h-100">
                            <h6 class="mb-2">Новий діалог</h6>
                            <p class="mb-0">Почніть розмову, задавши питання</p>
                        </div>
                    `;
                } else {
                    data.messages.forEach(msg => {
                        addMessageToUI(msg.message_text, msg.sender, msg.created_at, msg.status);
                    });
                }
            }
        } catch (error) {
            console.error('Помилка при завантаженні діалогу:', error);
        }
    }

    async function loadSessions() {
        try {
            const response = await fetch('/chatAI/api/sessions/');
            const data = await response.json();

            if (data.success) {
                const historyList = document.getElementById('historyList');
                historyList.innerHTML = '';

                if (data.sessions.length === 0) {
                    historyList.innerHTML = `
                        <div class="empty-chat text-center text-muted py-5">
                            <p class="mb-0">Немає історії діалогів</p>
                        </div>
                    `;
                } else {
                    data.sessions.forEach(session => {
                        const item = document.createElement('div');
                        item.className = 'history-item list-group-item list-group-item-action border-0 border-bottom';
                        item.setAttribute('data-session-id', session.session_id);
                        item.innerHTML = `
                            <div class="d-flex justify-content-between align-items-start gap-2">
                                <div class="flex-grow-1" role="button" onclick="loadChat('${session.session_id}')">
                                    <div class="history-item-title text-truncate">${escapeHtml(session.summary || 'Новий діалог')}</div>
                                    <div class="history-item-date small text-muted">${session.updated_at}</div>
                                </div>
                                <div class="history-item-actions d-flex align-items-center gap-2">
                                    <button class="btn btn-outline-danger btn-sm d-inline-flex align-items-center gap-1" onclick="event.stopPropagation(); deleteChat('${session.session_id}')" title="Видалити діалог">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                                            <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
                                            <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                                        </svg>
                                        Видалити
                                    </button>
                                </div>
                            </div>
                        `;
                        historyList.appendChild(item);
                    });
                }
            }
        } catch (error) {
            console.error('Помилка при завантаженні списку сесій:', error);
        }
    }

    async function sendMessage(event) {
        event.preventDefault();

        const input = document.getElementById('messageInput');
        const message = input.value.trim();

        if (!message) {
            return;
        }

        if (!currentSessionId) {
            await createNewChat();
        }

        const emptyChat = document.getElementById('emptyChat');
        if (emptyChat) {
            emptyChat.remove();
        }

        addMessageToUI(message, 'user', getCurrentTime());
        input.value = '';
        input.style.height = 'auto';

        showTypingIndicator();

        try {
            const response = await fetch('/chatAI/api/send-message/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: currentSessionId
                })
            });

            const data = await response.json();

            if (data.success) {
                currentSessionId = data.session_id;
                hideTypingIndicator();

                addMessageToUI(
                    'Це приклад відповіді від ШІ-асистента. Після підключення бэкенду тут будуть реальні відповіді на ваші питання про діабет та управління хворобою.',
                    'assistant',
                    getCurrentTime(),
                    'completed'
                );

                loadSessions();
            } else {
                hideTypingIndicator();
                alert('Помилка: ' + (data.error || 'Невідома помилка'));
            }
        } catch (error) {
            hideTypingIndicator();
            console.error('Помилка при відправці повідомлення:', error);
            alert('Помилка при відправці повідомлення');
        }
    }

    function addMessageToUI(text, sender, time, status = 'completed') {
        const messagesContainer = document.getElementById('chatMessages');

        const messageDiv = document.createElement('div');
        const isUser = sender === 'user';
        messageDiv.className = `message ${sender} d-flex gap-3 align-items-start ${isUser ? 'flex-row-reverse text-end' : ''}`;

        const avatarContent = isUser
            ? `<span class="text-uppercase">${getUserInitial()}</span>`
            : '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="white" viewBox="0 0 16 16"><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/><path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/></svg>';

        const messageBodyClasses = isUser
            ? 'message-body rounded-3 px-3 py-2 bg-primary text-white shadow-sm'
            : 'message-body rounded-3 border px-3 py-2 bg-light';

        messageDiv.innerHTML = `
            <div class="message-avatar rounded-circle d-flex align-items-center justify-content-center fw-semibold ${isUser ? 'bg-primary text-white' : 'bg-success text-white'}">
                ${avatarContent}
            </div>
            <div class="${messageBodyClasses}">
                <div>${formatMessage(text)}</div>
                <div class="message-time">${time}</div>
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const messagesContainer = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant d-flex gap-3 align-items-start';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="message-avatar rounded-circle d-flex align-items-center justify-content-center bg-success text-white">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="white" viewBox="0 0 16 16">
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                    <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
                </svg>
            </div>
            <div class="message-body rounded-3 border px-3 py-2 bg-light">
                <div class="d-flex gap-1">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        scrollToBottom();
    }

    function hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    function scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function formatMessage(text) {
        return escapeHtml(text).replace(/\n/g, '<br>');
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    function getCurrentTime() {
        const now = new Date();
        return now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    }

    function getUserInitial() {
        return 'В';
    }

    async function deleteChat(sessionId) {
        if (!confirm('Ви впевнені, що хочете видалити цей діалог?')) {
            return;
        }

        try {
            const response = await fetch(`/chatAI/api/sessions/${sessionId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();

            if (data.success) {
                if (currentSessionId == sessionId) {
                    currentSessionId = null;
                    document.getElementById('chatMessages').innerHTML = `
                        <div class="empty-chat text-center text-muted d-flex flex-column align-items-center justify-content-center h-100" id="emptyChat">
                            <h6 class="mb-2">Оберіть діалог з історії або створіть новий</h6>
                            <p class="mb-0">Я ваш помічник у питаннях управління діабетом</p>
                        </div>
                    `;
                }

                document.querySelectorAll('.history-item').forEach(item => {
                    item.classList.remove('active');
                });

                loadSessions();
            } else {
                alert('Помилка: ' + (data.error || 'Невідома помилка'));
            }
        } catch (error) {
            console.error('Помилка при видаленні діалогу:', error);
            alert('Помилка при видаленні діалогу');
        }
    }

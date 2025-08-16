document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const navToggle = document.getElementById('nav-toggle');
    const headerNav = document.getElementById('header-nav');
    const scrollBottomBtn = document.getElementById('scroll-bottom');
    const suggestionsElements = document.querySelectorAll('.dynamic-suggestion');

    function isScrolledToBottom() {
        return chatMessages.scrollHeight - chatMessages.clientHeight <= chatMessages.scrollTop + 10;
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function updateScrollButtonVisibility() {
        if (!isScrolledToBottom()) {
            scrollBottomBtn.classList.add('visible');
        } else {
            scrollBottomBtn.classList.remove('visible');
        }
    }

    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;

        const messageText = document.createElement('p');
        messageText.innerHTML = message.replace(/\n/g, '<br>');
        messageDiv.appendChild(messageText);

        chatMessages.appendChild(messageDiv);

        if (isScrolledToBottom()) {
            scrollToBottom();
        }

        updateScrollButtonVisibility();
    }

    function showTypingIndicator() {
        removeTypingIndicator();

        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typing-indicator';

        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'typing-dot';
            typingDiv.appendChild(dot);
        }

        chatMessages.appendChild(typingDiv);

        if (isScrolledToBottom()) {
            scrollToBottom();
        }
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    function handleSuggestionClick(text) {
        userInput.value = text;
        sendMessage();
    }

    function sendMessage() {
        const message = userInput.value.trim();

        if (!message) return;

        addMessage(message, true);
        userInput.value = '';

        showTypingIndicator();

        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            removeTypingIndicator();

            if (data.error) {
                addMessage("Sorry, there was an error processing your request. Please try again.", false);
                return;
            }

            addMessage(data.response, false);

            if (data.suggestions && data.suggestions.length > 0) {
                displaySuggestions(data.suggestions);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            removeTypingIndicator();
            addMessage("Sorry, there was an error connecting to the server. Please try again later.", false);
        });
    }

    function displaySuggestions(suggestions) {
        const oldSuggestions = document.querySelectorAll('.dynamic-suggestion');
        oldSuggestions.forEach(suggestion => suggestion.remove());

        suggestions.forEach(text => {
            const suggestionEl = document.createElement('div');
            suggestionEl.className = 'dynamic-suggestion';
            suggestionEl.innerText = text;
            suggestionEl.dataset.suggestion = text;
            suggestionEl.addEventListener('click', () => handleSuggestionClick(text));
            chatMessages.appendChild(suggestionEl);
        });

        if (isScrolledToBottom()) {
            scrollToBottom();
        }

        updateScrollButtonVisibility();
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }

    if (userInput) {
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        userInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';

            if (this.value === '') {
                this.style.height = '';
            }
        });
    }

    if (navToggle) {
        navToggle.addEventListener('click', () => {
            headerNav.classList.toggle('active');
        });
    }

    if (scrollBottomBtn) {
        scrollBottomBtn.addEventListener('click', scrollToBottom);
    }

    if (chatMessages) {
        chatMessages.addEventListener('scroll', updateScrollButtonVisibility);
    }

    suggestionsElements.forEach(suggestion => {
        suggestion.addEventListener('click', () => {
            const text = suggestion.dataset.suggestion;
            handleSuggestionClick(text);
        });
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            if (headerNav) headerNav.classList.remove('active');
        }
    });

    updateScrollButtonVisibility();
    scrollToBottom();
});
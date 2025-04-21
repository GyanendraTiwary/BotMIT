// Main chat functionality
const form = document.getElementById("chat-form");
const typingIndicator = document.getElementById("typing-indicator");
const typingText = document.getElementById("typing-text");
const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user_input");
const clearChatButton = document.getElementById("clear-chat-btn");

// Store original placeholder text
const originalPlaceholder = userInput.placeholder;

let typingInterval;

// Add event listener for clear chat button
clearChatButton.addEventListener("click", async function() {
  try {
    const response = await fetch(clearChatEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      }
    });
    
    if (response.ok) {
      // Clear chat box on successful response
      chatBox.innerHTML = "";
      // Optional: Add a system message indicating the chat was cleared
      addMessage("Chat history has been cleared. How can I help you today?", "bot");
    } else {
      console.error("Failed to clear chat history");
    }
  } catch (error) {
    console.error("Error clearing chat:", error);
  }
});

form.addEventListener("submit", async function (e) {
  e.preventDefault();

  const userMessage = userInput.value.trim();
  if (userMessage === "") return;

  // Add user message immediately
  addMessage(userMessage, "user");

  // Clear input
  userInput.value = "";

  // Show typing indicator
  typingIndicator.classList.remove("hidden");
  startTypingAnimation();
  typingIndicator.scrollIntoView({ behavior: "smooth" });

  // Send request to server
  try {
    const response = await fetch(chatEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ user_input: userMessage }),
    });

    const data = await response.json();
    stopTypingAnimation();
    typingIndicator.classList.add("hidden");

    if (data.bot_response) {
      addMessage(data.bot_response, "bot");
    } else {
      addMessage("Error: No response from server", "bot");
    }
  } catch (error) {
    console.error(error);
    stopTypingAnimation();
    typingIndicator.classList.add("hidden");
    addMessage("Error: Could not connect to server", "bot");
  }
});

function startTypingAnimation() {
  let dots = "";
  typingInterval = setInterval(() => {
    dots = dots.length < 3 ? dots + "." : "";
    typingText.textContent = `BotMIT is typing${dots}`;
  }, 400);
}

function stopTypingAnimation() {
  clearInterval(typingInterval);
  typingText.textContent = "BotMIT is typing";
}

function addMessage(text, sender) {
  const messageDiv = document.createElement("div");
  messageDiv.className = sender === "user" ? "text-right" : "text-left";

  const innerDiv = document.createElement("div");
  innerDiv.className =
    sender === "user"
      ? "inline-block bg-blue-500 text-white px-5 py-3 rounded-2xl"
      : "inline-block bg-gray-300 text-gray-800 px-5 py-3 rounded-2xl";

  innerDiv.textContent = text;
  messageDiv.appendChild(innerDiv);
  chatBox.appendChild(messageDiv);

  // Scroll to bottom smoothly
  messageDiv.scrollIntoView({ behavior: "smooth" });
}

// Speech recognition functionality
const micButton = document.getElementById("mic-button");
let recognition;

// Check if browser supports speech recognition
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  // Create speech recognition instance
  recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US'; // Set language
  
  // Handle speech recognition results
  recognition.onresult = function(event) {
    const transcript = event.results[0][0].transcript;
    userInput.value = transcript;
    micButton.classList.remove('bg-red-500');
    micButton.classList.add('bg-gray-200');
    // Reset placeholder to original
    userInput.placeholder = originalPlaceholder;
  };
  
  // Handle errors
  recognition.onerror = function(event) {
    console.error('Speech recognition error:', event.error);
    micButton.classList.remove('bg-red-500');
    micButton.classList.add('bg-gray-200');
    // Reset placeholder to original
    userInput.placeholder = originalPlaceholder;
  };
  
  // When speech recognition ends
  recognition.onend = function() {
    micButton.classList.remove('bg-red-500');
    micButton.classList.add('bg-gray-200');
    // Reset placeholder to original
    userInput.placeholder = originalPlaceholder;
  };
  
  // Toggle speech recognition on mic button click
  micButton.addEventListener('click', function() {
    if (recognition) {
      if (micButton.classList.contains('bg-red-500')) {
        // Currently recording, so stop
        recognition.stop();
        // Reset placeholder to original
        userInput.placeholder = originalPlaceholder;
      } else {
        // Start recording
        try {
          recognition.start();
          micButton.classList.remove('bg-gray-200');
          micButton.classList.add('bg-red-500');
          // Change placeholder to indicate listening
          userInput.placeholder = "Listening...";
        } catch (e) {
          console.error('Speech recognition error:', e);
        }
      }
    } else {
      alert('Speech recognition is not supported in your browser. Please try Chrome or Edge.');
    }
  });
} else {
  // Speech recognition not supported
  micButton.addEventListener('click', function() {
    alert('Speech recognition is not supported in your browser. Please try Chrome or Edge.');
  });
}
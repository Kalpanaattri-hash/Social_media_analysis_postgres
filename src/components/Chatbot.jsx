import React, { useState, useRef, useEffect } from 'react';

// Backend URL (Vite): set VITE_BACKEND_URL in .env if needed
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

// --- Icon Components (inlined for simplicity) ---
const ChatIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
    </svg>
);

const CloseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);


const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! How can I help you analyze your reviews data today?' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatHistoryRef = useRef(null);

  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userMessage = { role: 'user', content: inputValue };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
  const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: inputValue, selected_table: 'processed_product_reviews2' }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const assistantMessage = { role: 'assistant', content: data.reply };
      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error("Failed to send message:", error);
      const errorMessage = { role: 'assistant', content: 'Sorry, I am having trouble connecting to the server.' };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* --- Floating Action Button (FAB) --- */}
      {/* POSITION UPDATE: Changed from bottom-8 right-8 */}
      {!isOpen && (
        <div className="fixed bottom-6 right-6 z-50">
          <button
            onClick={() => setIsOpen(true)}
            className="bg-blue-700 text-white rounded-full w-16 h-16 flex items-center justify-center shadow-lg hover:bg-blue-800 transition-transform transform hover:scale-110"
            aria-label="Open chat"
          >
            <ChatIcon />
          </button>
        </div>
      )}

      {/* --- Chat Widget --- */}
      {/* POSITION UPDATE: Changed from bottom-8 right-8 */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-[400px] max-w-[90vw] h-[600px] bg-gray-800 text-white rounded-lg shadow-2xl flex flex-col">
          {/* Header */}
          <div className="bg-gray-900 p-4 rounded-t-lg flex justify-between items-center">
            <h3 className="font-bold text-lg">Chat with Reviews Assistant</h3>
            <button onClick={() => setIsOpen(false)} aria-label="Close chat" className="hover:text-gray-400">
              <CloseIcon />
            </button>
          </div>

          {/* Message History */}
          <div ref={chatHistoryRef} className="flex-1 p-4 overflow-y-auto bg-gray-800">
            {messages.map((msg, index) => (
              <div key={index} className={`my-2 flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`inline-block p-3 rounded-xl max-w-xs ${
                    msg.role === 'user'
                      ? 'bg-blue-600'
                      : 'bg-gray-700'
                  }`}
                >
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="my-2 flex justify-start">
                 <div className="inline-block p-3 rounded-xl bg-gray-700">
                    <p className="whitespace-pre-wrap text-sm">Thinking...</p>
                 </div>
              </div>
            )}
          </div>

          {/* Input Form */}
          <div className="p-4 border-t border-gray-700">
            <form onSubmit={handleSendMessage} className="flex items-center space-x-3">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Type your question..."
                className="flex-1 p-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                disabled={isLoading}
              />
              <button
                type="submit"
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-500"
                disabled={isLoading || !inputValue.trim()}
                aria-label="Send message"
              >
                Send
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

export default Chatbot;


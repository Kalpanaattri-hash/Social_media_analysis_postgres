import React, { useState, useRef, useEffect } from 'react';

// --- Icon Components ---
const ChatIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="28"
    height="28"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
  </svg>
);

// --- Chatbot Component ---
const Chatbot = () => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      resultsHtml: null,
      insights:
        'Hi! I am connected to your Vercel Postgres database. Ask me about internal reviews, complaints, trends, or even Amazon Reviews!',
      isInsightVisible: true,
      isResultExpanded: false,
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatHistoryRef = useRef(null);

  const TRUNCATE_THRESHOLD_LENGTH = 500;
  const TRUNCATE_MAX_HEIGHT = '300px';

  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages]);

  // --- RESTORED: Function to split text into Analysis vs Questions ---
  const parseInsights = (content) => {
    if (!content) return { mainInsight: '', questions: [] };
    // We split by the specific marker used in the backend prompt
    const parts = content.split('**Suggested Questions:**');
    const mainInsight = parts[0].trim();
    const questions =
      parts.length > 1
        ? parts[1]
            .split('\n')
            .map((q) => q.replace(/^[*\-]\s*/, '').trim()) // Remove bullets
            .filter(Boolean)
        : [];
    return { mainInsight, questions };
  };

  const sendMessageToServer = async (messageText) => {
    if (!messageText.trim()) return;
    const userMessage = { role: 'user', content: messageText };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: messageText }),
      });
      
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const data = await response.json();
      
      const newAssistantMessage = {
        role: 'assistant',
        resultsHtml: data.results_html,
        insights: data.error ? `Error: ${data.error}` : data.insights,
        isInsightVisible: !!data.error, // Show immediately if error
        isResultExpanded: false,
      };
      setMessages((prev) => [...prev, newAssistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          insights: 'Sorry, I am having trouble connecting to the server.',
          isInsightVisible: true,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    sendMessageToServer(inputValue);
  };

  // Handler for clicking a suggested question button
  const handleSuggestedQuestionClick = (question) => {
    sendMessageToServer(question);
  };

  const toggleInsightVisibility = (messageIndex) => {
    setMessages((prevMessages) =>
      prevMessages.map((msg, index) =>
        index === messageIndex
          ? { ...msg, isInsightVisible: !msg.isInsightVisible }
          : msg
      )
    );
  };

  const toggleResultExpanded = (messageIndex) => {
    setMessages((prevMessages) =>
      prevMessages.map((msg, index) =>
        index === messageIndex
          ? { ...msg, isResultExpanded: !msg.isResultExpanded }
          : msg
      )
    );
  };

  return (
    <div
      style={{
        backgroundColor: '#1F2937',
        color: 'white',
        borderRadius: '0.5rem',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
        height: '75vh',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Chat History */}
      <div
        ref={chatHistoryRef}
        style={{ flex: 1, padding: '1rem', overflowY: 'auto' }}
      >
        {messages.map((msg, index) => {
          const isResultLong =
            msg.resultsHtml &&
            msg.resultsHtml.length > TRUNCATE_THRESHOLD_LENGTH;
          const isResultTruncated = isResultLong && !msg.isResultExpanded;

          // Parse the insights to separate text from questions
          const { mainInsight, questions } =
             msg.role === 'assistant'
               ? parseInsights(msg.insights)
               : { mainInsight: '', questions: [] };

          return (
            <div
              key={index}
              style={{
                margin: '0.5rem 0',
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <div
                style={{
                  display: 'inline-block',
                  padding: '0.75rem',
                  borderRadius: '0.75rem',
                  maxWidth: '90%',
                  backgroundColor: msg.role === 'user' ? '#2563EB' : '#374151',
                  fontSize: '0.875rem',
                  wordBreak: 'break-word',
                }}
              >
                {msg.role === 'user' ? (
                  <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                ) : (
                  <div>
                    {msg.resultsHtml && (
                      <>
                        <div
                          style={{
                            maxHeight: isResultTruncated
                              ? TRUNCATE_MAX_HEIGHT
                              : 'none',
                            overflow: 'hidden',
                            position: 'relative',
                            transition: 'max-height 0.3s ease-in-out',
                          }}
                        >
                          <div dangerouslySetInnerHTML={{ __html: msg.resultsHtml }} />
                          {isResultTruncated && (
                            <div
                              style={{
                                position: 'absolute',
                                bottom: 0,
                                left: 0,
                                right: 0,
                                height: '50px',
                                background: 'linear-gradient(to top, #374151, transparent)',
                              }}
                            />
                          )}
                        </div>
                        {isResultLong && (
                          <button
                            onClick={() => toggleResultExpanded(index)}
                            style={{
                              background: '#4B5563',
                              color: 'white',
                              border: 'none',
                              borderRadius: '0.375rem',
                              padding: '0.375rem 0.75rem',
                              marginTop: '0.75rem',
                              cursor: 'pointer',
                              fontWeight: '600',
                            }}
                          >
                            {msg.isResultExpanded ? 'Show Less' : 'Show More'}
                          </button>
                        )}
                      </>
                    )}

                    {/* SHOW INSIGHTS BUTTON (Only if table exists) */}
                    {msg.resultsHtml && mainInsight && (
                      <button
                        onClick={() => toggleInsightVisibility(index)}
                        style={{
                          background: '#4B5563',
                          color: 'white',
                          border: 'none',
                          borderRadius: '0.375rem',
                          padding: '0.375rem 0.75rem',
                          marginTop: '0.75rem',
                          cursor: 'pointer',
                          fontWeight: '600',
                          marginLeft: isResultLong ? '0.5rem' : '0',
                        }}
                      >
                        {msg.isInsightVisible ? 'Hide' : 'Show'} Insights
                      </button>
                    )}

                    {/* ANALYSIS CONTENT */}
                    <div style={{ marginTop: '0.75rem' }}>
                        
                        {/* 1. Analysis Text: Show if NO table OR if toggled ON */}
                        {(!msg.resultsHtml || msg.isInsightVisible) && mainInsight && (
                            <p style={{ whiteSpace: 'pre-wrap' }}>{mainInsight}</p>
                        )}

                        {/* 2. Suggested Questions: ALWAYS Show if they exist */}
                        {questions.length > 0 && (
                            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                <p style={{ fontWeight: 'bold', color: '#9CA3AF', fontSize: '0.8rem' }}>Suggested Questions:</p>
                                {questions.map((q, idx) => (
                                    <button 
                                        key={idx}
                                        onClick={() => handleSuggestedQuestionClick(q)}
                                        style={{
                                            background: 'transparent',
                                            border: '1px solid #4B5563',
                                            borderRadius: '0.375rem',
                                            color: '#D1D5DB',
                                            padding: '0.5rem',
                                            textAlign: 'left',
                                            cursor: 'pointer',
                                            fontSize: '0.8rem',
                                            transition: 'background 0.2s'
                                        }}
                                        onMouseOver={(e) => e.target.style.background = '#4B5563'}
                                        onMouseOut={(e) => e.target.style.background = 'transparent'}
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                  </div>
                )}
              </div>
            </div>
          );
        })}
        {isLoading && (
          <div style={{ margin: '0.5rem 0', display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{ padding: '0.75rem', borderRadius: '0.75rem', backgroundColor: '#374151' }}>
              <p style={{ fontSize: '0.875rem' }}>Thinking...</p>
            </div>
          </div>
        )}
      </div>

      {/* Input Form */}
      <div style={{ padding: '1rem', borderTop: '1px solid #374151' }}>
        <form onSubmit={handleFormSubmit} style={{ display: 'flex', gap: '0.75rem' }}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask a question about reviews..."
            style={{
              flex: 1,
              padding: '0.5rem',
              backgroundColor: '#374151',
              border: '1px solid #4B5563',
              borderRadius: '0.5rem',
              color: 'white',
              outline: 'none',
            }}
            disabled={isLoading}
          />
          <button
            type="submit"
            style={{
              backgroundColor: '#2563EB',
              color: 'white',
              padding: '0.5rem 1rem',
              borderRadius: '0.5rem',
              cursor: isLoading || !inputValue.trim() ? 'not-allowed' : 'pointer',
              opacity: isLoading || !inputValue.trim() ? 0.5 : 1,
              border: 'none',
            }}
            disabled={isLoading || !inputValue.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

// --- Dashboard Page Component (Unchanged) ---
const DashboardPage = ({ title, icon, iframeSrc, pageKey }) => {
  const [isInsightVisible, setIsInsightVisible] = useState(false);
  const [insightData, setInsightData] = useState(null);
  const [isInsightLoading, setIsInsightLoading] = useState(false);
  const [insightError, setInsightError] = useState(null);

  useEffect(() => {
    setIsInsightVisible(false);
    setInsightData(null);
    setInsightError(null);
  }, [pageKey]);

  const INSIGHT_ENDPOINTS = {
    complaints: '/api/get-complaint-insights',
    social: '/api/get-social-insights',
    trends: '/api/get-trend-insights',
  };

  const endpoint = INSIGHT_ENDPOINTS[pageKey];

  const handleShowInsights = async () => {
    if (isInsightVisible) {
      setIsInsightVisible(false);
      return;
    }

    if (!endpoint) {
        setInsightError("Insights not available for this page yet.");
        setIsInsightVisible(true);
        return;
    }

    setIsInsightVisible(true);
    setIsInsightLoading(true);
    setInsightError(null);
    setInsightData(null);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page_key: pageKey }),
      });

      if (!response.ok) throw new Error(`Error: ${response.status} ${response.statusText}`);

      const data = await response.json();
      if (data.error) {
        setInsightError(data.error);
      } else {
        setInsightData(data.insights);
      }
    } catch (err) {
      setInsightError('Could not connect to server.');
    } finally {
      setIsInsightLoading(false);
    }
  };

  return (
    <div style={{ color: '#D1D5DB' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: 'white', display: 'flex', alignItems: 'center' }}>
          <span style={{ fontSize: '1.5rem', marginRight: '0.75rem' }}>{icon}</span> {title}
        </h2>
      </div>

      <div style={{ backgroundColor: '#1F2937', borderRadius: '0.5rem', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', height: '80vh' }}>
        <iframe title={title} width="100%" height="100%" src={iframeSrc} frameBorder="0" style={{ border: 0, borderRadius: '8px' }} allowFullScreen />
      </div>

      {endpoint && (
        <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
          <button
            onClick={handleShowInsights}
            disabled={isInsightLoading}
            style={{
              backgroundColor: '#2563EB',
              color: 'white',
              padding: '0.75rem 1.5rem',
              borderRadius: '0.5rem',
              cursor: isInsightLoading ? 'not-allowed' : 'pointer',
              opacity: isInsightLoading ? 0.7 : 1,
              border: 'none',
              fontWeight: '600',
              fontSize: '1rem',
            }}
          >
            {isInsightLoading ? 'Generating...' : isInsightVisible ? 'Hide Insights' : 'Show Insights'}
          </button>
        </div>
      )}

      {isInsightVisible && (
        <div style={{ backgroundColor: '#1F2937', color: 'white', borderRadius: '0.5rem', padding: '1.5rem', marginTop: '1.5rem', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', borderBottom: '1px solid #374151', paddingBottom: '0.75rem' }}>
            AI Dashboard Insights
          </h3>
          <div>
            {isInsightLoading && <p style={{ textAlign: 'center', padding: '1rem' }}>Generating analysis...</p>}
            {insightError && (
              <div style={{ backgroundColor: '#B91C1C', padding: '1rem', borderRadius: '0.375rem' }}>
                <p style={{ fontWeight: 'bold' }}>Error</p>
                <p>{insightError}</p>
              </div>
            )}
            {insightData && !isInsightLoading && (
              <div
                style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}
                dangerouslySetInnerHTML={{
                  __html: insightData
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/---/g, '<hr style="border-color: #374151; margin: 1rem 0;" />')
                    .replace(/\n/g, '<br />'),
                }}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const DashboardOverview = () => (
  <div style={{ color: '#D1D5DB' }}>
    <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', marginBottom: '1rem', color: 'white', display: 'flex', alignItems: 'center' }}>
      <span style={{ fontSize: '1.5rem', marginRight: '0.75rem' }}>🏠</span> Dashboard Overview
    </h2>
    <div style={{ backgroundColor: '#1F2937', padding: '1.5rem', borderRadius: '0.5rem' }}>
      <p>Welcome to the Agent Analytics Hub (Postgres Edition). Select a dashboard from the sidebar.</p>
      <ul style={{ listStyleType: 'disc', listStylePosition: 'inside', marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <li><span style={{ fontWeight: '600' }}>Social Media:</span> Customer sentiment trends.</li>
        <li><span style={{ fontWeight: '600' }}>Complaints:</span> Deep dive into issues using Postgres data.</li>
        <li><span style={{ fontWeight: '600' }}>Trends:</span> Seasonal analysis and product feedback.</li>
      </ul>
    </div>
  </div>
);

const About = () => (
  <div style={{ color: '#D1D5DB' }}>
    <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', marginBottom: '1rem', color: 'white', display: 'flex', alignItems: 'center' }}>
      <span style={{ fontSize: '1.5rem', marginRight: '0.75rem' }}>ℹ️</span> About
    </h2>
    <div style={{ backgroundColor: '#1F2937', padding: '1.5rem', borderRadius: '0.5rem' }}>
      <p>This application analyzes customer reviews using Vercel Postgres + Gemini AI.</p>
    </div>
  </div>
);

const ChatbotPage = () => (
  <div>
    <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', marginBottom: '1rem', color: 'white', display: 'flex', alignItems: 'center' }}>
      <span style={{ fontSize: '1.5rem', marginRight: '0.75rem' }}>🤖</span> AI Assistant
    </h2>
    <Chatbot />
  </div>
);

// --- Main App Component ---
function App() {
  const [currentPage, setCurrentPage] = useState('overview');

  const renderPage = () => {
    switch (currentPage) {
      case 'social':
        return (
          <DashboardPage
            title="Social Media Analysis"
            icon="📊"
            iframeSrc="https://lookerstudio.google.com/embed/reporting/667d0c51-efa8-43c5-8c5b-8db987728029/page/WqPdF&embed_config={%22navType%22:%22LEFT%22}"
            pageKey="social"
          />
        );
      case 'complaints':
        return (
          <DashboardPage
            title="Complaint Analysis"
            icon="📋"
            iframeSrc="https://lookerstudio.google.com/embed/u/0/reporting/fb60b83c-ea69-4f1a-993c-f329fd21f366/page/tMxWF&embed_config={%22navType%22:%22LEFT%22}"
            pageKey="complaints"
          />
        );
      case 'trends':
        return (
          <DashboardPage
            title="Trend Analysis"
            icon="📉"
            iframeSrc="https://lookerstudio.google.com/embed/reporting/5f3a7544-82b0-4a6a-aa26-e5917e23c23d/page/siQdF&embed_config={%22navType%22:%22LEFT%22}"
            pageKey="trends"
          />
        );
      case 'chatbot':
        return <ChatbotPage />;
      case 'about':
        return <About />;
      default:
        return <DashboardOverview />;
    }
  };

  const NavLink = ({ page, label }) => {
    const isActive = currentPage === page;
    const linkStyle = { display: 'flex', alignItems: 'center', width: '100%', textAlign: 'left', padding: '0.625rem 1rem', borderRadius: '0.375rem', fontSize: '0.875rem', fontWeight: '500', color: isActive ? 'white' : '#9CA3AF', backgroundColor: 'transparent', border: 'none', cursor: 'pointer' };
    return (
      <button onClick={() => setCurrentPage(page)} style={linkStyle}>
        <span style={{ width: '0.5rem', height: '0.5rem', borderRadius: '9999px', marginRight: '1rem', backgroundColor: isActive ? '#EF4444' : '#6B7280' }}></span>
        {label}
      </button>
    );
  };

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#111827', color: '#D1D5DB' }}>
      {/* Sidebar */}
      <div style={{ width: '16rem', backgroundColor: 'rgba(0, 0, 0, 0.2)', padding: '1rem', display: 'flex', flexDirection: 'column' }}>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'white', marginBottom: '0.5rem', padding: '0 1rem' }}>
          Navigation
        </h1>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <NavLink page="overview" label="Dashboard Overview" />
          <NavLink page="social" label="Social Media Analysis" />
          <NavLink page="complaints" label="Complaint Analysis" />
          <NavLink page="trends" label="Trend Analysis" />
          <NavLink page="chatbot" label="Analytics Assistant" />
          <NavLink page="about" label="About" />
        </nav>
      </div>
      
      {/* Main Content */}
      <main style={{ flex: '1 1 0%', padding: '2rem', overflowY: 'auto' }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold', color: 'white' }}>
            Analytics Assistant
          </h1>
          <p style={{ color: '#9CA3AF', marginTop: '0.5rem' }}>
            Analyze customer feedback using Vercel Postgres & AI.
          </p>
        </div>
        {renderPage()}
      </main>
    </div>
  );
}

export default App;
import './App.css'
import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import 'katex/dist/katex.min.css';

// Message type for chat history
interface Message {
  role: 'user' | 'assistant';
  content: string;
  interactionId?: string;
  feedbackStatus?: 'up' | 'down' | 'neutral';
}

const API_BASE = 'http://localhost:8000';

function App() {

  const [query, setQuery] = useState<string>('');

  // Initialize from sessionStorage
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = sessionStorage.getItem('chat_history');
    return saved ? JSON.parse(saved) : [];
  });

  // Save to sessionStorage whenever messages change
  useEffect(() => {
    sessionStorage.setItem('chat_history', JSON.stringify(messages));
  }, [messages]);

  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [currentResponse, setCurrentResponse] = useState<string>('');
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);

  // Admin auth state
  const [isAdmin, setIsAdmin] = useState<boolean>(false);
  const [showLoginModal, setShowLoginModal] = useState<boolean>(false);
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [loginError, setLoginError] = useState<string>('');
  const [isLoggingIn, setIsLoggingIn] = useState<boolean>(false);

  // File upload state
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentResponse]);

  // Clear upload status after 3 seconds
  useEffect(() => {
    if (uploadStatus) {
      const timer = setTimeout(() => setUploadStatus(''), 3000);
      return () => clearTimeout(timer);
    }
  }, [uploadStatus]);

  const handleQueryChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuery(event.target.value);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleQuerySubmit();
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setQuery('');
    setCurrentResponse('');
  };

  // Admin login handler
  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) {
      setLoginError('Please enter username and password');
      return;
    }

    setIsLoggingIn(true);
    setLoginError('');

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (response.ok) {
        setIsAdmin(true);
        setShowLoginModal(false);
        setUsername('');
        setPassword('');
      } else {
        setLoginError('Invalid credentials');
      }
    } catch {
      setLoginError('Connection error');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = () => {
    setIsAdmin(false);
  };

  // File upload handler
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadStatus('');

    const reader = new FileReader();

    reader.onload = async () => {
      try {
        const result = reader.result as string;
        // More robust base64 extraction
        const base64 = result.includes(',') ? result.split(',')[1] : result;

        console.log('Attempting upload to:', `${API_BASE}/upload_file`);
        const response = await fetch(`${API_BASE}/upload_file`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_data: base64,
            filename: file.name
          })
        });

        if (response.ok) {
          setUploadStatus(`✓ ${file.name} uploaded successfully`);
        } else {
          const error = await response.json().catch(() => ({}));
          console.error('Server error response:', error);
          setUploadStatus(`✗ Server Error: ${error.detail || response.statusText}`);
        }
      } catch (err: any) {
        console.error('NETWORK OR PARSING ERROR:', err);
        setUploadStatus(`✗ Connection Error: ${err.message || 'Check console'}`);
      } finally {
        setIsUploading(false);
      }
    };

    reader.onerror = () => {
      console.error('FileReader error:', reader.error);
      setUploadStatus('✗ Failed to read file');
      setIsUploading(false);
    };



    // Use readAsDataURL to get base64 string directly and safely
    reader.readAsDataURL(file);

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFeedback = async (interactionId: string, feedback: 'up' | 'down' | 'neutral') => {
    try {
      await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interactionId, feedback })
      });

      // Update local state to show feedback was given
      setMessages(prev => prev.map(msg =>
        msg.interactionId === interactionId
          ? { ...msg, feedbackStatus: feedback }
          : msg
      ));
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  const handleQuerySubmit = () => {

    // Check if Empty, and if so do nothing
    if (!query.trim()) return;

    const userMessage = query.trim();

    // Add user message to history
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setQuery('');
    setCurrentResponse('');

    // Track accumulated response locally to avoid closure issues
    let accumulatedResponse = '';
    let currentInteractionId = '';

    // Open Websocket Instance
    const websocket = new WebSocket('ws://localhost:8000/ws/stream');
    setIsStreaming(true);

    // Websocket On Open Action
    websocket.onopen = () => {
      console.log("Websocket connection established.");
      websocket.send(JSON.stringify({ query: userMessage, history: messages }))
    };

    // ON MESSAGE HANDLER
    websocket.onmessage = (event) => {
      const data = event.data;

      if (data.startsWith('<<ID:')) {
        currentInteractionId = data.replace('<<ID:', '').replace('>>', '');
        return;
      }

      if (data == '<<END>>') {
        // Add the complete response to messages before closing
        if (accumulatedResponse) {
          setMessages(msgs => [...msgs, {
            role: 'assistant',
            content: accumulatedResponse,
            interactionId: currentInteractionId
          }]);
        }
        setCurrentResponse('');
        setIsStreaming(false);
        websocket.close();
        return;
      }
      accumulatedResponse += data;
      setCurrentResponse(accumulatedResponse);
    };

    // Websocket Error Handler
    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (accumulatedResponse) {
        setMessages(msgs => [...msgs, {
          role: 'assistant',
          content: accumulatedResponse,
          interactionId: currentInteractionId
        }]);
      }
      setCurrentResponse('');
      setIsStreaming(false);
      websocket.close();
    };

    // ON CLOSE Action
    websocket.onclose = () => {
      console.log('WebSocket connection closed.');
    };
  }

  return (
    <div className='app-container'>

      {/* Login Modal */}
      {showLoginModal && (
        <div className='modal-overlay' onClick={() => setShowLoginModal(false)}>
          <div className='modal' onClick={e => e.stopPropagation()}>
            <h2>Admin Login</h2>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleLogin()}
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleLogin()}
            />
            {loginError && <p className='error-text'>{loginError}</p>}
            <div className='modal-buttons'>
              <button onClick={() => setShowLoginModal(false)} className='cancel-btn'>Cancel</button>
              <button onClick={handleLogin} disabled={isLoggingIn} className='login-btn'>
                {isLoggingIn ? 'Logging in...' : 'Login'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className='sidebar-header'>
          <button className='new-chat-btn' onClick={handleNewChat}>
            <span className='icon'>+</span>
            <span className='text'>New chat</span>
          </button>
          <button className='toggle-sidebar-btn' onClick={() => setSidebarOpen(!sidebarOpen)}>
            <span className='icon'>☰</span>
          </button>
        </div>

        {/* Admin Upload Section */}
        {isAdmin && (
          <div className='upload-section'>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".txt,.md"
              style={{ display: 'none' }}
            />
            <button
              className='upload-btn'
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              <span className='icon'>{isUploading ? '⏳' : '📁'}</span>
              <span className='text'>{isUploading ? 'Uploading...' : 'Upload Files'}</span>
            </button>
            {uploadStatus && (
              <p className={`upload-status ${uploadStatus.startsWith('✓') ? 'success' : 'error'}`}>
                {uploadStatus}
              </p>
            )}
          </div>
        )}

        <div className='sidebar-footer'>
          {isAdmin ? (
            <div className='user-info admin' onClick={handleLogout}>
              <div className='avatar admin'>A</div>
              <span className='username'>Admin (Logout)</span>
            </div>
          ) : (
            <>
              <div className='user-info'>
                <div className='avatar'>👤</div>
                <span className='username'>Guest User</span>
              </div>
              <div className='user-info' onClick={() => setShowLoginModal(true)}>
                <div className='avatar'>🔐</div>
                <span className='username'>Admin Login</span>
              </div>
            </>
          )}
        </div>
      </aside>

      {/* Collapsed Sidebar Toggle */}
      {!sidebarOpen && (
        <button className='sidebar-open-btn' onClick={() => setSidebarOpen(true)}>
          <span>☰</span>
        </button>
      )}

      {/* Main Chat Area */}
      <main className='main-content'>
        {/* Chat Header */}
        <header className='chat-header'>
          <h1>AcadGPT</h1>
          <span className='model-badge'>Gemini-2.5-Flash</span>
        </header>

        {/* Messages Container */}
        <div className='messages-container'>
          {messages.length === 0 && !isStreaming ? (
            <div className='welcome-screen'>
              <div className='welcome-icon'>🤖</div>
              <h2>How can I help you today?</h2>
              <p>Ask me anything about your data</p>
              <div className='suggestion-cards'>
                <div className='suggestion-card' onClick={() => { setQuery('Analyze my documents'); }}>
                  <span className='card-icon'>📊</span>
                  <span>Analyze my documents</span>
                </div>
                <div className='suggestion-card' onClick={() => { setQuery('Search through files'); }}>
                  <span className='card-icon'>🔍</span>
                  <span>Search through files</span>
                </div>
                <div className='suggestion-card' onClick={() => { setQuery('Get insights from my data'); }}>
                  <span className='card-icon'>💡</span>
                  <span>Get insights</span>
                </div>
              </div>
            </div>
          ) : (
            <div className='messages'>
              {messages.map((message, index) => (
                <div key={index} className={`message ${message.role === 'user' ? 'user-message' : 'ai-message'}`}>
                  <div className={`message-avatar ${message.role === 'user' ? 'user' : 'ai'}`}>
                    {message.role === 'user' ? 'U' : '🤖'}
                  </div>
                  <div className='message-content'>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                    >
                      {message.content}
                    </ReactMarkdown>
                    {message.role === 'assistant' && message.interactionId && (
                      <div className='feedback-buttons'>
                        <button
                          className={`feedback-btn ${message.feedbackStatus === 'up' ? 'active' : ''}`}
                          onClick={() => handleFeedback(message.interactionId!, 'up')}
                          disabled={!!message.feedbackStatus}
                          title="Good response"
                        >
                          👍
                        </button>
                        <button
                          className={`feedback-btn ${message.feedbackStatus === 'neutral' ? 'active' : ''}`}
                          onClick={() => handleFeedback(message.interactionId!, 'neutral')}
                          disabled={!!message.feedbackStatus}
                          title="Neutral response"
                        >
                          😐
                        </button>
                        <button
                          className={`feedback-btn ${message.feedbackStatus === 'down' ? 'active' : ''}`}
                          onClick={() => handleFeedback(message.interactionId!, 'down')}
                          disabled={!!message.feedbackStatus}
                          title="Bad response"
                        >
                          👎
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {/* Current streaming response */}
              {isStreaming && (
                <div className='message ai-message'>
                  <div className='message-avatar ai'>🤖</div>
                  <div className="message-content">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                    >
                      {currentResponse + (isStreaming ? "|" : "")}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}

        <div className='input-area'>
          <div className='input-container'>
            <textarea
              className='message-input'
              value={query}
              onChange={handleQueryChange}
              onKeyDown={handleKeyDown}
              placeholder="Message AcadGPT..."
              rows={1}
              disabled={isStreaming}
            />
            <button
              className='send-btn'
              onClick={handleQuerySubmit}
              disabled={isStreaming || !query.trim()}
            >
              {isStreaming ? (
                <span className='loading-spinner'></span>
              ) : (
                <span className='send-icon'>↑</span>
              )}
            </button>
          </div>
          <p className='disclaimer'>AcadGPT is still in beta testing, please check important information.</p>
        </div>
      </main>
    </div>
  )
}

export default App
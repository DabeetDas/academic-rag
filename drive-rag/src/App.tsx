import './App.css'
import { useState, useRef, useEffect } from 'react'

// Message type for chat history
interface Message {
  role: 'user' | 'assistant';
  content: string;
}

function App() {

  const [query, setQuery] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [currentResponse, setCurrentResponse] = useState<string>('');
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentResponse]);

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

    // Open Websocket Instance
    const websocket = new WebSocket('ws://localhost:8000/ws/stream');
    setIsStreaming(true);

    // Websocket On Open Action
    websocket.onopen = () => {
      console.log("Websocket connection established.");
      websocket.send(JSON.stringify({ query: userMessage }))
    };

    // ON MESSAGE HANDLER
    websocket.onmessage = (event) => {
      const data = event.data;
      console.log('data: ', data);
      if (data == '<<END>>') {
        // Add the complete response to messages before closing
        if (accumulatedResponse) {
          setMessages(msgs => [...msgs, { role: 'assistant', content: accumulatedResponse }]);
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
        setMessages(msgs => [...msgs, { role: 'assistant', content: accumulatedResponse }]);
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

        <div className='sidebar-footer'>
          <div className='user-info'>
            <div className='avatar'>U</div>
            <span className='username'>User</span>
          </div>
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
          <span className='model-badge'>GPT-4</span>
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
                    <p>{message.content}</p>
                  </div>
                </div>
              ))}
              {/* Current streaming response */}
              {isStreaming && (
                <div className='message ai-message'>
                  <div className='message-avatar ai'>🤖</div>
                  <div className='message-content'>
                    <p>{currentResponse}<span className='cursor'>▊</span></p>
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
import './App.css'
import { useState } from 'react'

function App() {

  const [query,setQuery] = useState<string>('');
  const [response, setResponse] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);

  const handleQueryChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
  setQuery(event.target.value);
  };

  const handleQuerySubmit = () => {

  // Check if Empty, and if so do nothing
  if (!query.trim()) return;

  // Open Websocket Instance
  const websocket = new WebSocket('ws://localhost:8000/ws/stream');
  setIsStreaming(true);
  setResponse('');

  // Websocket On Open Action
  websocket.onopen = () => {
    console.log("Websocket connection established.");
    websocket.send(JSON.stringify({query}))
  };

  // ON MESSAGE HANDLER
  websocket.onmessage = (event) => {
    const data = event.data;
    console.log('data: ',data);
    if (data == '<<END>>'){
      websocket.close();
      setIsStreaming(false);
      return;
    }
    setResponse((prevResponse) => prevResponse + data);
  };

  // Websocket Error Handler
  websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      websocket.close();
      setIsStreaming(false);
  };

  // ON CLOSE Action
  websocket.onclose = () => {
    console.log('WebSocket connection closed.');
    setIsStreaming(false);
  };
}

  return (
   <div className='main-div'>

      <div className='header-container'>
        {/* Title */}
        <h1>Full Stack RAG</h1>

        {/* Query Input Bar */}
        <div className='query-input-bar'>
          <textarea
            className='query-textarea'
            value = {query}
            onChange={handleQueryChange}
            placeholder="Query your data here..."
            rows={5}
            cols={100}
          >
          </textarea>
          <button
            className='sumbit-btn'
            onClick={handleQuerySubmit}
            disabled = {isStreaming}
          >
            Sumbit
          </button>
        </div>
      </div>

      <div className='response-container'>
        {response}
      </div>
      
    </div>
  )
}

export default App

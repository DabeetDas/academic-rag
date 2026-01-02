import './App.css'

function App() {

  return (
   <div className='main-div'>

      <div className='header-container'>
        {/* Title */}
        <h1>Full Stack RAG</h1>

        {/* Query Input Bar */}
        <div className='query-input-bar'>
          <textarea
            className='query-textarea'
            placeholder="Query your data here..."
            rows={5}
            cols={100}
          ></textarea>
          <button
            className='sumbit-btn'
          >
            Sumbit
          </button>
        </div>
      </div>

      <div className='response-container'>
        {/* RESPONSE WILL GO HERE */}
      </div>
      
    </div>
  )
}

export default App

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

export default function ChatBot({onClose}) {

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [welcome, setWelcome] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  const chatsRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    const fetchHistory = async () => {
      const token = localStorage.getItem('token');
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL}/api/chat/history`, {
          headers: {
            'x-auth-token': token || ''
          }
        });
        console.log('History fetch status:', res.status, res.statusText);
        const data = await res.json();
        console.log('History fetch data:', data);
        if (Array.isArray(data)) {
          setMessages(data.map(msg => ({ from: msg.from, text: msg.text })));
          if (data.length > 0) {
            setWelcome(false);
          }
        }
      } catch (err) {
        console.error('Error fetching chat history:', err);
      }
    };

    fetchHistory();
  }, []);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text) return;

    if (welcome) setWelcome(false);

    const userMsg = { from: 'user', text };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setInput("");

    const token = localStorage.getItem('token');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/chat/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-auth-token': token || ''
        },
        body: JSON.stringify({ question: text })
      });
      const data = await res.json();
      const botReply = data.answer || "Sorry, I couldn't fetch a response.";
      const botMsg = { from: 'bot', text: botReply };
      setMessages(prev => [...prev, botMsg]);
    } catch (err) {
      console.error('Chat API error:', err);
      const errorMsg = { from: 'bot', text: "Oops! Something went wrong." };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);



  return (
    <div className="bot-container">
      <div className="chat-header">
        <span>AI Cooking Expert</span>
        <button className="close-chat-btn" onClick={onClose}>×</button>
      </div>

      <div className="chat-container">
        <div className="chats" ref={chatsRef}>
          {welcome && !messages.length && (
            <h2 className="bot-name">Hello, AJ</h2>
          )}

          {messages.map((msg, idx) =>
            msg.from === 'user' ? (
              <div key={idx} className="user-chat">
                <p style={{ whiteSpace: "pre-wrap" }}>{msg.text}</p>
              </div>
            ) : (
              <div key={idx} className="bot-chat">
                <ReactMarkdown
                  children={msg.text}
                  remarkPlugins={[remarkGfm, remarkBreaks]}
                  components={{
                    p: ({ node, ...props }) => (
                      <p style={{ whiteSpace: "pre-wrap", margin: "0 0 0.5rem" }} {...props} />
                    )
                  }}
                />
              </div>
            )
          )}

          
          {isLoading && (
            <div className="bot-loading">
              <p>Thinking...</p>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>
      <div className="bot-input">
        <input
          type="text"
          placeholder="Cook everything"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !isLoading && sendMessage()}
          disabled={isLoading}
        />
        <button className="bot-arrow" onClick={sendMessage} disabled={isLoading}>
          <i className="fa-solid fa-arrow-up" />
        </button>
      </div>
    </div>
  );
}

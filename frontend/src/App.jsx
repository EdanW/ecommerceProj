import { useState, useEffect } from 'react';
import axios from 'axios';
import { Auth } from './components/Auth';      // The new Login/Register screen
import { Profile } from './components/Profile'; // The new Profile/Data screen
import { Activity, Utensils, User, Home } from 'lucide-react';
import './App.css';

const API_URL = 'http://localhost:8000';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [view, setView] = useState('dashboard'); // 'dashboard', 'craving', 'profile'

  // If no token, show the Auth/Register screen
  if (!token) return <Auth setToken={setToken} />;

  // If logged in, show the main app
  return (
    <div className="app-container">
      <div className="phone-frame">
        <Header />

        {/* VIEW SWITCHER */}
        {view === 'dashboard' && <Dashboard setView={setView} token={token} />}
        {view === 'craving' && <CravingTool setView={setView} token={token} />}
        {view === 'profile' && <Profile setView={setView} token={token} />}

        <BottomNav setView={setView} active={view} />
      </div>
    </div>
  );
}

// --- Components ---

function Dashboard({ setView, token }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get(`${API_URL}/status`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setData(res.data);
      } catch (err) {
        console.error("Failed to load dashboard");
      }
    };
    fetchData();
  }, [token]);

  if (!data) return <div className="content">Loading...</div>;

  return (
    <div className="content">
      <div className="greeting">
        <p className="subtext">Good afternoon {data.user}</p>
        <h2>{data.wellness_message}</h2>
      </div>

      <div className="card progress-card">
        <div className="row">
          <span>Week {data.week}</span>
          <span className="pink-tag">Trimester 3</span>
        </div>
        <div className="progress-bar"><div style={{width: '70%'}}></div></div>
        <p className="tiny-text">Your baby is about the size of an eggplant 🍆</p>
      </div>

      <div className="card glucose-card">
        <div className="row">
          <Activity color="#F48FB1" />
          <span>Current Glucose</span>
        </div>
        <h1 className={data.glucose.level > 140 ? "alert-text" : "normal-text"}>
          {data.glucose.level} <span className="unit">mg/dL</span>
        </h1>
        <p className="tiny-text">{data.glucose.status} — based on recent trend</p>
      </div>

      <button className="crave-btn" onClick={() => setView('craving')}>
        <Utensils size={18} /> Tell me what you're craving ✨
      </button>
    </div>
  );
}

function CravingTool({ setView, token }) {
  const [input, setInput] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const checkCraving = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/analyze_craving`,
        { food_name: input },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setResult(res.data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  return (
    <div className="content craving-view">
      <button className="back-btn" onClick={() => setView('dashboard')}>← Back</button>
      <h2>What are you in the mood for?</h2>
      <div className="input-group">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="e.g., A chocolate milkshake..."
        />
        <button onClick={checkCraving} disabled={loading}>
          {loading ? "..." : "Check"}
        </button>
      </div>

      {result && (
        <div className="ai-response fade-in">
          <div className={`status-badge ${result.safety === 'High Safety' ? 'green' : 'orange'}`}>
            {result.safety}
          </div>
          <p className="ai-message">"{result.message}"</p>
          <div className="suggestion-box">
            <h4>💡 Better Option:</h4>
            <p>{result.alternative}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function Header() { return <div className="status-bar"><span>9:41</span></div>; }

function BottomNav({ setView, active }) {
  return (
    <div className="bottom-nav">
      <div
        className={active === 'dashboard' ? 'active' : ''}
        onClick={() => setView('dashboard')}
      >
        <Home size={20} />
        <span>Home</span>
      </div>
      <div
        className={active === 'profile' ? 'active' : ''}
        onClick={() => setView('profile')}
      >
        <User size={20} />
        <span>Profile</span>
      </div>
    </div>
  );
}

export default App;
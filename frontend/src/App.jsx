import { useState, useEffect } from 'react';
import axios from 'axios';
import { Auth } from './components/Auth';
import { Profile } from './components/Profile';
import { Header } from './components/Header';
import { Activity, Utensils, Home, User } from 'lucide-react';
import './App.css';

const API_URL = 'http://localhost:8000';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [view, setView] = useState('dashboard');

  const logout = () => {
      localStorage.removeItem('token');
      setToken(null);
      setView('dashboard');
  };

  return (
    <div className="app-container">
      {/* 1. Phone Frame ALWAYS exists */}
      <div className="phone-frame">

        {/* 2. Header ALWAYS exists (Status Bar) */}
        <Header />

        {/* 3. Content Switches INSIDE the phone */}
        {!token ? (
            <Auth setToken={setToken} />
        ) : (
            <>
                {view === 'dashboard' && <Dashboard setView={setView} token={token} logout={logout} />}
                {view === 'craving' && <CravingTool setView={setView} token={token} />}
                {view === 'profile' && <Profile setView={setView} token={token} logout={logout} />}

                {/* Navigation only shows when logged in */}
                <BottomNav setView={setView} active={view} />
            </>
        )}
      </div>
    </div>
  );
}

// ... Keep your existing Dashboard, CravingTool, BottomNav components below ...
function Dashboard({ setView, token, logout }) {
    // ... (Your existing Dashboard code)
    // Just to be safe, paste the Dashboard code from previous steps here
    const [data, setData] = useState(null);
    useEffect(() => {
        // ZOMBIE FIX
        const interceptor = axios.interceptors.response.use(r => r, e => {
            if (e.response?.status === 401) logout();
            return Promise.reject(e);
        });
        axios.get(`${API_URL}/status`, { headers: { Authorization: `Bearer ${token}` } })
            .then(res => setData(res.data))
            .catch(console.error);
        return () => axios.interceptors.response.eject(interceptor);
    }, []);

    if (!data) return <div className="content">Loading...</div>;

    return (
        <div className="content">
            <div style={{display:'flex', alignItems:'center', gap:'10px', marginBottom:'20px'}}>
                <h2 style={{margin:0, color:'#2D3436'}}>Eat42</h2>
            </div>
            <div className="greeting">
                <p className="subtext">Good afternoon {data.user}</p>
                <h2>{data.wellness_message}</h2>
            </div>
            {/* ... rest of your cards ... */}
            <div className="card progress-card">
                <div className="row"><span>Week {data.week}</span><span className="pink-tag">Trimester 3</span></div>
                <div className="progress-bar"><div style={{width: '70%'}}></div></div>
                <p className="tiny-text">Your baby is about the size of an eggplant 🍆</p>
            </div>
            <div className="card glucose-card">
                <div className="row"><Activity color="#F48FB1" /><span>Current Glucose</span></div>
                <h1 className={data.glucose.level > 140 ? "alert-text" : "normal-text"}>
                    {data.glucose.level} <span className="unit">mg/dL</span>
                </h1>
            </div>
            <button className="crave-btn" onClick={() => setView('craving')}><Utensils size={18} /> Tell me what you're craving ✨</button>
        </div>
    );
}

function CravingTool({ setView, token }) {
    // ... (Your existing CravingTool code) ...
    return <div className="content">Craving Tool (Check previous code)</div>; // Replace with real code
}

function BottomNav({ setView, active }) {
  return (
    <div className="bottom-nav">
      <div className={active === 'dashboard' ? 'active' : ''} onClick={() => setView('dashboard')}><Home size={20} /><span>Home</span></div>
      <div className={active === 'profile' ? 'active' : ''} onClick={() => setView('profile')}><User size={20} /><span>Profile</span></div>
    </div>
  );
}

export default App;
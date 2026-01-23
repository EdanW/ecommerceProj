import { useState, useEffect } from 'react';
import axios from 'axios';
import { Auth } from './components/Auth';
import { Profile } from './components/Profile';
import { Header } from './components/Header';
import './App.css';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { GlucoseChart, FoodLog } from './components/Placeholders';
import { Activity, Utensils, Home, User, LineChart, ScrollText } from 'lucide-react';

const API_URL = 'http://localhost:8000';

function App() {
  const [token, setToken] = useState(sessionStorage.getItem('token'));
  const [view, setView] = useState('dashboard');

    const logout = () => {
        sessionStorage.removeItem('token'); // changed from localStorage
        setToken(null);
        setView('dashboard');
    };

  return (
    <div className="app-container">
      <div className="phone-frame">
        <Header />
        {!token ? (
            <Auth setToken={setToken} />
        ) : (
            <>
                {view === 'dashboard' && <Dashboard setView={setView} token={token} logout={logout} />}
                {view === 'craving' && <CravingTool setView={setView} token={token} />}
                {view === 'profile' && <Profile setView={setView} token={token} logout={logout} />}
                {view === 'glucose' && <GlucoseChart />}
                {view === 'foodlog' && <FoodLog />}
                {/* Navigation only shows when logged in */}
                <BottomNav setView={setView} active={view} />
            </>
        )}
      </div>
    </div>
  );
}

function Dashboard({ setView, token, logout }) {
    const [data, setData] = useState(null);
    const getGreeting = () => {
      const hour = new Date().getHours();
      if (hour < 12) return "☀️ Good Morning";
      if (hour < 18) return "🌅 Good Afternoon";
      if (hour < 21) return "✨ Good Evening";
      return "💤 Good Night";
  };
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
          <div className="greeting" style={{marginTop: '10px'}}>
            <p className="subtext">{getGreeting()} {data.display_name}</p>
            <h2>{data.wellness_message}</h2>
          </div>

        <div className="card progress-card">
            {data.pregnancy_data ? (
                <>
                    {/* 3. Spacing Fixed */}
                    <div className="row" style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                      <span style={{fontWeight:'bold'}}>Week {data.pregnancy_data.week}</span>
                      <span className="pink-tag">Trimester {data.pregnancy_data.trimester}</span>
                    </div>
                    <div className="progress-bar"><div style={{width: `${(data.pregnancy_data.week / 40) * 100}%`}}></div></div>
                    {/* 4. Dynamic Baby Size */}
                    <p className="tiny-text">Your baby is about the size of {data.pregnancy_data.size}</p>
                </>
            ) : (
                <div style={{textAlign:'center', padding:'10px'}}>
                    <p>Add your pregnancy start date to see your progress!</p>
                    <button className="crave-btn" style={{padding:'10px', fontSize:'14px'}} onClick={() => setView('profile')}>Add Date</button>
                </div>
            )}
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
    const [input, setInput] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [feedbackGiven, setFeedbackGiven] = useState(false); // Track if user voted

    const checkCraving = async () => {
        if (!input.trim()) return;
        setLoading(true);
        setFeedbackGiven(false); // Reset feedback for new search
        try {
            const res = await axios.post(`${API_URL}/analyze_craving`,
                { food_name: input },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setResult(res.data);
        } catch (e) {
            console.error(e);
            alert("AI service unavailable.");
        }
        setLoading(false);
    };

    const sendFeedback = async (isLiked) => {
        try {
            await axios.post(`${API_URL}/feedback`, {
                craving: input,
                suggestion: result.alternative, // We save the suggestion specifically
                is_liked: isLiked
            }, { headers: { Authorization: `Bearer ${token}` } });

            setFeedbackGiven(true); // Show "Thank you"
        } catch (e) {
            console.error("Feedback failed", e);
        }
    };

    return (
        <div className="content craving-view">
            <button className="back-btn" onClick={() => setView('dashboard')}>← Back</button>
            <h2 style={{marginTop: '0'}}>What are you in the mood for?</h2>

            <div className="input-group" style={{marginTop: '20px'}}>
                <input
                  className="modern-input"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder="e.g., A chocolate milkshake..."
                />
                <button className="crave-btn" onClick={checkCraving} disabled={loading} style={{opacity: loading ? 0.7 : 1}}>
                  {loading ? "Analyzing..." : "Check"}
                </button>
            </div>

            {result && (
                <div className="fade-in" style={{marginTop: '25px', background:'#F9FAFB', padding:'20px', borderRadius:'15px', border:'1px solid #eee'}}>
                  <div className={`status-badge ${result.safety === 'High Safety' ? 'green' : 'orange'}`} style={{display:'inline-block', marginBottom:'10px'}}>
                    {result.safety}
                  </div>

                  <p style={{fontSize:'18px', fontWeight:'500', color:'#333', marginTop:'5px'}}>
                    "{result.message}"
                  </p>

                  <div style={{marginTop: '15px', background:'white', padding:'15px', borderRadius:'12px', borderLeft:'4px solid #6FCF97', boxShadow:'0 2px 5px rgba(0,0,0,0.05)'}}>
                    <h4 style={{margin:'0 0 5px 0', color:'#6FCF97', fontSize:'14px'}}>💡 Better Option:</h4>
                    <p style={{margin:0, fontSize:'15px', color:'#555'}}>{result.alternative}</p>
                  </div>

                  {/* FEEDBACK SECTION */}
                  <div style={{marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '15px', display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                    <span className="tiny-text">Was this helpful?</span>

                    {!feedbackGiven ? (
                        <div style={{display: 'flex', gap: '10px'}}>
                            <button onClick={() => sendFeedback(false)} style={{background: 'white', border: '1px solid #eee', borderRadius: '8px', padding: '8px', cursor: 'pointer', color: '#FF5252'}}>
                                <ThumbsDown size={18} />
                            </button>
                            <button onClick={() => sendFeedback(true)} style={{background: 'white', border: '1px solid #eee', borderRadius: '8px', padding: '8px', cursor: 'pointer', color: '#6FCF97'}}>
                                <ThumbsUp size={18} />
                            </button>
                        </div>
                    ) : (
                        <span className="tiny-text" style={{color: '#6FCF97', fontWeight: 'bold'}}>Thanks for your feedback!</span>
                    )}
                  </div>

                </div>
            )}
        </div>
    );
}


function BottomNav({ setView, active }) {
  return (
    <div className="bottom-nav" style={{justifyContent: 'space-around', paddingBottom:'10px'}}>

      {/* Home */}
      <div className={active === 'dashboard' ? 'active' : ''} onClick={() => setView('dashboard')}>
        <Home size={24} strokeWidth={active === 'dashboard' ? 3 : 2} />
      </div>

      {/* Glucose Chart */}
      <div className={active === 'glucose' ? 'active' : ''} onClick={() => setView('glucose')}>
        <LineChart size={24} strokeWidth={active === 'glucose' ? 3 : 2} />
      </div>

      {/* Food Log (Now Standard Style) */}
      <div className={active === 'foodlog' ? 'active' : ''} onClick={() => setView('foodlog')}>
        <ScrollText size={24} strokeWidth={active === 'foodlog' ? 3 : 2} />
      </div>

      {/* Profile */}
      <div className={active === 'profile' ? 'active' : ''} onClick={() => setView('profile')}>
        <User size={24} strokeWidth={active === 'profile' ? 3 : 2} />
      </div>

    </div>
  );
}

export default App;
import { useState } from 'react';
import axios from 'axios';
import { CloudLightning, Check, Loader } from 'lucide-react';

const API_URL = 'http://localhost:8000';

export function Profile({ setView, token }) {
    const [connected, setConnected] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleConnect = async () => {
        setLoading(true);
        try {
            // Trigger the "Ingestion" on backend
            await axios.post(`${API_URL}/ingest_data`, { source: 'google_health' }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setTimeout(() => {
                setConnected(true);
                setLoading(false);
            }, 1500); // Fake delay for realism
        } catch (e) {
            alert("Connection failed");
            setLoading(false);
        }
    };

    return (
        <div className="content">
            <button className="back-btn" onClick={() => setView('dashboard')}>← Back</button>
            <h2>My Health Data</h2>

            <div className="card">
                <div className="row">
                    <div style={{display:'flex', gap:'10px', alignItems:'center'}}>
                        <div className="icon-box blue"><CloudLightning /></div>
                        <div>
                            <strong>Google Health</strong>
                            <p className="tiny-text">Sync glucose & activity</p>
                        </div>
                    </div>
                    {connected ? <Check color="green"/> : null}
                </div>

                {!connected ? (
                    <button className="crave-btn" onClick={handleConnect} disabled={loading} style={{marginTop: '15px'}}>
                         {loading ? <span><Loader className="spin"/> Syncing...</span> : "Connect Account"}
                    </button>
                ) : (
                    <div className="suggestion-box" style={{marginTop: '15px'}}>
                        <p className="tiny-text" style={{color:'green'}}>
                            ✅ Synced: 28 days of glucose logs imported.
                        </p>
                    </div>
                )}
            </div>

            <button className="back-btn" style={{marginTop:'auto', color:'red'}}
                onClick={() => {
                    localStorage.removeItem('token');
                    window.location.reload();
                }}>
                Log Out
            </button>
        </div>
    );
}
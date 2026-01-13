import { useState } from 'react';
import axios from 'axios';
import { Sparkles } from 'lucide-react';

const API_URL = 'http://localhost:8000';

export function Auth({ setToken }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      if (isRegistering) {
        // Register Flow
        await axios.post(`${API_URL}/register`, { username, password });
        // Auto-login after register
        await login();
      } else {
        // Login Flow
        await login();
      }
    } catch (err) {
      setError(isRegistering
        ? "Username already taken."
        : "Invalid credentials. Try registering!");
    }
  };

  const login = async () => {
    // Note: In real OAuth, you use FormData. Here we use JSON for simplicity as built in main.py
    const res = await axios.post(`${API_URL}/token`, { username, password });
    localStorage.setItem('token', res.data.access_token);
    setToken(res.data.access_token);
  };

  return (
    <div className="login-screen">
      <div className="logo-area">
        <h1 className="logo-text">Eat42 <Sparkles size={24} style={{display:'inline'}}/></h1>
        <p>From Restriction to Support</p>
      </div>

      <div className="card" style={{marginTop: '20px'}}>
        <h3>{isRegistering ? 'Create Account' : 'Welcome Back'}</h3>

        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />

          <button type="submit" className="crave-btn" style={{marginTop: '10px'}}>
            {isRegistering ? 'Sign Up' : 'Log In'}
          </button>
        </form>

        {error && <p className="alert-text" style={{fontSize: '12px', marginTop: '10px'}}>{error}</p>}

        <p className="tiny-text" style={{marginTop: '20px', cursor: 'pointer'}}
           onClick={() => setIsRegistering(!isRegistering)}>
          {isRegistering ? "Already have an account? Log in" : "New here? Create account"}
        </p>
      </div>
    </div>
  );
}
import { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

export function Auth({ setToken }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [formData, setFormData] = useState({
    username: '', password: '',
    first_name: '', last_name: '', // New Fields
    email: '', phone: '', age: '', height: '', weight: '', pregnancy_start_date: '', medical_notes: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => setFormData({...formData, [e.target.name]: e.target.value});

  const validatePassword = (pwd) => {
    const regex = /^(?=.*[A-Z])(?=.*[!@#$&*])(?=.{6,})/;
    return regex.test(pwd);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');

    try {
      if (isRegistering) {
        if (!validatePassword(formData.password)) {
            setError("Password needs: 6+ chars, 1 Capital, 1 Symbol");
            return;
        }

        const cleanData = {
            ...formData,
            age: formData.age ? parseInt(formData.age) : null,
            height: formData.height ? parseFloat(formData.height) : null,
            weight: formData.weight ? parseFloat(formData.weight) : null
        };

        await axios.post(`${API_URL}/register`, cleanData);
        setSuccess("Account created! Please Log In.");
        setIsRegistering(false);
        setFormData({...formData, password: ''});
      } else {
        const res = await axios.post(`${API_URL}/token`, {
            username: formData.username, password: formData.password
        });
        localStorage.setItem('token', res.data.access_token);
        setToken(res.data.access_token);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Action failed");
    }
  };

  return (
    <div className="login-screen">
      <div style={{textAlign: 'center', marginBottom: '20px', marginTop: '40px'}}>
        <h1 className="logo-text" style={{fontSize: '42px', margin: 0}}>Eat42</h1>
        <p style={{color: '#888', fontSize: '14px'}}>From Restriction to Support</p>
      </div>

      <div className="card fade-in" style={{maxHeight: '65vh', overflowY: 'auto'}}>
        <h3 style={{marginBottom: '15px'}}>{isRegistering ? 'Join Us' : 'Welcome Back'}</h3>
        {error && <div className="status-badge orange" style={{display:'block', marginBottom:'10px'}}>{error}</div>}
        {success && <div className="status-badge green" style={{display:'block', marginBottom:'10px'}}>{success}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <input className="modern-input" name="username" placeholder="Username (for login)" onChange={handleChange} required />
          <input className="modern-input" name="password" type="password" placeholder="Password" onChange={handleChange} required />

          {isRegistering && (
            <div className="fade-in">
                <p className="tiny-text" style={{marginTop:'15px', fontWeight:'bold'}}>About You</p>
                {/* NEW NAME FIELDS */}
                <div className="row-inputs">
                    <input className="modern-input" name="first_name" placeholder="First Name" onChange={handleChange} />
                    <input className="modern-input" name="last_name" placeholder="Last Name" onChange={handleChange} />
                </div>

                <input className="modern-input" name="email" placeholder="Email Address" onChange={handleChange} />

                <div className="row-inputs">
                    <input className="modern-input" name="height" type="number" placeholder="Height (cm)" onChange={handleChange} />
                    <input className="modern-input" name="weight" type="number" placeholder="Weight (kg)" onChange={handleChange} />
                </div>
                <div className="row-inputs">
                    <input className="modern-input" name="age" type="number" placeholder="Age" onChange={handleChange} />
                    <input className="modern-input" name="pregnancy_start_date" type="text" onFocus={(e) => e.target.type = 'date'} placeholder="Pregnancy Start" onChange={handleChange} />
                </div>
                <textarea className="modern-input" name="medical_notes" placeholder="Any medical notes?" onChange={handleChange} style={{resize:'none', height:'80px'}}/>
            </div>
          )}
          <button type="submit" className="crave-btn" style={{marginTop: '20px'}}>{isRegistering ? 'Sign Up' : 'Log In'}</button>
        </form>
        <p className="tiny-text" style={{marginTop: '20px', textAlign:'center', cursor: 'pointer', textDecoration:'underline', color:'#666'}} onClick={() => setIsRegistering(!isRegistering)}>
           {isRegistering ? "Already have an account? Log In" : "New here? Create Account"}
        </p>
      </div>
    </div>
  );
}
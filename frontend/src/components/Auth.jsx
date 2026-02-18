import { useState } from 'react';
import axios from 'axios';
import { Camera } from 'lucide-react';
import { validatePassword, validateProfileData } from '../utils/validations.js';

const API_URL = 'http://localhost:8000';

export function Auth({ setToken }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [formData, setFormData] = useState({
    username: '', password: '',
    first_name: '', last_name: '',
    email: '', phone: '', age: '', height: '', weight: '', pregnancy_start_date: '', medical_notes: '',
    profile_picture: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => setFormData({...formData, [e.target.name]: e.target.value});

  const handleImageUpload = (e) => {
      const file = e.target.files[0];
      if (file) {
          const reader = new FileReader();
          reader.onloadend = () => setFormData({...formData, profile_picture: reader.result});
          reader.readAsDataURL(file);
      }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');

    try {
      if (isRegistering) {
        // --- CLEAN VALIDATION LOGIC ---

        // 1. Check Password
        if (!validatePassword(formData.password)) {
            setError("Password needs: 6+ chars, 1 Capital, 1 Symbol (!@#$)");
            return;
        }

        // 2. Check Profile Data (Age, Weight, Date, etc.)
        const validationError = validateProfileData(formData);
        if (validationError) {
            setError(validationError);
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
        setFormData(prev => ({ ...prev, password: '' }));
        setError('');
      } else {
        const res = await axios.post(`${API_URL}/token`, {
            username: formData.username, password: formData.password
        });
        sessionStorage.setItem('token', res.data.access_token);
        setToken(res.data.access_token);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Action failed");
    }
  };

  const toggleMode = () => { setIsRegistering(!isRegistering); setError(''); setSuccess(''); };

  return (
      <div className="login-screen">
           <div className="text-center mb-20" style={{marginTop: '40px'}}>
            <h1 className="logo-text" style={{fontSize: '42px', margin: 0}}>Nouri</h1>
            <p style={{color: '#888', fontSize: '14px'}}>From Restriction to Support</p>
          </div>

          <div className="card fade-in" style={{maxHeight: '65vh', overflowY: 'auto'}}>
            <h3 className="mb-20">{isRegistering ? 'Join Us' : 'Welcome Back'}</h3>

            <form onSubmit={handleSubmit} className="auth-form">
              <input className="modern-input" name="username" placeholder="Username" onChange={handleChange} value={formData.username} required />
              <input className="modern-input" name="password" type="password" placeholder="Password" onChange={handleChange} value={formData.password} required />

              {isRegistering && (
                <div className="fade-in">
                    <p className="tiny-text" style={{marginTop:'15px', fontWeight:'bold'}}>About You</p>
                    <div className="text-center mb-20">
                        <div className="profile-pic-container" style={{margin: '0 auto'}}>
                            {formData.profile_picture ? (
                                <img src={formData.profile_picture} style={{width:'100%', height:'100%', objectFit:'cover'}} />
                            ) : (
                                <div className="flex-center" style={{height:'100%', color:'#aaa'}}><Camera size={24}/></div>
                            )}
                            <input type="file" accept="image/*" onChange={handleImageUpload} style={{position:'absolute', top:0, left:0, width:'100%', height:'100%', opacity:0, cursor:'pointer'}} />
                        </div>
                        <p className="tiny-text">Tap to add photo</p>
                    </div>
                    <div className="row-inputs">
                        <input className="modern-input" name="first_name" placeholder="First Name" onChange={handleChange} />
                        <input className="modern-input" name="last_name" placeholder="Last Name" onChange={handleChange} />
                    </div>
                    <input className="modern-input" name="email" placeholder="Email Address" onChange={handleChange} />
                    <input className="modern-input" name="phone" placeholder="Phone Number" onChange={handleChange} />
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

              {/* Messages */}
              {error && <div className="status-badge orange" style={{display:'block', marginBottom:'10px', marginTop:'10px'}}>{error}</div>}
              {success && <div className="status-badge green" style={{display:'block', marginBottom:'10px', marginTop:'10px'}}>{success}</div>}

              <button type="submit" className="crave-btn mt-10">{isRegistering ? 'Sign Up' : 'Log In'}</button>
            </form>

            <p className="tiny-text text-center mt-20" style={{cursor: 'pointer', textDecoration:'underline', color:'#666'}} onClick={toggleMode}>
               {isRegistering ? "Already have an account? Log In" : "New here? Create Account"}
            </p>
          </div>
      </div>
  );
}
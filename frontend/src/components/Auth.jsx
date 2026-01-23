import { useState } from 'react';
import axios from 'axios';
import { Camera } from 'lucide-react';

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
          reader.onloadend = () => {
              setFormData({...formData, profile_picture: reader.result});
          };
          reader.readAsDataURL(file);
      }
  };

  // --- 2. FIXED VALIDATION LOGIC ---
  const validatePassword = (pwd) => {
    // 1 Capital, 1 Symbol, 6+ Characters
    const regex = /^(?=.*[A-Z])(?=.*[!@#$&*])(?=.{6,})/;
    return regex.test(pwd);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');

    try {
      if (isRegistering) {
        // --- CHECK PASSWORD STRENGTH HERE ---
        if (!validatePassword(formData.password)) {
            setError("Password too weak: Needs 6+ chars, 1 Capital, 1 Symbol (!@#$)");
            return; // Stop execution if weak
        }

        if (formData.age && (formData.age < 18 || formData.age > 60)) {
            setError("Please enter a valid age (18-60)");
            return;
        }

        if (formData.height && (formData.height < 100 || formData.height > 250)) {
            setError("Please enter a valid height in cm");
            return;
        }

        if (formData.weight && (formData.weight < 40 || formData.weight > 500)) {
            setError("Please enter a valid weight in kg");
            return;
        }

        if (formData.pregnancy_start_date) {
            const date = new Date(formData.pregnancy_start_date);
            const today = new Date();
            if (date > today) {
                setError("Pregnancy start date cannot be in the future");
                return;
            }
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

  // --- 3. FIX ERROR CLEARING ON TOGGLE ---
  const toggleMode = () => {
      setIsRegistering(!isRegistering);
      setError('');   // Clear old errors
      setSuccess(''); // Clear old success messages
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
          {}
          <input className="modern-input" name="username" placeholder="Username" onChange={handleChange} value={formData.username} required />
          <input className="modern-input" name="password" type="password" placeholder="Password" onChange={handleChange} value={formData.password} required />

          {isRegistering && (
            <div className="fade-in">
                <p className="tiny-text" style={{marginTop:'15px', fontWeight:'bold'}}>About You</p>

                <div style={{textAlign:'center', marginBottom:'15px'}}>
                    <div style={{width:'80px', height:'80px', borderRadius:'50%', background:'#f0f0f0', margin:'0 auto', overflow:'hidden', position:'relative', border:'2px solid #ddd'}}>
                        {formData.profile_picture ? (
                            <img src={formData.profile_picture} style={{width:'100%', height:'100%', objectFit:'cover'}} />
                        ) : (
                            <div style={{display:'flex', alignItems:'center', justifyContent:'center', height:'100%', color:'#aaa'}}><Camera size={24}/></div>
                        )}
                        <input type="file" accept="image/*" onChange={handleImageUpload}
                               style={{position:'absolute', top:0, left:0, width:'100%', height:'100%', opacity:0, cursor:'pointer'}} />
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
          <button type="submit" className="crave-btn" style={{marginTop: '20px'}}>{isRegistering ? 'Sign Up' : 'Log In'}</button>
        </form>

        {/* USE THE NEW TOGGLE FUNCTION HERE */}
        <p className="tiny-text" style={{marginTop: '20px', textAlign:'center', cursor: 'pointer', textDecoration:'underline', color:'#666'}}
           onClick={toggleMode}>
           {isRegistering ? "Already have an account? Log In" : "New here? Create Account"}
        </p>
      </div>
    </div>
  );
}
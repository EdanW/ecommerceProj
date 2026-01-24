import { useState, useEffect } from 'react';
import axios from 'axios';
import { User, LogOut, Save, Edit2, X, Camera, Trash2 } from 'lucide-react';
import { validateProfileData } from '../utils/validations.js';

const API_URL = 'http://localhost:8000';

export function Profile({ setView, token, logout }) {
    const [isEditing, setIsEditing] = useState(false);
    const [loading, setLoading] = useState(true);
    const [msg, setMsg] = useState('');
    const [error, setError] = useState(''); // New state for validation errors

    const [profile, setProfile] = useState({
        username: '', first_name: '', last_name: '',
        email: '', phone: '', age: '', height: '', weight: '',
        pregnancy_start_date: '', medical_notes: '', profile_picture: ''
    });

    useEffect(() => { loadData(); }, []);

    const loadData = async () => {
        try {
            const res = await axios.get(`${API_URL}/status`, { headers: { Authorization: `Bearer ${token}` } });
            const p = res.data.profile || {};
            setProfile({
                username: res.data.username || '',
                first_name: p.first_name || '',
                last_name: p.last_name || '',
                email: p.email || '',
                phone: p.phone || '',
                age: p.age || '',
                height: p.height || '',
                weight: p.weight || '',
                pregnancy_start_date: p.pregnancy_start_date || '',
                medical_notes: p.medical_notes || '',
                profile_picture: p.profile_picture || ''
            });
            setLoading(false);
        } catch (err) { if (err.response?.status === 401) logout(); }
    };

    const handleSave = async () => {
        setMsg(''); setError('');
        const validationError = validateProfileData(profile);

        if (validationError) {
            setError(validationError);
            return;
        }

        try {
            const cleanNum = (val) => (val === '' || val == null ? null : Number(val));
            const cleanStr = (val) => (val === '' ? null : val);

            const payload = {
                username: profile.username, password: "x",
                first_name: cleanStr(profile.first_name),
                last_name: cleanStr(profile.last_name),
                email: cleanStr(profile.email),
                phone: cleanStr(profile.phone),
                age: cleanNum(profile.age),
                height: cleanNum(profile.height),
                weight: cleanNum(profile.weight),
                pregnancy_start_date: cleanStr(profile.pregnancy_start_date),
                medical_notes: cleanStr(profile.medical_notes),
                profile_picture: cleanStr(profile.profile_picture)
            };

            await axios.put(`${API_URL}/update_profile`, payload, { headers: { Authorization: `Bearer ${token}` } });
            setMsg('Saved!');
            setIsEditing(false);
            setTimeout(() => setMsg(''), 2000);
        } catch (e) { setMsg('Error Saving'); }
    };

    const handleDeleteAccount = async () => {
        if (confirm("Are you sure? This will delete all your data permanently.")) {
            try {
                await axios.delete(`${API_URL}/delete_account`, { headers: { Authorization: `Bearer ${token}` } });
                logout(); // Log out immediately after deletion
            } catch (e) {
                alert("Failed to delete account");
            }
        }
    };

    const handleImageUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => setProfile({...profile, profile_picture: reader.result});
            reader.readAsDataURL(file);
        }
    };

    const handleChange = (e) => setProfile({...profile, [e.target.name]: e.target.value});

    if (loading) return <div className="content">Loading...</div>;

    const displayName = (profile.first_name || profile.last_name) ? `${profile.first_name} ${profile.last_name}` : profile.username;
    const formatDate = (value) => {
        if (!value) return '';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' });
    };

    return (
        <div className="content">
            <div style={{display:'flex', justifyContent:'flex-end', marginBottom:'10px'}}>
                {!isEditing ? (
                    <button className="icon-btn" onClick={() => setIsEditing(true)} style={{color:'var(--pink)'}}><Edit2 size={18}/> Edit</button>
                ) : (
                    <button className="icon-btn" onClick={() => { setIsEditing(false); loadData(); setError(''); }} style={{color:'#888'}}><X size={18}/> Cancel</button>
                )}
            </div>

            {msg && <div className="status-badge green" style={{marginBottom:'15px'}}>{msg}</div>}
            {error && <div className="status-badge orange" style={{marginBottom:'15px'}}>{error}</div>}

            <div className="card">
                <div style={{textAlign:'center', marginBottom:'20px'}}>
                    <div className="profile-pic-container" style={{margin: '0 auto 10px'}}>
                        {profile.profile_picture ? (
                            <img src={profile.profile_picture} style={{width:'100%', height:'100%', objectFit:'cover'}} />
                        ) : (
                            <div className="flex-center" style={{height:'100%', color:'#ccc'}}><User size={40}/></div>
                        )}
                        {isEditing && <input type="file" accept="image/*" onChange={handleImageUpload} style={{position:'absolute', top:0, left:0, width:'100%', height:'100%', opacity:0, cursor:'pointer'}} />}
                    </div>
                    <h3 style={{margin:0}}>{displayName}</h3>
                    {!isEditing && <p className="tiny-text">{profile.email || "No email"}</p>}
                </div>

                {!isEditing ? (
                    <div className="profile-details fade-in">
                        <InfoRow label="Phone" value={profile.phone} />
                        <div style={{display:'flex', gap:'20px'}}>
                            <InfoRow label="Age" value={profile.age} />
                            <InfoRow label="Start Date" value={formatDate(profile.pregnancy_start_date)} />
                        </div>
                        <div style={{display:'flex', gap:'20px'}}>
                            <InfoRow label="Height" value={profile.height ? `${profile.height} cm` : ''} />
                            <InfoRow label="Weight" value={profile.weight ? `${profile.weight} kg` : ''} />
                        </div>
                        <div style={{marginTop:'15px'}}>
                            <label className="tiny-text">Medical Notes</label>
                            <div style={{padding:'10px', background:'#F9FAFB', borderRadius:'10px', fontSize:'14px', minHeight:'40px', color:'#555'}}>
                                {profile.medical_notes || "No notes."}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="edit-form fade-in">
                        <label className="tiny-text">Name</label>
                        <div className="row-inputs">
                            <input className="modern-input" name="first_name" placeholder="First Name" value={profile.first_name} onChange={handleChange} />
                            <input className="modern-input" name="last_name" placeholder="Last Name" value={profile.last_name} onChange={handleChange} />
                        </div>
                        <label className="tiny-text">Contact</label>
                        <input className="modern-input" name="email" placeholder="Email" value={profile.email} onChange={handleChange} />
                        <input className="modern-input" name="phone" placeholder="Phone" value={profile.phone} onChange={handleChange} />
                        <label className="tiny-text">Stats</label>
                        <div className="row-inputs">
                            <input className="modern-input" name="age" type="number" placeholder="Age" value={profile.age} onChange={handleChange} />
                            <input className="modern-input" name="pregnancy_start_date" type="date" value={profile.pregnancy_start_date} onChange={handleChange} />
                        </div>
                        <div className="row-inputs">
                            <input className="modern-input" name="height" type="number" placeholder="Height" value={profile.height} onChange={handleChange} />
                            <input className="modern-input" name="weight" type="number" placeholder="Weight" value={profile.weight} onChange={handleChange} />
                        </div>
                        <label className="tiny-text">Notes</label>
                        <textarea className="modern-input" name="medical_notes" placeholder="Notes..." value={profile.medical_notes} onChange={handleChange} style={{height:'80px'}}/>
                        <button className="crave-btn" onClick={handleSave} style={{marginTop:'10px'}}><Save size={18}/> Save Changes</button>
                    </div>
                )}
            </div>

            <button className="back-btn" onClick={logout} style={{marginTop:'20px', color:'#888', width:'100%', justifyContent:'center'}}>
                <LogOut size={18}/> Log Out
            </button>

            <button className="back-btn" onClick={handleDeleteAccount} style={{marginTop:'10px', color:'#FF5252', width:'100%', justifyContent:'center', fontSize:'12px'}}>
                <Trash2 size={14}/> Delete Account
            </button>
        </div>
    );
}

function InfoRow({ label, value }) { return (<div style={{marginBottom:'12px', flex:1}}><label className="tiny-text" style={{display:'block', marginBottom:'2px'}}>{label}</label><div style={{fontSize:'15px', fontWeight:'500', color:'#333', borderBottom:'1px solid #eee', paddingBottom:'5px'}}>{value || "-"}</div></div>); }
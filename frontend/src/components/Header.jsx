import { useState, useEffect } from 'react';

export function Header() {
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const formatTime = (date) => {
        return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false });
    };

    return (
        <div className="header-container">
            <h2 style={{margin:0, color:'#6FCF97', fontSize:'24px', fontFamily:'sans-serif'}}>Eat42</h2>
            <span style={{fontWeight:'600', fontSize:'14px', color:'#333'}}>{formatTime(time)}</span>
        </div>
    );
}
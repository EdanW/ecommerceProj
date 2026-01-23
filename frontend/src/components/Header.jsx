import { useState, useEffect } from 'react';

export function Header() {
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const formatTime = (date) => {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    return (
        <div style={{
            height: '44px',
            display: 'flex',
            alignItems: 'center',
            paddingLeft: '25px', /* Increased padding to avoid corner clip */
            paddingRight: '20px',
            fontWeight: '600',
            fontSize: '14px',
            marginTop: '5px' /* Push down slightly */
        }}>
            <span>{formatTime(time)}</span>
        </div>
    );
}
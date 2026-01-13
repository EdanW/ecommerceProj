import { useState } from 'react';
import { Droplet, Moon, Footprints } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

export function WellnessWidget({ token }) {
    const [water, setWater] = useState(0);

    const addWater = async () => {
        try {
            // Optimistic UI update (update screen before waiting for server)
            setWater(prev => prev + 1);

            await axios.post(`${API_URL}/log_habit`,
                { habit_type: 'water', value: 1 },
                { headers: { Authorization: `Bearer ${token}` } }
            );
        } catch (error) {
            console.error("Failed to save habit");
        }
    };

    return (
        <div className="card wellness-card">
            <h3>Daily Habits</h3>

            {/* Hydration Row */}
            <div className="habit-row">
                <div className="icon-box blue"><Droplet size={20} /></div>
                <div className="habit-info">
                    <span>Stay Hydrated</span>
                    <span className="sub-info">{water} / 8 glasses</span>
                </div>
                <button className="add-btn" onClick={addWater}>+</button>
            </div>

            {/* Movement Row - Visual Only for Demo */}
            <div className="habit-row">
                <div className="icon-box green"><Footprints size={20} /></div>
                <div className="habit-info">
                    <span>Gentle Movement</span>
                    <span className="sub-info">15 min walk</span>
                </div>
                <div className="checkbox-circle"></div>
            </div>
        </div>
    );
}
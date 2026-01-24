import { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart as LineChartIcon, ScrollText } from 'lucide-react';
import {
    LineChart as RechartsLineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer
} from 'recharts';

const API_URL = 'http://localhost:8000';

const pad = (value) => String(value).padStart(2, '0');

const formatLocalDateTime = (date) => (
    `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`
);

const parseLocalDateTime = (value) => {
    if (!value) return null;
    const match = value.match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})$/);
    if (!match) return null;
    const day = Number(match[1]);
    const month = Number(match[2]);
    const year = Number(match[3]);
    const hours = Number(match[4]);
    const minutes = Number(match[5]);
    if (month < 1 || month > 12 || hours > 23 || minutes > 59) return null;
    const date = new Date(year, month - 1, day, hours, minutes, 0, 0);
    if (Number.isNaN(date.getTime())) return null;
    if (
        date.getFullYear() !== year
        || date.getMonth() !== month - 1
        || date.getDate() !== day
        || date.getHours() !== hours
        || date.getMinutes() !== minutes
    ) {
        return null;
    }
    return date.toISOString();
};

const formatLocalLabel = (value) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
};

const formatTime24 = (value) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false });
};

export function GlucoseChart({ token }) {
    const now = new Date();
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const [startLocal, setStartLocal] = useState(() => formatLocalDateTime(weekAgo));
    const [endLocal, setEndLocal] = useState(() => formatLocalDateTime(now));
    const [readings, setReadings] = useState([]);
    const [loading, setLoading] = useState(false);
    const [fetchError, setFetchError] = useState('');

    const startUtc = parseLocalDateTime(startLocal);
    const endUtc = parseLocalDateTime(endLocal);
    const validationError = !startUtc || !endUtc
        ? 'Please select a valid start and end time.'
        : (new Date(startUtc) > new Date(endUtc)
            ? 'Start time must be before end time.'
            : '');
    const displayError = validationError || fetchError;

    useEffect(() => {
        if (!token || validationError) return;

        let isActive = true;
        const fetchTrends = async () => {
            setLoading(true);
            setFetchError('');
            try {
                const res = await axios.get(`${API_URL}/glucose/trends`, {
                    params: { start: startUtc, end: endUtc },
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (isActive) {
                    setReadings(res.data.readings || []);
                }
            } catch (err) {
                console.error(err);
                if (isActive) {
                    setFetchError('Unable to load glucose trends.');
                }
            } finally {
                if (isActive) setLoading(false);
            }
        };

        fetchTrends();
        return () => { isActive = false; };
    }, [startUtc, endUtc, token, validationError]);

    const chartData = readings.map(reading => ({
        timestamp: reading.timestamp_utc,
        glucose_mg_dl: reading.glucose_mg_dl,
        tag: reading.tag,
        source: reading.source
    }));

    return (
        <div className="content">
            <div style={{display:'flex', alignItems:'center', gap:'10px', marginBottom:'15px'}}>
                <div style={{width:'48px', height:'48px', background:'#F5F5F5', borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center'}}>
                    <LineChartIcon size={26} color="#F48FB1"/>
                </div>
                <div>
                    <h3 className="mt-0">Glucose Trends</h3>
                    <p className="tiny-text" style={{marginTop:'4px'}}>Filter by time range to refresh the chart.</p>
                </div>
            </div>

            <div className="card" style={{marginBottom:'16px'}}>
                <div className="input-group" style={{gap:'10px', flexWrap:'wrap'}}>
                    <div style={{display:'flex', flexDirection:'column', gap:'6px', flex:'1 1 220px'}}>
                        <label className="tiny-text">Start (local)</label>
                        <input
                            className="modern-input"
                            type="text"
                            inputMode="numeric"
                            placeholder="dd/mm/yyyy hh:mm"
                            value={startLocal}
                            onChange={(event) => setStartLocal(event.target.value)}
                        />
                    </div>
                    <div style={{display:'flex', flexDirection:'column', gap:'6px', flex:'1 1 220px'}}>
                        <label className="tiny-text">End (local)</label>
                        <input
                            className="modern-input"
                            type="text"
                            inputMode="numeric"
                            placeholder="dd/mm/yyyy hh:mm"
                            value={endLocal}
                            onChange={(event) => setEndLocal(event.target.value)}
                        />
                    </div>
                </div>
                {displayError && <p className="tiny-text" style={{color:'#FF5252', marginTop:'8px'}}>{displayError}</p>}
            </div>

            <div className="card">
                {loading && <p className="tiny-text">Loading glucose data...</p>}
                {!loading && !displayError && chartData.length === 0 && (
                    <p className="tiny-text">No readings in this range yet.</p>
                )}
                {!loading && chartData.length > 0 && (
                    <ResponsiveContainer width="100%" height={260}>
                        <RechartsLineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="timestamp"
                                tickFormatter={formatTime24}
                                minTickGap={20}
                            />
                            <YAxis />
                            <Tooltip
                                labelFormatter={formatLocalLabel}
                                formatter={(value) => [`${value} mg/dL`, 'Glucose']}
                            />
                            <Line
                                type="monotone"
                                dataKey="glucose_mg_dl"
                                stroke="#F48FB1"
                                strokeWidth={2}
                                dot={false}
                            />
                        </RechartsLineChart>
                    </ResponsiveContainer>
                )}
            </div>
        </div>
    );
}

export function FoodLog() {
    return (
        <div className="content" style={{textAlign:'center', paddingTop:'100px'}}>
            <div style={{width:'80px', height:'80px', background:'#F5F5F5', borderRadius:'50%', margin:'0 auto 20px', display:'flex', alignItems:'center', justifyContent:'center'}}>
                <ScrollText size={40} color="#6FCF97"/>
            </div>
            <h3>Food Log</h3>
            <p className="tiny-text">Meal tracking coming soon...</p>
        </div>
    );
}
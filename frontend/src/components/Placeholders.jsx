import { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart as LineChartIcon, ScrollText } from 'lucide-react';
import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer
} from 'recharts';

const API_URL = 'http://localhost:8000';

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

const roundDownToHalfHour = (value) => {
    const rounded = new Date(value);
    const minutes = rounded.getMinutes();
    const roundedMinutes = minutes < 30 ? 0 : 30;
    rounded.setMinutes(roundedMinutes, 0, 0);
    return rounded;
};

const buildAxisTicks = (startMs, endMs, intervalMs) => {
    if (!startMs || !endMs || endMs <= startMs || !intervalMs) return null;
    const ticks = [];
    for (let current = startMs; current <= endMs; current += intervalMs) {
        ticks.push(current);
    }
    if (ticks[ticks.length - 1] !== endMs) {
        ticks.push(endMs);
    }
    return ticks;
};

export function GlucoseChart({ token }) {
    const [endTime] = useState(() => roundDownToHalfHour(new Date()));
    const [readings, setReadings] = useState([]);
    const [loading, setLoading] = useState(false);
    const [fetchError, setFetchError] = useState('');

    const startTime = new Date(endTime);
    startTime.setHours(8, 0, 0, 0);
    const startUtc = startTime.toISOString();
    const endUtc = endTime.toISOString();
    const startMs = startTime.getTime();
    const endMs = endTime.getTime();
    const axisTicks = buildAxisTicks(startMs, endMs, 2 * 60 * 60 * 1000);
    const displayError = fetchError;

    useEffect(() => {
        if (!token) return;

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
    }, [startUtc, endUtc, token]);

    const chartData = readings.map(reading => {
        const timestampMs = new Date(reading.timestamp_utc).getTime();
        return {
            timestamp: reading.timestamp_utc,
            timestamp_ms: Number.isNaN(timestampMs) ? null : timestampMs,
            glucose_mg_dl: reading.glucose_mg_dl,
            tag: reading.tag,
            source: reading.source
        };
    });
    const chartHeight = Math.max(260, Math.min(360, chartData.length * 6 + 120));

    return (
        <div className="content">
            <div style={{display:'flex', alignItems:'center', gap:'10px', marginBottom:'15px'}}>
                <div style={{width:'48px', height:'48px', background:'#F5F5F5', borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center'}}>
                    <LineChartIcon size={26} color="#6FCF97"/>
                </div>
                <div>
                    <h3 className="mt-0">Glucose Trends</h3>
                    <p className="tiny-text" style={{marginTop:'4px'}}>Today&apos;s readings from 08:00 to now.</p>
                </div>
            </div>

            <div className="card" style={{marginBottom:'16px'}}>
                {loading && <p className="tiny-text">Loading glucose data...</p>}
                {!loading && !displayError && chartData.length === 0 && (
                    <p className="tiny-text">No readings in this range yet.</p>
                )}
                {!loading && displayError && (
                    <p className="tiny-text" style={{color:'#FF5252'}}>{displayError}</p>
                )}
                {!loading && chartData.length > 0 && (
                    <ResponsiveContainer width="100%" height={chartHeight}>
                        <ScatterChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="timestamp_ms"
                                tickFormatter={formatTime24}
                                minTickGap={20}
                                type="number"
                                scale="time"
                                domain={startMs && endMs ? [startMs, endMs] : ['auto', 'auto']}
                                ticks={axisTicks || undefined}
                            />
                            <YAxis dataKey="glucose_mg_dl" domain={[50, 'auto']} />
                            <Tooltip
                                content={({ active, payload }) => {
                                    if (!active || !payload?.length) return null;
                                    const point = payload[0]?.payload;
                                    if (!point) return null;
                                    const timeLabel = point.timestamp_ms ? formatTime24(point.timestamp_ms) : '';
                                    const suffix = timeLabel ? ` @ ${timeLabel}` : '';
                                    return (
                                        <div
                                            className="custom-tooltip"
                                            style={{
                                                background: '#FFFFFF',
                                                border: '1px solid #E0E0E0',
                                                borderRadius: '8px',
                                                padding: '8px 12px',
                                                boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
                                            }}
                                        >
                                            <p style={{ margin: 0, fontSize: '14px', color: '#111827' }}>
                                                {`Glucose: ${point.glucose_mg_dl} mg/dL${suffix}`}
                                            </p>
                                        </div>
                                    );
                                }}
                            />
                            <Scatter data={chartData} fill="#6FCF97" />
                        </ScatterChart>
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
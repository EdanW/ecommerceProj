// Health dashboard widgets: GlucoseChart (scatter plot) and FoodLog (meal tracker)
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

// --- Formatting helpers for chart axis labels and tooltips ---
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

// Snap a date down to the nearest :00 or :30 for a clean chart boundary
const roundDownToHalfHour = (value) => {
    const rounded = new Date(value);
    const minutes = rounded.getMinutes();
    const roundedMinutes = minutes < 30 ? 0 : 30;
    rounded.setMinutes(roundedMinutes, 0, 0);
    return rounded;
};

// Generate evenly-spaced tick marks between start and end (ms timestamps)
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

// Displays today's glucose readings as a scatter chart (08:00 → now)
export function GlucoseChart({ token }) {
    const [endTime] = useState(() => roundDownToHalfHour(new Date()));
    const [readings, setReadings] = useState([]);
    const [loading, setLoading] = useState(false);
    const [fetchError, setFetchError] = useState('');

    // Time window: today 08:00 up to the current half-hour
    const startTime = new Date(endTime);
    startTime.setHours(8, 0, 0, 0);
    //handle post midnight checks
    if (endTime < startTime) {
        startTime.setDate(startTime.getDate() - 1);
    }
    const startUtc = startTime.toISOString();
    const endUtc = endTime.toISOString();
    const startMs = startTime.getTime();
    const endMs = endTime.getTime();
    const axisTicks = buildAxisTicks(startMs, endMs, 2 * 60 * 60 * 1000);
    const displayError = fetchError;

    // Fetch glucose readings from the API whenever the time window or token changes
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

    // Transform API readings into chart-friendly objects with ms timestamps
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

// Meal logging form + display of the most recent entry for today
export function FoodLog({ token }) {
    const MAX_NOTE_LENGTH = 200;
    const [mealTime, setMealTime] = useState('');
    const [note, setNote] = useState('');
    const [latestEntry, setLatestEntry] = useState(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const noteRemaining = MAX_NOTE_LENGTH - note.length;

    // On mount, fetch the latest food log entry for today
    useEffect(() => {
        if (!token) return;
        let isActive = true;

        const fetchLatest = async () => {
            setLoading(true);
            setError('');
            try {
                const res = await axios.get(`${API_URL}/food_logs/today/latest`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (isActive) {
                    setLatestEntry(res.data.entry || null);
                }
            } catch (err) {
                console.error(err);
                if (isActive) {
                    setError("Unable to load today's food log.");
                }
            } finally {
                if (isActive) setLoading(false);
            }
        };

        fetchLatest();
        return () => { isActive = false; };
    }, [token]);

    // Re-fetch latest entry (called after a successful submit)
    const refreshLatest = async () => {
        setLoading(true);
        setError('');
        try {
            const res = await axios.get(`${API_URL}/food_logs/today/latest`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setLatestEntry(res.data.entry || null);
        } catch (err) {
            console.error(err);
            setError(err.response?.data?.detail || "Unable to load today's food log.");
        } finally {
            setLoading(false);
        }
    };

    // Validate inputs, POST the new food log, then refresh the displayed entry
    const submitLog = async (event) => {
        event.preventDefault();
        if (!mealTime) {
            setError('Please add a meal time.');
            return;
        }
        if (note.length > MAX_NOTE_LENGTH) {
            setError(`Notes must be ${MAX_NOTE_LENGTH} characters or fewer.`);
            return;
        }

        setSaving(true);
        setError('');
        try {
            const res = await axios.post(`${API_URL}/food_logs`, {
                meal_time: mealTime,
                note: note.trim()
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const newEntry = res.data.entry;
            setMealTime('');
            setNote('');
            await refreshLatest();
        } catch (err) {
            console.error(err);
            setError(err.response?.data?.detail || 'Unable to save food log.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="content">
            <div style={{display:'flex', alignItems:'center', gap:'10px', marginBottom:'15px'}}>
                <div style={{width:'48px', height:'48px', background:'#F5F5F5', borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center'}}>
                    <ScrollText size={26} color="#6FCF97"/>
                </div>
                <div>
                    <h3 className="mt-0">Food Log</h3>
                    <p className="tiny-text" style={{marginTop:'4px'}}>Add today&apos;s meals and notes.</p>
                </div>
            </div>

            <div className="card" style={{marginBottom:'16px'}}>
                <form onSubmit={submitLog}>
                    <label className="tiny-text" style={{display:'block', marginBottom:'6px'}}>Meal time</label>
                    <input
                        type="time"
                        lang="en-GB"
                        step="60"
                        className="modern-input"
                        value={mealTime}
                        onChange={event => setMealTime(event.target.value)}
                        required
                    />

                    <label className="tiny-text" style={{display:'block', margin:'14px 0 6px'}}>What did you eat?</label>
                    <textarea
                        className="modern-input"
                        rows={3}
                        maxLength={MAX_NOTE_LENGTH}
                        value={note}
                        onChange={event => setNote(event.target.value)}
                        placeholder="Add notes about your meal..."
                        style={{resize:'vertical'}}
                    />
                    <div className="flex-between" style={{marginTop:'6px'}}>
                        <span className="tiny-text">{noteRemaining} characters left</span>
                        {error && <span className="tiny-text" style={{color:'#FF5252'}}>{error}</span>}
                    </div>

                    <button className="crave-btn" type="submit" disabled={saving} style={{marginTop:'16px', opacity: saving ? 0.7 : 1}}>
                        {saving ? 'Saving...' : 'Submit'}
                    </button>
                </form>
            </div>

            <div className="card">
                {loading && <p className="tiny-text">Loading today&apos;s entries...</p>}
                {!loading && !latestEntry && (
                    <p className="tiny-text">No meals logged yet today.</p>
                )}
                {!loading && latestEntry && (
                    <div style={{borderBottom:'1px solid #F0F0F0', paddingBottom:'10px'}}>
                        <div className="flex-between">
                            <span style={{fontWeight:'bold'}}>{latestEntry.meal_time}</span>
                            <span className="tiny-text">{latestEntry.created_date}</span>
                        </div>
                        {latestEntry.note && (
                            <p className="tiny-text" style={{marginTop:'6px'}}>{latestEntry.note}</p>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
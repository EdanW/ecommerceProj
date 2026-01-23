import { LineChart, ScrollText } from 'lucide-react';

export function GlucoseChart() {
    return (
        <div className="content" style={{textAlign:'center', paddingTop:'100px'}}>
            <div style={{width:'80px', height:'80px', background:'#F5F5F5', borderRadius:'50%', margin:'0 auto 20px', display:'flex', alignItems:'center', justifyContent:'center'}}>
                <LineChart size={40} color="#F48FB1"/>
            </div>
            <h3>Glucose Trends</h3>
            <p className="tiny-text">Chart coming soon...</p>
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
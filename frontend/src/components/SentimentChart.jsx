import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORS = {
  positive: '#10b981',
  negative: '#ef4444',
  neutral: '#6b7280'
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="card" style={{ padding: '0.75rem', minWidth: '180px' }}>
        <p style={{ fontWeight: 600, marginBottom: '0.5rem', color: '#f8fafc' }}>
          {label}
        </p>
        {payload.map((entry, index) => (
          <p key={index} style={{ color: entry.color, fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            {entry.name.charAt(0).toUpperCase() + entry.name.slice(1)}: <span style={{ fontWeight: 600 }}>{entry.value}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function SentimentChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="card">
        <h3 className="card-title">Sentiment Trends</h3>
        <div style={{ 
          height: '300px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: '#94a3b8' 
        }}>
          No data available
        </div>
      </div>
    );
  }

  // Transform data for the chart
  const chartData = data.map(item => {
    const timestamp = new Date(item.timestamp);
    const time = timestamp.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
    
    return {
      time,
      positive: item.positive || 0,
      negative: item.negative || 0,
      neutral: item.neutral || 0,
    };
  });

  return (
    <div className="card">
      <h3 className="card-title">Sentiment Trends</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis 
            dataKey="time" 
            stroke="#94a3b8"
            style={{ fontSize: '0.75rem' }}
          />
          <YAxis 
            stroke="#94a3b8"
            style={{ fontSize: '0.75rem' }}
            label={{ value: 'Posts', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            formatter={(value) => value.charAt(0).toUpperCase() + value.slice(1)}
            wrapperStyle={{ paddingTop: '10px' }}
          />
          <Line 
            type="monotone" 
            dataKey="positive" 
            stroke={COLORS.positive} 
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line 
            type="monotone" 
            dataKey="negative" 
            stroke={COLORS.negative} 
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line 
            type="monotone" 
            dataKey="neutral" 
            stroke={COLORS.neutral} 
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

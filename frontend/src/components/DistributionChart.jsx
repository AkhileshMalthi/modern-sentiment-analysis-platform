import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

const COLORS = {
  positive: '#10b981',
  negative: '#ef4444',
  neutral: '#6b7280'
};

const RADIAN = Math.PI / 180;
const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text 
      x={x} 
      y={y} 
      fill="white" 
      textAnchor={x > cx ? 'start' : 'end'} 
      dominantBaseline="central"
      style={{ fontSize: '14px', fontWeight: 'bold' }}
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="card" style={{ padding: '0.75rem', minWidth: '150px' }}>
        <p style={{ fontWeight: 600, marginBottom: '0.25rem', textTransform: 'capitalize' }}>
          {data.name}
        </p>
        <p style={{ color: '#94a3b8' }}>
          Count: <span style={{ color: '#f8fafc', fontWeight: 600 }}>{data.value}</span>
        </p>
        <p style={{ color: '#94a3b8' }}>
          Percentage: <span style={{ color: '#f8fafc', fontWeight: 600 }}>{data.percentage}%</span>
        </p>
      </div>
    );
  }
  return null;
};

export default function DistributionChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="card">
        <h3 className="card-title">Sentiment Distribution</h3>
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

  const chartData = data.map(item => ({
    name: item.sentiment,
    value: item.count,
    percentage: item.percentage
  }));

  return (
    <div className="card">
      <h3 className="card-title">Sentiment Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomizedLabel}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[entry.name]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            formatter={(value) => value.charAt(0).toUpperCase() + value.slice(1)}
            wrapperStyle={{ paddingTop: '20px' }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

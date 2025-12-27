import { useState, useEffect, useRef } from 'react';
import DistributionChart from './DistributionChart';
import SentimentChart from './SentimentChart';
import LiveFeed from './LiveFeed';
import { fetchDistribution, fetchAggregateData, fetchPosts, connectWebSocket } from '../services/api';

export default function Dashboard() {
  const [distributionData, setDistributionData] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [recentPosts, setRecentPosts] = useState([]);
  const [metrics, setMetrics] = useState({
    total: 0,
    positive: 0,
    negative: 0,
    neutral: 0
  });
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Fetch initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [distribution, aggregate, posts] = await Promise.all([
          fetchDistribution(24),
          fetchAggregateData('hour'),
          fetchPosts(20, 0)
        ]);

        // Transform distribution object to array format
        const distArray = Object.entries(distribution.distribution || {}).map(([sentiment, count]) => ({
          sentiment,
          count,
          percentage: distribution.percentages?.[sentiment] || 0
        }));

        // Transform aggregate data to match chart expectations
        const transformedTrendData = (aggregate.data || []).map(item => ({
          timestamp: item.timestamp,
          positive: item.positive_count || 0,
          negative: item.negative_count || 0,
          neutral: item.neutral_count || 0,
        }));

        setDistributionData(distArray);
        setTrendData(transformedTrendData);
        setRecentPosts(posts.posts || []);

        // Update metrics from distribution
        setMetrics({
          total: distribution.total || 0,
          positive: distribution.distribution?.positive || 0,
          negative: distribution.distribution?.negative || 0,
          neutral: distribution.distribution?.neutral || 0
        });

        setLastUpdate(new Date());
        setLoading(false);
      } catch (err) {
        console.error('Error loading initial data:', err);
        setError('Failed to load dashboard data. Please refresh the page.');
        setLoading(false);
      }
    };

    loadInitialData();
  }, []);

  // WebSocket connection
  useEffect(() => {
    const connectWS = () => {
      try {
        setConnectionStatus('connecting');

        wsRef.current = connectWebSocket(
          // onMessage
          (data) => {
            setConnectionStatus('connected');
            setLastUpdate(new Date()); // Set lastUpdate on WebSocket message

            if (data.type === 'new_post') {
              // Add new post to the feed
              setRecentPosts(prev => [data.data, ...prev].slice(0, 20));

              // Update metrics
              setMetrics(prev => ({
                total: prev.total + 1,
                positive: prev.positive + (data.data.sentiment?.label === 'positive' ? 1 : 0),
                negative: prev.negative + (data.data.sentiment?.label === 'negative' ? 1 : 0),
                neutral: prev.neutral + (data.data.sentiment?.label === 'neutral' ? 1 : 0)
              }));

              // Update distribution data
              setDistributionData(prev => {
                const newData = [...prev];
                const sentimentIndex = newData.findIndex(item => item.sentiment === data.data.sentiment?.label);

                if (sentimentIndex >= 0) {
                  newData[sentimentIndex] = {
                    ...newData[sentimentIndex],
                    count: newData[sentimentIndex].count + 1
                  };
                } else {
                  newData.push({
                    sentiment: data.data.sentiment?.label,
                    count: 1,
                    percentage: 0
                  });
                }

                // Recalculate percentages
                const total = newData.reduce((sum, item) => sum + item.count, 0);
                return newData.map(item => ({
                  ...item,
                  percentage: ((item.count / total) * 100).toFixed(2)
                }));
              });
            }
          },
          // onError
          (error) => {
            console.error('WebSocket error:', error);
            setConnectionStatus('error');
          },
          // onClose
          (event) => {
            console.log('WebSocket closed:', event.code);
            setConnectionStatus('disconnected');

            // Attempt to reconnect after 5 seconds
            if (reconnectTimeoutRef.current) {
              clearTimeout(reconnectTimeoutRef.current);
            }
            reconnectTimeoutRef.current = setTimeout(() => {
              console.log('Attempting to reconnect WebSocket...');
              connectWS();
            }, 5000);
          }
        );
      } catch (err) {
        console.error('Failed to connect WebSocket:', err);
        setConnectionStatus('error');
      }
    };

    connectWS();

    // Cleanup
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Periodic data refresh (every 60 seconds)
  useEffect(() => {
    const refreshInterval = setInterval(async () => {
      try {
        const [distribution, aggregate] = await Promise.all([
          fetchDistribution(24),
          fetchAggregateData('hour')
        ]);

        // Transform distribution object to array format
        const distArray = Object.entries(distribution.distribution || {}).map(([sentiment, count]) => ({
          sentiment,
          count,
          percentage: distribution.percentages?.[sentiment] || 0
        }));

        // Transform aggregate data to match chart expectations
        const transformedTrendData = (aggregate.data || []).map(item => ({
          timestamp: item.timestamp,
          positive: item.positive_count || 0,
          negative: item.negative_count || 0,
          neutral: item.neutral_count || 0,
        }));

        setDistributionData(distArray);
        setTrendData(transformedTrendData);
      } catch (err) {
        console.error('Error refreshing data:', err);
      }
    }, 60000);

    return () => clearInterval(refreshInterval);
  }, []);

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        fontSize: '1.5rem',
        fontWeight: 'bold',
        color: '#3b82f6'
      }}>
        Loading dashboard data...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div style={{ fontSize: '1.125rem', color: '#ef4444' }}>
          {error}
        </div>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            fontSize: '1rem'
          }}
        >
          Reload
        </button>
      </div>
    );
  }

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return '#10b981';
      case 'connecting': return '#f59e0b';
      case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      padding: '2rem',
      backgroundColor: '#0f172a'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '0.5rem'
        }}>
          <h1 style={{ fontSize: '2rem', fontWeight: 700, color: '#f8fafc' }}>
            Real-Time Sentiment Analysis Dashboard
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Status:</span>
              <span
                className={connectionStatus === 'connected' ? 'status-indicator status-live' : 'status-indicator status-disconnected'}
                style={{ backgroundColor: getStatusColor() }}
              />
              <span style={{ fontSize: '0.875rem', color: connectionStatus === 'connected' ? '#10b981' : '#94a3b8', fontWeight: 500 }}>
                {connectionStatus === 'connected' ? 'Live' : connectionStatus}
              </span>
            </div>
            {lastUpdate && (
              <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>
                Last Update: {lastUpdate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
              </div>
            )}
          </div>
        </div>
        <p style={{ color: '#94a3b8' }}>
          Monitor sentiment analysis in real-time across social media platforms
        </p>
      </div>

      {/* Distribution Chart + Live Feed Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '1.5rem',
        marginBottom: '1.5rem'
      }}>
        <DistributionChart data={distributionData} />
        <LiveFeed posts={recentPosts} />
      </div>

      {/* Sentiment Trend Chart (Full Width) */}
      <div style={{ marginBottom: '1.5rem' }}>
        <SentimentChart data={trendData} />
      </div>

      {/* Metrics Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem'
      }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
            Total Posts
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#f8fafc' }}>
            {metrics.total.toLocaleString()}
          </div>
        </div>

        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
            Positive
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#10b981' }}>
            {metrics.positive.toLocaleString()}
          </div>
        </div>

        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
            Negative
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#ef4444' }}>
            {metrics.negative.toLocaleString()}
          </div>
        </div>

        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '0.875rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
            Neutral
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#6b7280' }}>
            {metrics.neutral.toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
}

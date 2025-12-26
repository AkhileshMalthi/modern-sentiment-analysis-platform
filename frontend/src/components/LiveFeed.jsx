import { useEffect, useRef } from 'react';

const SENTIMENT_COLORS = {
  positive: '#10b981',
  negative: '#ef4444',
  neutral: '#6b7280'
};

export default function LiveFeed({ posts }) {
  const feedRef = useRef(null);
  const prevPostsLength = useRef(posts.length);

  useEffect(() => {
    // Auto-scroll when new posts arrive
    if (feedRef.current && posts.length > prevPostsLength.current) {
      feedRef.current.scrollTop = 0;
    }
    prevPostsLength.current = posts.length;
  }, [posts]);

  if (!posts || posts.length === 0) {
    return (
      <div className="card">
        <h3 className="card-title">Live Feed</h3>
        <div style={{ 
          height: '400px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: '#94a3b8' 
        }}>
          Waiting for posts...
        </div>
      </div>
    );
  }

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    
    if (diffSecs < 60) return `${diffSecs}s ago`;
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    
    return date.toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const truncateText = (text, maxLength = 100) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + '...';
  };

  return (
    <div className="card">
      <h3 className="card-title">Live Feed</h3>
      <div 
        ref={feedRef}
        style={{ 
          height: '400px', 
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem'
        }}
      >
        {posts.map((post) => (
          <div 
            key={post.id}
            style={{
              backgroundColor: '#0f172a',
              padding: '1rem',
              borderRadius: '0.375rem',
              borderLeft: `3px solid ${SENTIMENT_COLORS[post.sentiment?.label] || '#6b7280'}`,
              transition: 'all 0.2s',
            }}
          >
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'flex-start',
              marginBottom: '0.5rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span 
                  style={{ 
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: SENTIMENT_COLORS[post.sentiment?.label],
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}
                >
                  {post.sentiment?.label}
                </span>
                {post.sentiment?.emotion && (
                  <span 
                    style={{ 
                      fontSize: '0.75rem',
                      color: '#94a3b8',
                      backgroundColor: '#1e293b',
                      padding: '0.125rem 0.5rem',
                      borderRadius: '0.25rem'
                    }}
                  >
                    {post.sentiment.emotion}
                  </span>
                )}
              </div>
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                {formatTimestamp(post.timestamp || post.created_at)}
              </span>
            </div>
            
            <p style={{ 
              fontSize: '0.875rem', 
              color: '#cbd5e1',
              lineHeight: '1.5'
            }}>
              {truncateText(post.content)}
            </p>
            
            {post.sentiment?.confidence !== undefined && (
              <div style={{ marginTop: '0.5rem' }}>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  fontSize: '0.75rem',
                  color: '#94a3b8',
                  marginBottom: '0.25rem'
                }}>
                  <span>Confidence</span>
                  <span>{(post.sentiment.confidence * 100).toFixed(1)}%</span>
                </div>
                <div style={{ 
                  width: '100%', 
                  height: '4px', 
                  backgroundColor: '#1e293b',
                  borderRadius: '2px',
                  overflow: 'hidden'
                }}>
                  <div 
                    style={{ 
                      width: `${post.sentiment.confidence * 100}%`,
                      height: '100%',
                      backgroundColor: SENTIMENT_COLORS[post.sentiment.label],
                      transition: 'width 0.3s ease'
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

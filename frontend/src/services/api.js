const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

/**
 * Fetch posts with optional filters and pagination
 */
export async function fetchPosts(limit = 10, offset = 0, filters = {}) {
  try {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
      ...Object.fromEntries(
        Object.entries(filters).filter(([_, value]) => value !== undefined && value !== null && value !== '')
      )
    });

    const response = await fetch(`${API_BASE_URL}/api/posts?${params}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching posts:', error);
    throw error;
  }
}

/**
 * Fetch sentiment distribution data
 */
export async function fetchDistribution(hours = 24) {
  try {
    const params = new URLSearchParams({ hours: hours.toString() });
    const response = await fetch(`${API_BASE_URL}/api/sentiment/distribution?${params}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching distribution:', error);
    throw error;
  }
}

/**
 * Fetch aggregated sentiment data
 */
export async function fetchAggregateData(period = 'hour', startDate = null, endDate = null) {
  try {
    const params = new URLSearchParams({ period });
    
    if (startDate) {
      params.append('start_date', startDate);
    }
    if (endDate) {
      params.append('end_date', endDate);
    }
    
    const response = await fetch(`${API_BASE_URL}/api/sentiment/aggregate?${params}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching aggregate data:', error);
    throw error;
  }
}

/**
 * Connect to WebSocket for real-time sentiment updates
 */
export function connectWebSocket(onMessage, onError = null, onClose = null) {
  const ws = new WebSocket(`${WS_BASE_URL}/ws/sentiment`);
  
  ws.onopen = () => {
    console.log('WebSocket connected');
  };
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      if (onError) onError(error);
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    if (onError) onError(error);
  };
  
  ws.onclose = (event) => {
    console.log('WebSocket disconnected:', event.code, event.reason);
    if (onClose) onClose(event);
  };
  
  return ws;
}

/**
 * Check API health
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error checking health:', error);
    throw error;
  }
}

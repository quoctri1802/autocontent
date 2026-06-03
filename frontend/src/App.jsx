import React, { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : window.location.origin);

export default function App() {
  const [activeTab, setActiveTab] = useState('overview'); // overview | trends | articles | videos | cookies
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  
  // Data States
  const [trends, setTrends] = useState([]);
  const [articles, setArticles] = useState([]);
  const [fbPosts, setFbPosts] = useState([]);
  const [videoScripts, setVideoScripts] = useState([]);
  
  // Input/Generation States
  const [topicInput, setTopicInput] = useState('');
  const [generatedArticle, setGeneratedArticle] = useState(null);
  const [editingArticle, setEditingArticle] = useState(null);
  
  // Video States
  const [videoTopic, setVideoTopic] = useState('');
  const [generatedScript, setGeneratedScript] = useState(null);
  const [compilingScriptId, setCompilingScriptId] = useState(null);
  
  // System State
  const [missingKeys, setMissingKeys] = useState([]);

  // Fetch initial system status and data
  useEffect(() => {
    fetchSystemStatus();
    fetchTrends();
    fetchArticles();
    fetchVideoScripts();
    fetchFacebookPosts();
    
    // Poll for video statuses every 7 seconds
    const interval = setInterval(() => {
      fetchVideoScripts(false);
    }, 7000);
    return () => clearInterval(interval);
  }, []);

  const showToast = (msg, type = 'success') => {
    if (type === 'success') {
      setSuccessMessage(msg);
      setTimeout(() => setSuccessMessage(''), 4000);
    } else {
      setErrorMessage(msg);
      setTimeout(() => setErrorMessage(''), 5000);
    }
  };

  const fetchSystemStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/`);
      if (res.ok) {
        const data = await res.json();
        setMissingKeys(data.missing_keys || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchTrends = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/trends`);
      if (res.ok) setTrends(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchArticles = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/articles`);
      if (res.ok) setArticles(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchFacebookPosts = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/facebook-posts`);
      if (res.ok) setFbPosts(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchVideoScripts = async (showLoading = true) => {
    try {
      const res = await fetch(`${API_BASE}/api/video-scripts`);
      if (res.ok) setVideoScripts(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const triggerFetchTrends = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/trends/fetch`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        showToast(`Đã tìm kiếm xu hướng thành công! Đã thêm ${data.items_added} từ khóa hot.`);
        fetchTrends();
      } else {
        showToast('Lỗi cập nhật xu hướng.', 'error');
      }
    } catch (e) {
      showToast('Không kết nối được server.', 'error');
    } finally {
      setLoading(false);
    }
  };

  // --- ARTICLE FUNCTIONS ---
  const handleGenerateArticle = async () => {
    if (!topicInput.trim()) return;
    setLoading(true);
    setGeneratedArticle(null);
    try {
      const res = await fetch(`${API_BASE}/api/articles/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topicInput })
      });
      if (res.ok) {
        const data = await res.json();
        setGeneratedArticle(data);
        setEditingArticle(data);
        showToast('Đã sinh bài viết AI nháp thành công! Vui lòng duyệt lại bên dưới.');
        fetchArticles();
      } else {
        showToast('Gemini lỗi trong quá trình sinh bài viết.', 'error');
      }
    } catch (e) {
      showToast('Lỗi kết nối.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateArticle = async () => {
    if (!editingArticle || !editingArticle.id) return;
    try {
      const res = await fetch(`${API_BASE}/api/articles/${editingArticle.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingArticle)
      });
      if (res.ok) {
        showToast('Đã lưu bài viết nháp thành công.');
        fetchArticles();
      } else {
        showToast('Lỗi lưu nháp.', 'error');
      }
    } catch (e) {
      showToast('Lỗi kết nối.', 'error');
    }
  };

  const handlePublishArticle = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/publish/website/${id}`, { method: 'POST' });
      if (res.ok) {
        showToast('Đã xuất bản bài viết lên Website thành công!');
        fetchArticles();
        if (editingArticle && editingArticle.id === id) {
          setEditingArticle({ ...editingArticle, status: 'published' });
        }
      } else {
        const errorData = await res.json();
        showToast(`Xuất bản thất bại: ${errorData.detail}`, 'error');
      }
    } catch (e) {
      showToast('Lỗi kết nối.', 'error');
    }
  };

  const handleDeleteArticle = async (id) => {
    if (!confirm('Bạn có chắc chắn muốn xóa bài viết này không?')) return;
    try {
      const res = await fetch(`${API_BASE}/api/articles/${id}`, { method: 'DELETE' });
      if (res.ok) {
        showToast('Đã xóa bài viết.');
        fetchArticles();
        if (editingArticle && editingArticle.id === id) {
          setEditingArticle(null);
          setGeneratedArticle(null);
        }
      }
    } catch (e) {
      showToast('Lỗi kết nối.', 'error');
    }
  };

  // --- VIDEO FUNCTIONS ---
  const handleGenerateScript = async () => {
    if (!videoTopic.trim()) return;
    setLoading(true);
    setGeneratedScript(null);
    try {
      const res = await fetch(`${API_BASE}/api/video-scripts/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: videoTopic })
      });
      if (res.ok) {
        const data = await res.json();
        setGeneratedScript(data);
        showToast('Đã tạo kịch bản video. Hãy ấn Compile Video để render hình âm!');
        fetchVideoScripts();
      } else {
        showToast('Lỗi tạo kịch bản từ Gemini.', 'error');
      }
    } catch (e) {
      showToast('Lỗi kết nối.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCompileVideo = async (scriptId) => {
    try {
      const res = await fetch(`${API_BASE}/api/video-scripts/${scriptId}/compile`, { method: 'POST' });
      if (res.ok) {
        showToast('Bắt đầu render video dưới nền. Quá trình mất khoảng 1-2 phút.');
        setCompilingScriptId(scriptId);
        fetchVideoScripts();
      }
    } catch (e) {
      showToast('Lỗi kết nối.', 'error');
    }
  };

  const handlePublishVideo = async (scriptId, platform) => {
    try {
      const res = await fetch(`${API_BASE}/api/publish/video/${scriptId}?platform=${platform}`, { method: 'POST' });
      if (res.ok) {
        showToast(`Đã xếp hàng tác vụ tải video lên ${platform.toUpperCase()} ngầm.`);
      } else {
        const error = await res.json();
        showToast(`Lỗi: ${error.detail}`, 'error');
      }
    } catch (e) {
      showToast('Lỗi kết nối.', 'error');
    }
  };

  const handleDeleteScript = async (id) => {
    if (!confirm('Bạn muốn xóa kịch bản này?')) return;
    try {
      const res = await fetch(`${API_BASE}/api/video-scripts/${id}`, { method: 'DELETE' });
      if (res.ok) {
        showToast('Đã xóa kịch bản.');
        fetchVideoScripts();
        if (generatedScript && generatedScript.id === id) setGeneratedScript(null);
      }
    } catch (e) {
      showToast('Lỗi kết nối.', 'error');
    }
  };

  // --- COOKIE UPLOAD ---
  const handleCookieUpload = async (e, platform) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await fetch(`${API_BASE}/api/cookies/${platform}`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        showToast(`Tải file cookies cho ${platform.toUpperCase()} thành công!`);
      } else {
        showToast('Upload cookies thất bại.', 'error');
      }
    } catch (e) {
      showToast('Lỗi kết nối.', 'error');
    }
  };

  return (
    <div className="dashboard-grid">
      {/* Background neon spheres */}
      <div className="blur-container">
        <div className="blur-circle circle-1"></div>
        <div className="blur-circle circle-2"></div>
        <div className="blur-circle circle-3"></div>
      </div>

      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img 
              src="https://mebimthongthai.io.vn/viet_mom_baby.png" 
              alt="Logo" 
              style={{ width: '45px', height: '45px', borderRadius: '50%' }}
            />
            <div>
              <h2 style={{ fontSize: '18px', color: 'white' }}>MBTE Engine</h2>
              <span style={{ fontSize: '12px', color: 'var(--color-primary)' }}>Mẹ Bỉm Thông Thái</span>
            </div>
          </div>
          
          <nav className="sidebar-menu">
            <div 
              className={`menu-item ${activeTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2v-4z" />
              </svg>
              Tổng quan
            </div>
            <div 
              className={`menu-item ${activeTab === 'trends' ? 'active' : ''}`}
              onClick={() => setActiveTab('trends')}
            >
              <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              Săn xu hướng
            </div>
            <div 
              className={`menu-item ${activeTab === 'articles' ? 'active' : ''}`}
              onClick={() => setActiveTab('articles')}
            >
              <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
              Trình tạo bài viết
            </div>
            <div 
              className={`menu-item ${activeTab === 'videos' ? 'active' : ''}`}
              onClick={() => setActiveTab('videos')}
            >
              <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 00-2 2z" />
              </svg>
              Kịch bản & Video
            </div>
            <div 
              className={`menu-item ${activeTab === 'cookies' ? 'active' : ''}`}
              onClick={() => setActiveTab('cookies')}
            >
              <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              Cấu hình Cookies
            </div>
          </nav>
        </div>
        
        {/* Footer info */}
        <div style={{ padding: '10px 0', borderTop: '1px solid rgba(255,255,255,0.05)', fontSize: '12px', color: '#6a6575' }}>
          <span>VPS Mode 24/7 Enabled</span>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Alerts / Toast Messages */}
        {successMessage && (
          <div className="glass-card animate-fade-in" style={{ position: 'fixed', right: '40px', bottom: '40px', background: 'rgba(72,192,150,0.9)', borderLeft: '5px solid #238b68', zIndex: 1000, padding: '16px 24px', color: 'white', fontWeight: 500, display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span>✅ {successMessage}</span>
          </div>
        )}
        {errorMessage && (
          <div className="glass-card animate-fade-in" style={{ position: 'fixed', right: '40px', bottom: '40px', background: 'rgba(223,71,89,0.9)', borderLeft: '5px solid #9c1f2e', zIndex: 1000, padding: '16px 24px', color: 'white', fontWeight: 500, display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span>⚠️ {errorMessage}</span>
          </div>
        )}

        {/* Global Warnings for missing credentials */}
        {missingKeys.length > 0 && (
          <div className="glass-card animate-fade-in" style={{ background: 'rgba(255, 92, 122, 0.1)', borderColor: 'var(--color-primary)', marginBottom: '30px', padding: '16px 24px', borderRadius: '15px' }}>
            <h4 style={{ color: 'var(--color-primary)', marginBottom: '5px', fontWeight: 600 }}>⚠️ Cảnh báo thiết lập chưa hoàn tất!</h4>
            <p style={{ fontSize: '13px', color: '#c9c7cd' }}>
              Thiếu các khoá môi trường cấu hình: <strong style={{ color: 'white' }}>{missingKeys.join(', ')}</strong>. Hệ thống sẽ tạm thời sinh dữ liệu mô phỏng (mock data) cho đến khi các biến trên được cấu hình vào file `.env`.
            </p>
          </div>
        )}

        {/* LOADING SCREEN OVERLAY */}
        {loading && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(7,4,10,0.85)', zIndex: 9999, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ width: '80px', height: '80px', border: '5px solid rgba(255,92,122,0.1)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
            <h3 style={{ marginTop: '20px', color: 'white', fontWeight: 500 }}>AI Mẹ Bỉm sữa đang suy nghĩ...</h3>
            <p style={{ fontSize: '13px', color: '#9c97aa', marginTop: '5px' }}>Vui lòng đợi trong giây lát</p>
            <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {/* 1. OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="animate-fade-in">
            <div className="section-header">
              <div>
                <h1 style={{ fontSize: '28px' }}>Xin chào Admin!</h1>
                <p style={{ color: '#9c97aa', fontSize: '14px' }}>Bảng điều khiển hệ thống nội dung tự động Mẹ Bỉm Thông Thái.</p>
              </div>
              <button className="btn btn-primary" onClick={triggerFetchTrends}>
                🔄 Cập nhật xu hướng ngay
              </button>
            </div>

            {/* Quick Analytics Cards */}
            <div className="grid-cols-3" style={{ marginBottom: '40px' }}>
              <div className="glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '14px', color: '#9c97aa' }}>Bài viết Website</span>
                  <span style={{ fontSize: '24px' }}>📝</span>
                </div>
                <h2 style={{ fontSize: '32px', margin: '15px 0 5px 0' }}>{articles.length}</h2>
                <p style={{ fontSize: '12px', color: 'var(--color-secondary)' }}>
                  {articles.filter(a => a.status === 'published').length} bài đã đăng • {articles.filter(a => a.status === 'draft').length} nháp
                </p>
              </div>

              <div className="glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '14px', color: '#9c97aa' }}>Kịch bản Video</span>
                  <span style={{ fontSize: '24px' }}>🎬</span>
                </div>
                <h2 style={{ fontSize: '32px', margin: '15px 0 5px 0' }}>{videoScripts.length}</h2>
                <p style={{ fontSize: '12px', color: 'var(--color-secondary)' }}>
                  {videoScripts.filter(v => v.status === 'rendered').length} video đã render hoàn tất
                </p>
              </div>

              <div className="glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '14px', color: '#9c97aa' }}>Xu hướng hot phát hiện</span>
                  <span style={{ fontSize: '24px' }}>🔥</span>
                </div>
                <h2 style={{ fontSize: '32px', margin: '15px 0 5px 0' }}>{trends.length}</h2>
                <p style={{ fontSize: '12px', color: 'var(--color-primary)' }}>
                  {trends.filter(t => t.is_viral).length} xu hướng có độ viral cao
                </p>
              </div>
            </div>

            {/* Recent Activities List */}
            <div className="glass-card">
              <h3 style={{ fontSize: '18px', marginBottom: '20px' }}>Lịch sử tạo nội dung gần đây</h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#9c97aa', fontSize: '13px' }}>
                      <th style={{ padding: '12px' }}>Nội dung</th>
                      <th style={{ padding: '12px' }}>Loại</th>
                      <th style={{ padding: '12px' }}>Ngày tạo</th>
                      <th style={{ padding: '12px' }}>Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody>
                    {articles.slice(0, 4).map((art) => (
                      <tr key={`art-${art.id}`} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)', fontSize: '14px' }}>
                        <td style={{ padding: '14px 12px', fontWeight: 500 }}>{art.title}</td>
                        <td style={{ padding: '14px 12px', color: '#9c97aa' }}>Website Article</td>
                        <td style={{ padding: '14px 12px', fontSize: '12px', color: '#6a6575' }}>{new Date(art.created_at).toLocaleDateString('vi-VN')}</td>
                        <td style={{ padding: '14px 12px' }}>
                          <span className={`badge badge-${art.status}`}>{art.status === 'published' ? 'Đã đăng' : 'Bản nháp'}</span>
                        </td>
                      </tr>
                    ))}
                    {videoScripts.slice(0, 4).map((vid) => (
                      <tr key={`vid-${vid.id}`} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)', fontSize: '14px' }}>
                        <td style={{ padding: '14px 12px', fontWeight: 500 }}>{vid.title}</td>
                        <td style={{ padding: '14px 12px', color: '#9c97aa' }}>Short Video</td>
                        <td style={{ padding: '14px 12px', fontSize: '12px', color: '#6a6575' }}>{new Date(vid.created_at).toLocaleDateString('vi-VN')}</td>
                        <td style={{ padding: '14px 12px' }}>
                          <span className={`badge badge-${vid.status}`}>
                            {vid.status === 'rendered' ? 'Đã Render' : vid.status === 'rendering' ? 'Đang Render' : 'Bản nháp'}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {articles.length === 0 && videoScripts.length === 0 && (
                      <tr>
                        <td colSpan={4} style={{ textAlign: 'center', padding: '30px', color: '#6a6575' }}>Chưa có nội dung nào được tạo.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 2. TRENDS TAB */}
        {activeTab === 'trends' && (
          <div className="animate-fade-in">
            <div className="section-header">
              <div>
                <h1 style={{ fontSize: '28px' }}>Mẹ Bỉm Trend Hunter 🕵️‍♀️</h1>
                <p style={{ color: '#9c97aa', fontSize: '14px' }}>Hệ thống tự động cào và lọc các chủ đề y học & thói quen chăm con đang sốt dẻo.</p>
              </div>
              <button className="btn btn-primary" onClick={triggerFetchTrends}>
                ⚡️ Bấm quét mới
              </button>
            </div>

            <div className="glass-card">
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#9c97aa', fontSize: '13px' }}>
                      <th style={{ padding: '12px' }}>Chủ đề xu hướng</th>
                      <th style={{ padding: '12px' }}>Nguồn phát hiện</th>
                      <th style={{ padding: '12px' }}>Điểm Viral</th>
                      <th style={{ padding: '12px' }}>Mức độ nóng</th>
                      <th style={{ padding: '12px', textAlign: 'right' }}>Hành động</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trends.map((trend) => (
                      <tr key={trend.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)', fontSize: '14px' }}>
                        <td style={{ padding: '14px 12px', fontWeight: 600 }}>{trend.keyword}</td>
                        <td style={{ padding: '14px 12px' }}>
                          <span style={{ background: 'rgba(255,255,255,0.05)', padding: '4px 8px', borderRadius: '6px', fontSize: '12px', color: '#ba9b76' }}>
                            {trend.source}
                          </span>
                        </td>
                        <td style={{ padding: '14px 12px', color: trend.is_viral ? 'var(--color-primary)' : 'white', fontWeight: 700 }}>
                          🔥 {trend.popularity_score}%
                        </td>
                        <td style={{ padding: '14px 12px' }}>
                          <div style={{ width: '100px', height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: `${trend.popularity_score}%`, height: '100%', background: trend.is_viral ? 'var(--color-primary)' : 'var(--color-secondary)' }}></div>
                          </div>
                        </td>
                        <td style={{ padding: '14px 12px', textAlign: 'right' }}>
                          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                            <button 
                              className="btn btn-secondary" 
                              style={{ padding: '6px 12px', fontSize: '12px' }}
                              onClick={() => {
                                setTopicInput(trend.keyword);
                                setActiveTab('articles');
                              }}
                            >
                              ✍️ Viết bài viết
                            </button>
                            <button 
                              className="btn btn-primary" 
                              style={{ padding: '6px 12px', fontSize: '12px' }}
                              onClick={() => {
                                setVideoTopic(trend.keyword);
                                setActiveTab('videos');
                              }}
                            >
                              🎬 Tạo video ngắn
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {trends.length === 0 && (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', padding: '30px', color: '#6a6575' }}>
                          Chưa có xu hướng nào. Hãy ấn nút "Bấm quét mới" ở trên để thu thập dữ liệu.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 3. ARTICLES TAB */}
        {activeTab === 'articles' && (
          <div className="animate-fade-in">
            <div className="section-header">
              <div>
                <h1 style={{ fontSize: '28px' }}>AI Article Studio 📝</h1>
                <p style={{ color: '#9c97aa', fontSize: '14px' }}>Viết bài viết SEO tự động chuẩn y khoa cho Website Mẹ Bỉm Thông Thái.</p>
              </div>
            </div>

            <div className="grid-cols-2">
              {/* Creator Form */}
              <div className="glass-card" style={{ height: 'fit-content' }}>
                <h3 style={{ fontSize: '18px', marginBottom: '15px' }}>Tạo bài viết mới</h3>
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '13px', color: '#9c97aa' }}>
                    Nhập chủ đề nuôi con muốn phát triển nội dung:
                  </label>
                  <input
                    className="glass-input"
                    type="text"
                    placeholder="Ví dụ: Giấc ngủ EASY 4 cữ cho trẻ 3 tháng tuổi..."
                    value={topicInput}
                    onChange={(e) => setTopicInput(e.target.value)}
                    style={{ marginBottom: '15px' }}
                  />
                  <button className="btn btn-primary" style={{ width: '100%' }} onClick={handleGenerateArticle}>
                    ✨ Bắt đầu sinh bài viết AI
                  </button>
                </div>

                <h3 style={{ fontSize: '16px', marginBottom: '15px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '15px' }}>
                  Danh sách bài viết đã sinh
                </h3>
                <div style={{ maxHeight: '400px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {articles.map((art) => (
                    <div 
                      key={art.id} 
                      className="glass-card" 
                      style={{ 
                        padding: '12px', 
                        cursor: 'pointer', 
                        borderColor: editingArticle?.id === art.id ? 'var(--color-primary)' : 'rgba(255,255,255,0.05)',
                        background: editingArticle?.id === art.id ? 'rgba(255, 92, 122, 0.05)' : 'rgba(25,18,38,0.3)'
                      }}
                      onClick={() => {
                        setGeneratedArticle(art);
                        setEditingArticle(art);
                      }}
                    >
                      <h4 style={{ fontSize: '14px', color: 'white', marginBottom: '5px' }}>{art.title}</h4>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#6a6575' }}>{new Date(art.created_at).toLocaleDateString('vi-VN')}</span>
                        <span className={`badge badge-${art.status}`} style={{ fontSize: '10px', padding: '2px 8px' }}>
                          {art.status === 'published' ? 'Đã đăng' : 'Bản nháp'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Live Editor */}
              <div>
                {editingArticle ? (
                  <div className="glass-card animate-fade-in">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                      <h3 style={{ fontSize: '18px' }}>Hiệu chỉnh bài viết</h3>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: '12px' }} onClick={handleUpdateArticle}>
                          💾 Lưu nháp
                        </button>
                        <button 
                          className="btn btn-success" 
                          style={{ padding: '8px 16px', fontSize: '12px' }}
                          disabled={editingArticle.status === 'published'}
                          onClick={() => handlePublishArticle(editingArticle.id)}
                        >
                          🚀 Đăng Web
                        </button>
                        <button 
                          className="btn btn-danger" 
                          style={{ padding: '8px', borderRadius: '12px' }}
                          onClick={() => handleDeleteArticle(editingArticle.id)}
                        >
                          🗑️
                        </button>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                      <div>
                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', color: '#9c97aa' }}>Tiêu đề bài viết:</label>
                        <input
                          className="glass-input"
                          type="text"
                          value={editingArticle.title}
                          onChange={(e) => setEditingArticle({ ...editingArticle, title: e.target.value })}
                        />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                        <div>
                          <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', color: '#9c97aa' }}>Chuyên mục:</label>
                          <input
                            className="glass-input"
                            type="text"
                            value={editingArticle.category}
                            onChange={(e) => setEditingArticle({ ...editingArticle, category: e.target.value })}
                          />
                        </div>
                        <div>
                          <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', color: '#9c97aa' }}>Mục con:</label>
                          <input
                            className="glass-input"
                            type="text"
                            value={editingArticle.subcategory || ''}
                            onChange={(e) => setEditingArticle({ ...editingArticle, subcategory: e.target.value })}
                          />
                        </div>
                      </div>

                      <div>
                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', color: '#9c97aa' }}>Từ khóa (Tags):</label>
                        <input
                          className="glass-input"
                          type="text"
                          value={editingArticle.tags}
                          onChange={(e) => setEditingArticle({ ...editingArticle, tags: e.target.value })}
                        />
                      </div>

                      <div>
                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', color: '#9c97aa' }}>Tóm tắt ngắn (SEO):</label>
                        <textarea
                          className="glass-input"
                          rows={2}
                          value={editingArticle.summary || ''}
                          onChange={(e) => setEditingArticle({ ...editingArticle, summary: e.target.value })}
                          style={{ resize: 'vertical' }}
                        />
                      </div>

                      <div>
                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', color: '#9c97aa' }}>Nội dung bài viết (HTML / Text):</label>
                        <textarea
                          className="glass-input"
                          rows={12}
                          value={editingArticle.content}
                          onChange={(e) => setEditingArticle({ ...editingArticle, content: e.target.value })}
                          style={{ fontFamily: 'monospace', fontSize: '13px', resize: 'vertical' }}
                        />
                      </div>

                      {/* Mockup Google Search Snippet Card */}
                      <div className="glass-card" style={{ background: '#120c1f', padding: '16px', borderRadius: '12px', border: '1px dashed rgba(255,255,255,0.1)' }}>
                        <span style={{ fontSize: '11px', color: '#00b4d8' }}>Google Search Preview</span>
                        <h4 style={{ fontSize: '15px', color: '#8ab4f8', margin: '5px 0', fontWeight: 500 }}>
                          {editingArticle.meta_title || editingArticle.title}
                        </h4>
                        <span style={{ fontSize: '12px', color: '#30a14e' }}>http://www.mebimthongthai.io.vn/bai-viet/</span>
                        <p style={{ fontSize: '12px', color: '#bdc1c6', marginTop: '5px' }}>
                          {editingArticle.meta_description || editingArticle.summary || 'Chưa có mô tả bài viết.'}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="glass-card" style={{ textAlign: 'center', padding: '100px 20px', color: '#6a6575', borderStyle: 'dashed' }}>
                    <span>👈 Hãy chọn một bài viết trong danh sách hoặc gõ chủ đề để AI sinh mới.</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 4. SHORT VIDEOS TAB */}
        {activeTab === 'videos' && (
          <div className="animate-fade-in">
            <div className="section-header">
              <div>
                <h1 style={{ fontSize: '28px' }}>AI Video Shorts Studio 🎬</h1>
                <p style={{ color: '#9c97aa', fontSize: '14px' }}>Tự động sản xuất video ngắn TikTok/Reels có phụ đề chạy và giọng đọc tiếng Việt.</p>
              </div>
            </div>

            <div className="grid-cols-2">
              {/* Creator Form */}
              <div className="glass-card" style={{ height: 'fit-content' }}>
                <h3 style={{ fontSize: '18px', marginBottom: '15px' }}>Tạo video mới</h3>
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '13px', color: '#9c97aa' }}>
                    Nhập chủ đề/mẹo chăm bé muốn dựng thành video:
                  </label>
                  <input
                    className="glass-input"
                    type="text"
                    placeholder="Ví dụ: 3 cách hạ sốt nhanh an toàn tại nhà cho bé..."
                    value={videoTopic}
                    onChange={(e) => setVideoTopic(e.target.value)}
                    style={{ marginBottom: '15px' }}
                  />
                  <button className="btn btn-primary" style={{ width: '100%' }} onClick={handleGenerateScript}>
                    ✨ Tạo kịch bản video AI
                  </button>
                </div>

                <h3 style={{ fontSize: '16px', marginBottom: '15px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '15px' }}>
                  Danh sách video của bạn
                </h3>
                <div style={{ maxHeight: '400px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {videoScripts.map((vid) => (
                    <div 
                      key={vid.id} 
                      className="glass-card" 
                      style={{ 
                        padding: '12px', 
                        cursor: 'pointer', 
                        borderColor: generatedScript?.id === vid.id ? 'var(--color-primary)' : 'rgba(255,255,255,0.05)',
                        background: generatedScript?.id === vid.id ? 'rgba(255, 92, 122, 0.05)' : 'rgba(25,18,38,0.3)'
                      }}
                      onClick={() => setGeneratedScript(vid)}
                    >
                      <h4 style={{ fontSize: '14px', color: 'white', marginBottom: '5px' }}>{vid.title}</h4>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span className={`badge badge-${vid.status}`}>
                          {vid.status === 'rendered' ? 'Đã Render' : vid.status === 'rendering' ? 'Đang Render' : vid.status === 'failed' ? 'Lỗi Render' : 'Kịch bản'}
                        </span>
                        <div style={{ display: 'flex', gap: '5px', fontSize: '11px', color: '#6a6575' }}>
                          <span style={{ color: vid.tiktok_published ? 'var(--color-secondary)' : '#6a6575' }}>TikTok</span>
                          <span style={{ color: vid.facebook_published ? 'var(--color-secondary)' : '#6a6575' }}>Reels</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Script and Preview Studio */}
              <div>
                {generatedScript ? (
                  <div className="glass-card animate-fade-in">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                      <h3 style={{ fontSize: '18px' }}>Chi tiết Video: {generatedScript.title}</h3>
                      <button 
                        className="btn btn-danger" 
                        style={{ padding: '8px 12px' }}
                        onClick={() => handleDeleteScript(generatedScript.id)}
                      >
                        🗑️
                      </button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      {/* Compiling controls */}
                      <div className="glass-card" style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <span style={{ fontSize: '12px', color: '#9c97aa' }}>Trạng thái kết xuất:</span>
                            <div style={{ marginTop: '5px' }}>
                              <span className={`badge badge-${generatedScript.status}`} style={{ fontSize: '14px' }}>
                                {generatedScript.status === 'rendered' ? 'Sẵn sàng sử dụng' : generatedScript.status === 'rendering' ? 'Đang kết xuất video...' : generatedScript.status === 'failed' ? 'Gặp lỗi trong quá trình render' : 'Chưa render'}
                              </span>
                            </div>
                          </div>
                          
                          {generatedScript.status !== 'rendered' && generatedScript.status !== 'rendering' && (
                            <button className="btn btn-primary" onClick={() => handleCompileVideo(generatedScript.id)}>
                              🎥 Biên dịch & Render Video
                            </button>
                          )}
                          {generatedScript.status === 'rendering' && (
                            <div style={{ fontSize: '13px', color: '#e04d65', animation: 'pulse 1.5s infinite' }}>
                              Đang ghép nối tiếng nói và phụ đề...
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Video Player Preview and Social Buttons */}
                      {generatedScript.status === 'rendered' && (
                        <div className="grid-cols-2" style={{ gap: '20px' }}>
                          <div style={{ display: 'flex', justifyContent: 'center' }}>
                            {/* Vertical Preview Video Player */}
                            <video 
                              key={generatedScript.video_path}
                              controls 
                              style={{ width: '220px', height: '390px', borderRadius: '15px', border: '2px solid rgba(255,255,255,0.08)', boxShadow: '0 8px 30px rgba(0,0,0,0.5)', objectFit: 'cover' }}
                            >
                              <source src={`${API_BASE}${generatedScript.video_path}`} type="video/mp4" />
                              Browser not supporting video tag.
                            </video>
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '15px' }}>
                            <h4 style={{ fontSize: '16px' }}>Đăng tải tự động lên:</h4>
                            
                            <button 
                              className="btn btn-primary" 
                              style={{ background: '#000000', border: '1px solid rgba(255,255,255,0.1)' }}
                              onClick={() => handlePublishVideo(generatedScript.id, 'tiktok')}
                            >
                              🎵 Tải lên TikTok
                              {generatedScript.tiktok_published ? ' (Đã đăng)' : ''}
                            </button>
                            
                            <button 
                              className="btn btn-success" 
                              style={{ background: '#1877F2', boxShadow: 'none' }}
                              onClick={() => handlePublishVideo(generatedScript.id, 'facebook')}
                            >
                              🎬 Tải lên Facebook Reels
                              {generatedScript.facebook_published ? ' (Đã đăng)' : ''}
                            </button>
                            
                            <span style={{ fontSize: '11px', color: '#6a6575', textAlign: 'center' }}>
                              * Đăng tải ngầm qua Playwright sử dụng cookies trình duyệt được lưu ở phần cài đặt.
                            </span>
                          </div>
                        </div>
                      )}

                      {/* Script scene outlines */}
                      <div>
                        <h4 style={{ fontSize: '15px', marginBottom: '10px' }}>Phác thảo kịch bản lời thoại:</h4>
                        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '15px', borderRadius: '12px', fontSize: '14px', lineHeight: '1.8' }}>
                          <strong style={{ color: 'var(--color-primary)' }}>Hook mở đầu:</strong> "{generatedScript.hook}"
                          <p style={{ marginTop: '10px', color: '#c9c7cd' }}>
                            <strong style={{ color: 'white' }}>Lời thoại:</strong> {generatedScript.voiceover_text}
                          </p>
                          <div style={{ marginTop: '10px', fontSize: '12px', color: '#6a6575', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '10px' }}>
                            Giọng đọc: {generatedScript.voice_model} • Nhạc nền: {generatedScript.bg_music}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="glass-card" style={{ textAlign: 'center', padding: '100px 20px', color: '#6a6575', borderStyle: 'dashed' }}>
                    <span>👈 Hãy chọn một video kịch bản trong danh sách hoặc nhập chủ đề để tạo kịch bản mới.</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 5. COOKIES UPLOAD TAB */}
        {activeTab === 'cookies' && (
          <div className="animate-fade-in">
            <div className="section-header">
              <div>
                <h1 style={{ fontSize: '28px' }}>Cấu hình Session Cookies 🔑</h1>
                <p style={{ color: '#9c97aa', fontSize: '14px' }}>Cấu hình cookies để Playwright đăng nhập tự động và đăng Reels/TikTok thay mặt bạn.</p>
              </div>
            </div>

            <div className="glass-card" style={{ maxWidth: '600px', margin: '0 auto' }}>
              <h3 style={{ fontSize: '18px', marginBottom: '15px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '10px' }}>
                Tại sao cần cấu hình Cookies?
              </h3>
              <p style={{ fontSize: '14px', color: '#c9c7cd', marginBottom: '20px' }}>
                Hệ thống đăng bài tự động sử dụng trình duyệt ngầm giả lập thao tác của người dùng. Để tránh bị hỏi mật khẩu hay xác thực OTP mỗi lần đăng, bạn cần trích xuất Cookie đăng nhập từ trình duyệt của mình (dùng các extension Chrome như <strong>EditThisCookie</strong> hoặc <strong>Get Cookies.txt</strong> ở dạng JSON) và tải lên tại đây.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ border: '1px solid rgba(255,255,255,0.05)', padding: '15px', borderRadius: '12px', background: 'rgba(0,0,0,0.1)' }}>
                  <h4 style={{ fontSize: '15px', marginBottom: '10px', color: 'white' }}>1. Tải lên Cookies TikTok</h4>
                  <input 
                    type="file" 
                    accept=".json"
                    onChange={(e) => handleCookieUpload(e, 'tiktok')}
                    style={{ fontSize: '13px', color: '#9c97aa' }}
                  />
                  <div style={{ fontSize: '11px', color: '#6a6575', marginTop: '5px' }}>
                    Yêu cầu file định dạng JSON chứa cookies đăng nhập của TikTok.
                  </div>
                </div>

                <div style={{ border: '1px solid rgba(255,255,255,0.05)', padding: '15px', borderRadius: '12px', background: 'rgba(0,0,0,0.1)' }}>
                  <h4 style={{ fontSize: '15px', marginBottom: '10px', color: 'white' }}>2. Tải lên Cookies Facebook</h4>
                  <input 
                    type="file" 
                    accept=".json"
                    onChange={(e) => handleCookieUpload(e, 'facebook')}
                    style={{ fontSize: '13px', color: '#9c97aa' }}
                  />
                  <div style={{ fontSize: '11px', color: '#6a6575', marginTop: '5px' }}>
                    Sử dụng để Playwright truy cập facebook.com/reels/create và đăng Reels.
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

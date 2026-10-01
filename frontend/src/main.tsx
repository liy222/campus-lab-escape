import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [status, setStatus] = useState('正在检查服务连接…');
  useEffect(() => {
    fetch('/api/health')
      .then(async response => {
        if (!response.ok) throw new Error(String(response.status));
        const data = await response.json();
        setStatus(data.status === 'ok' ? '后端服务已连接' : '服务响应异常');
      })
      .catch(() => setStatus('无法连接后端服务，请检查启动窗口。'));
  }, []);
  return <main>
    <p className="eyebrow">校园实验室 · 本地开发原型</p>
    <h1>逃离校园实验室</h1>
    <p>探索三个房间，收集线索，与需要你确认行动的 AI 队友协作。</p>
    <section aria-labelledby="status-title">
      <h2 id="status-title">工程骨架</h2>
      <p role="status">{status}</p>
      <p>当前版本仅验证页面与服务连接。游戏交互正在实现。</p>
    </section>
  </main>;
}

createRoot(document.getElementById('root')!).render(<App />);

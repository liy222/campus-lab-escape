import { createRoot } from 'react-dom/client';
import App from './App';
import V5Workspace from './v5/Workspace';
import './style.css';
createRoot(document.getElementById('root')!).render((import.meta as ImportMeta & {env?:Record<string,string>}).env?.VITE_GAMEPLAY_VERSION === 'v5' ? <V5Workspace /> : <App />);

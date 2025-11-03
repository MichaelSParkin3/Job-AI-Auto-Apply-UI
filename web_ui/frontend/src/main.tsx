import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// TODO: Re-enable StrictMode after fixing WebSocket cleanup in ApplyProgress.tsx
createRoot(document.getElementById('root')!).render(
  <App />
)

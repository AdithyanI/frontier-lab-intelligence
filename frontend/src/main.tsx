import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './tokens.css'
import './app.css'
import App from './app/App'
import { AuditDateProvider } from './app/AuditDateProvider'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuditDateProvider>
        <App />
      </AuditDateProvider>
    </BrowserRouter>
  </StrictMode>,
)

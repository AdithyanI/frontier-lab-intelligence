import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './tokens.css'
import './app.css'
import App from './App'
import { AuditDateProvider } from './AuditDateContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuditDateProvider>
        <App />
      </AuditDateProvider>
    </BrowserRouter>
  </StrictMode>,
)

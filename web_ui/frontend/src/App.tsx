import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'

export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background">
        <Routes>
          <Route path="/" element={<div>Dashboard</div>} />
        </Routes>
      </div>
    </Router>
  )
}

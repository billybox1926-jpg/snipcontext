import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Snippets from './pages/Snippets'
import SnippetDetail from './pages/SnippetDetail'
import NewSnippet from './pages/NewSnippet'
import Tags from './pages/Tags'
import ExportPage from './pages/Export'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/snippets" element={<Snippets />} />
        <Route path="/snippets/new" element={<NewSnippet />} />
        <Route path="/snippets/:id" element={<SnippetDetail />} />
        <Route path="/tags" element={<Tags />} />
        <Route path="/export" element={<ExportPage />} />
      </Route>
    </Routes>
  )
}

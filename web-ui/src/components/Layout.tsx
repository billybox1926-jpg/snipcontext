import { Outlet, NavLink } from 'react-router-dom'

export default function Layout() {
  const link = ({ isActive }: { isActive: boolean }) =>
    `block rounded px-3 py-2 text-sm ${isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:text-white'}`

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 border-r border-gray-800 bg-gray-950/60 p-3">
        <div className="px-1 pb-3 text-sm font-semibold text-gray-200">SnipContext</div>
        <nav className="flex flex-col gap-1">
          <NavLink to="/" end className={link}>Dashboard</NavLink>
          <NavLink to="/snippets" className={link}>Snippets</NavLink>
          <NavLink to="/tags" className={link}>Tags</NavLink>
          <NavLink to="/export" className={link}>Export</NavLink>
        </nav>
      </aside>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}

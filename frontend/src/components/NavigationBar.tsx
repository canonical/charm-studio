interface Props {
  sidebarOpen: boolean
  onToggleSidebar: () => void
}

export default function NavigationBar({ sidebarOpen, onToggleSidebar }: Props) {
  return (
    <header className="p-navigation">
      <div className="p-navigation__row">
        <button
          className="p-navigation__toggle"
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
            <rect y="2" width="18" height="2" rx="1" />
            <rect y="8" width="18" height="2" rx="1" />
            <rect y="14" width="18" height="2" rx="1" />
          </svg>
        </button>
        <div className="p-navigation__banner">
          <span className="p-navigation__brand-name">charm.studio</span>
        </div>
      </div>
    </header>
  )
}

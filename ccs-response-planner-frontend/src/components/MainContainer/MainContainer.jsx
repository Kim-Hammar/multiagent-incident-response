import { Outlet } from 'react-router-dom'
import { APP_TITLE } from '../Common/constants'

function MainContainer() {
  return (
    <div>
      <nav className="navbar navbar-dark bg-dark mb-4">
        <span className="navbar-brand">{APP_TITLE}</span>
      </nav>
      <div className="container">
        <Outlet />
      </div>
    </div>
  )
}

export default MainContainer

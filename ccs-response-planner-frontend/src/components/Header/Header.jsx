import './Header.css'
import { NavLink } from 'react-router-dom'
import {
  LOGIN_RESOURCE,
  ABOUT_RESOURCE,
  RESPONSE_PLANNER_RESOURCE
} from '../Common/constants'

/**
 * The header component that is present on every page
 */
const Header = () => (
  <nav className="navbar navbar-expand navbar-dark bg-dark mb-4">
    <ul className="navbar-nav">
      <li className="nav-item">
        <NavLink className="nav-link" to={`/${RESPONSE_PLANNER_RESOURCE}`}>
          Response Planner
        </NavLink>
      </li>
      <li className="nav-item">
        <NavLink className="nav-link" to={`/${ABOUT_RESOURCE}`}>
          About
        </NavLink>
      </li>
      <li className="nav-item">
        <NavLink className="nav-link" to={`/${LOGIN_RESOURCE}`}>
          Login
        </NavLink>
      </li>
    </ul>
  </nav>
)

export default Header

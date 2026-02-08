import './Header.css'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  LOGIN_RESOURCE,
  ABOUT_RESOURCE,
  RESPONSE_PLANNER_RESOURCE,
  LLM_RESOURCE,
  TOOLS_RESOURCE,
  DIGITAL_TWIN_RESOURCE
} from '../Common/constants'

/**
 * The header component that is present on every page
 */
const Header = () => {
  const { isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate(`/${LOGIN_RESOURCE}`)
  }

  return (
    <nav className="navbar navbar-expand navbar-dark bg-dark mb-4">
      <ul className="navbar-nav">
        <li className="nav-item">
          <NavLink className="nav-link" to={`/${RESPONSE_PLANNER_RESOURCE}`}>
            Response planner
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink className="nav-link" to={`/${LLM_RESOURCE}`}>
            LLM
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink className="nav-link" to={`/${TOOLS_RESOURCE}`}>
            Tools
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink className="nav-link" to={`/${DIGITAL_TWIN_RESOURCE}`}>
            Digital twin
          </NavLink>
        </li>
        <li className="nav-item">
          <NavLink className="nav-link" to={`/${ABOUT_RESOURCE}`}>
            About
          </NavLink>
        </li>
        {isAuthenticated ? (
          <li className="nav-item">
            <button
              className="nav-link btn btn-link"
              onClick={handleLogout}
              style={{ cursor: 'pointer' }}
            >
              Logout
            </button>
          </li>
        ) : (
          <li className="nav-item">
            <NavLink className="nav-link" to={`/${LOGIN_RESOURCE}`}>
              Login
            </NavLink>
          </li>
        )}
      </ul>
    </nav>
  )
}

export default Header

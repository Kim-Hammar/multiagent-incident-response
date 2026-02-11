import './MainContainer.css'
import { Outlet } from 'react-router-dom'
import Header from '../Header/Header.jsx'
import Footer from '../Footer/Footer.jsx'

function MainContainer() {
  return (
    <div>
      <Header />
      <div className="container-fluid main-content">
        <Outlet />
      </div>
      <Footer />
    </div>
  )
}

export default MainContainer

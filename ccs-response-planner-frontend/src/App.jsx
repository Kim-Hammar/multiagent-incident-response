import './App.css'
import MainContainer from './components/MainContainer/MainContainer.jsx'
import NotFound from './components/MainContainer/NotFound/NotFound.jsx'
import Home from './components/MainContainer/Home/Home.jsx'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { HOME_RESOURCE, NOT_FOUND_RESOURCE } from './components/Common/constants'

function App() {
  return (
    <div className="App container-fluid">
      <div className="row">
        <div className="col-sm-12">
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<MainContainer />}>
                <Route index element={<Navigate to={HOME_RESOURCE} />} />
                <Route path={HOME_RESOURCE} element={<Home />} />
                <Route path={NOT_FOUND_RESOURCE} element={<NotFound />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </div>
      </div>
    </div>
  )
}

export default App

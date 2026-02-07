import './App.css'
import MainContainer from './components/MainContainer/MainContainer.jsx'
import NotFound from './components/NotFound/NotFound.jsx'
import Login from './components/Login/Login.jsx'
import About from './components/About/About.jsx'
import ResponsePlanner from './components/ResponsePlanner/ResponsePlanner.jsx'
import Llm from './components/LLM/LLM.jsx'
import ProtectedRoute from './components/Common/ProtectedRoute.jsx'
import { AuthProvider } from './contexts/AuthContext.jsx'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import {
  LOGIN_RESOURCE,
  ABOUT_RESOURCE,
  RESPONSE_PLANNER_RESOURCE,
  LLM_RESOURCE,
  NOT_FOUND_RESOURCE
} from './components/Common/constants'

function App() {
  return (
    <div className="App container-fluid">
      <div className="row">
        <div className="col-sm-12">
          <AuthProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<MainContainer />}>
                  <Route index element={<Navigate to={RESPONSE_PLANNER_RESOURCE} />} />
                  <Route
                    path={RESPONSE_PLANNER_RESOURCE}
                    element={
                      <ProtectedRoute>
                        <ResponsePlanner />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path={LLM_RESOURCE}
                    element={
                      <ProtectedRoute>
                        <Llm />
                      </ProtectedRoute>
                    }
                  />
                  <Route path={ABOUT_RESOURCE} element={<About />} />
                  <Route path={LOGIN_RESOURCE} element={<Login />} />
                  <Route path={NOT_FOUND_RESOURCE} element={<NotFound />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </AuthProvider>
        </div>
      </div>
    </div>
  )
}

export default App

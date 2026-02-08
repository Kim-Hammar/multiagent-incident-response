import './Tools.css'
import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext.jsx'
import TavilyCard from './TavilyCard.jsx'
import NvdCard from './NvdCard.jsx'
import MitreCard from './MitreCard.jsx'
import VirusTotalCard from './VirusTotalCard.jsx'
import AbuseIPDBCard from './AbuseIPDBCard.jsx'
import OtxCard from './OtxCard.jsx'
import DtExecCard from './DtExecCard.jsx'
import DtLogsCard from './DtLogsCard.jsx'
import DtPythonCard from './DtPythonCard.jsx'

/**
 * Tools page listing all connected external tools.
 */
function Tools() {
  const { token, logout } = useAuth()

  const [alert, setAlert] = useState(null)

  useEffect(() => {
    if (!alert) return
    const timer = setTimeout(() => setAlert(null), 3000)
    return () => clearTimeout(timer)
  }, [alert])

  return (
    <div className="Tools">
      <h2>Tools</h2>
      <hr />

      {alert && (
        <div className={`alert alert-${alert.type} alert-dismissible fade show`} role="alert">
          {alert.message}
          <button type="button" className="close" onClick={() => setAlert(null)}>
            <span>&times;</span>
          </button>
        </div>
      )}

      <TavilyCard token={token} logout={logout} setAlert={setAlert} />
      <NvdCard token={token} logout={logout} setAlert={setAlert} />
      <MitreCard token={token} logout={logout} setAlert={setAlert} />
      <VirusTotalCard token={token} logout={logout} setAlert={setAlert} />
      <AbuseIPDBCard token={token} logout={logout} setAlert={setAlert} />
      <OtxCard token={token} logout={logout} setAlert={setAlert} />
      <DtExecCard token={token} logout={logout} setAlert={setAlert} />
      <DtLogsCard token={token} logout={logout} setAlert={setAlert} />
      <DtPythonCard token={token} logout={logout} setAlert={setAlert} />
    </div>
  )
}

export default Tools

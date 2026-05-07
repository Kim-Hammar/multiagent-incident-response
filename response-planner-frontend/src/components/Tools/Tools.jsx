import './Tools.css'
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
  const noop = () => {}

  return (
    <div className="Tools">
      <h2>Tools</h2>
      <hr />

      <TavilyCard token={token} logout={logout} setAlert={noop} />
      <NvdCard token={token} logout={logout} setAlert={noop} />
      <MitreCard token={token} logout={logout} setAlert={noop} />
      <VirusTotalCard token={token} logout={logout} setAlert={noop} />
      <AbuseIPDBCard token={token} logout={logout} setAlert={noop} />
      <OtxCard token={token} logout={logout} setAlert={noop} />
      <DtExecCard token={token} logout={logout} setAlert={noop} />
      <DtLogsCard token={token} logout={logout} setAlert={noop} />
      <DtPythonCard token={token} logout={logout} setAlert={noop} />
    </div>
  )
}

export default Tools

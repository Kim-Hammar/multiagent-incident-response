import { APP_TITLE } from '../../Common/constants'

function Home() {
  return (
    <div className="card">
      <div className="card-body">
        <h1 className="card-title">{APP_TITLE}</h1>
        <p className="card-text">
          Welcome to the incident response planner. This tool helps you create
          and manage incident response plans for cyber-security events.
        </p>
      </div>
    </div>
  )
}

export default Home

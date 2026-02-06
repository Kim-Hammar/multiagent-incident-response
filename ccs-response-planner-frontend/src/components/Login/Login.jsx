import './Login.css'

/**
 * The login page component
 */
function Login() {
  return (
    <div className="Login">
      <div className="card login-card mx-auto">
        <div className="card-body">
          <h2 className="card-title mb-4">Login</h2>
          <form>
            <div className="form-group mb-3">
              <label htmlFor="username">Username</label>
              <input
                type="text"
                className="form-control"
                id="username"
                placeholder="Enter username"
              />
            </div>
            <div className="form-group mb-3">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                className="form-control"
                id="password"
                placeholder="Enter password"
              />
            </div>
            <button type="submit" className="btn btn-dark btn-block">
              Sign in
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default Login

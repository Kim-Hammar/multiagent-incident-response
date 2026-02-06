import './Footer.css'

/**
 * The footer component that is present on every page
 */
const Footer = () => (
  <div className="Footer">
    <footer className="footer">
      <div className="container">
        <p className="text-muted">
          Released under the Creative Commons Attribution-ShareAlike 4.0
          International License
          <a
            href="https://github.com/Kim-Hammar/ccs26_incident_response"
            className="githubLink"
          >
            <i className="fa fa-github" aria-hidden="true" />
          </a>
        </p>
        <p className="text-muted">
          Copyright 2026 &copy; Kim Hammar, Tansu Alpcan, Emil Lupu
        </p>
      </div>
    </footer>
  </div>
)

export default Footer

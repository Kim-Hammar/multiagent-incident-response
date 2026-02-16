import './About.css'
import MethodFigure from './method.png'

/**
 * The about page component
 */
function About() {
  return (
    <div className="About">
      <h2>About</h2>
      <hr />
      <p>
        This is an agentic multiagent incident response system that leverages large language models
        (LLMs) to assist security operators during incident handling.
      </p>
      <img src={MethodFigure} alt="Method overview" className="method-figure" />
    </div>
  )
}

export default About

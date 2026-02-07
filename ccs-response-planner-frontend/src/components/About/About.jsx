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
        <b>Incident response</b> refers to the coordinated actions taken to
        contain, mitigate, and recover from cyberattacks. Today, incident
        response is largely a manual process carried out by security
        operators. While this approach can be effective, it is often slow,
        labor-intensive, and requires specialized skills. For instance, a recent
        study reports that organizations take an average of 73 days to
        respond and recover from an incident. Reducing this delay requires
        improved decision-support tools to assist operators during
        incident handling. Currently, the standard approach to assisting
        operators relies on response playbooks, which comprise predefined
        rules for managing specific incidents. However, such playbooks still
        depend on security experts for configuration, which makes them difficult
        to keep aligned with evolving threats and system architectures.
      </p>
      <p>
        To overcome these limitations, an emerging direction of research is to
        leverage the security knowledge encoded in{' '}
        large language models (LLMs) as decision support in incident
        response. Notably, IBM recently launched an LLM-based incident response
        service and Google has developed an LLM-driven security operations
        platform. The role of the LLM within these systems is to analyze large
        volumes of system logs and suggest potential response actions.
      </p>
      <p>
        Most of the LLM-based methods proposed in the literature so far are
        based on prompt engineering of frontier LLMs, such as ChatGPT.
        While this approach has shown promise, it is costly and does not provide
        theoretical guarantees. A few recent works have tried to address these
        drawbacks by combining the LLM&apos;s predictions with{' '}
        planning techniques, such as lookahead optimization. However,
        current methods that follow this approach rely on repeated invocations of
        the LLM to generate candidate actions and evaluate their potential
        outcomes, which is inefficient and limits the depth of planning that can
        be performed in practice.
      </p>
      <p>
        In this paper, we advocate for an alternative approach, which is both{' '}
        computationally efficient and theoretically principled.
        Instead of using the LLM to generate response actions from system logs,
        we use it to generate a model of the response process as{' '}
        <b>Python code</b>. This model allows us to leverage standard planning
        algorithms (e.g., tree search) to efficiently compute an
        effective response plan through simulation. We then refine the code model
        through <b>in-context learning (ICL)</b> based on feedback from security
        operators. For example, an operator may identify infeasible actions in
        the model or other inconsistencies with the target system. After
        collecting such feedback, we incorporate it into the context of the LLM
        to revise the code model and update the response plan. See the figure
        below.
      </p>
      <img
        src={MethodFigure}
        alt="Method overview"
        className="method-figure"
      />
      <p>
        We prove that this feedback loop allows to control the expected
        operational cost when the response plan is deployed in the target system.
        To evaluate our method experimentally, we apply it to generate response
        plans for two multi-stage attacks executed in our testbed. The
        results show that our method is significantly more computationally
        efficient than current LLM-based methods and reduces operational costs by
        up to X% for the incidents we tested.
      </p>
      <p>
        Our <b>contributions</b> can be summarized as follows:
      </p>
      <ul>
        <li>
          We develop a novel method for incident response planning with
          an LLM. Our method uses the LLM to generate and refine a{' '}
          code model of the response process based on system logs. This
          model is then used to efficiently compute a response plan through
          standard planning algorithms.
        </li>
        <li>
          We bound the misspecification error of the code model generated
          by the LLM and derive a performance guarantee for the response
          plans computed through our method.
        </li>
        <li>
          We evaluate our method on two different multi-stage attacks in our
          testbed. The results show that our method reduces operational costs by
          up to X% and is several orders of magnitude more efficient than
          state-of-the-art methods.
        </li>
        <li>
          We release source code and a video demonstration of a
          decision-support system for incident response that implements our
          method; see the repository at X.
        </li>
      </ul>
    </div>
  )
}

export default About

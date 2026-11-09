# Agent Skills

xstructured publishes two [Agent Skills](https://agentskills.io). They give a
coding agent the instructions, references, scripts, templates and tests it
needs to use xstructured correctly. They work in Claude Code, Codex, Cursor,
GitHub Copilot and any other agent that reads the open Agent Skills format.

<div class="xs-agentic" markdown>

## Agentic installation

Install the skills so your coding agent knows how to:

- get prose and a validated Pydantic value from one model response;
- attach xstructured to a chat model, chain, graph, or agent;
- stream prose and a structured card to a UI;
- customize parsing, prompting, and metrics through the extension points.

=== "Ask your coding agent"

    Give your coding agent the repository and let it install the skills it
    needs.

    ```text title="Agent instruction"
    Install the Agent Skills from https://github.com/smuniharish/xstructured
    (xstructured-skills/skills/xstructured and
    xstructured-skills/skills/xstructured-extend) into this project, run the
    xstructured skill's scripts/verify_setup.py, then add structured output
    to this application with xstructured, following the skill's workflow and
    rules.
    ```

=== "skills CLI"

    The [skills CLI](https://github.com/vercel-labs/skills) finds both skills
    in the repository and installs them for the agents in your project. It
    needs Node.js 22.20 or later.

    ```bash
    npx skills add smuniharish/xstructured
    ```

    To install a single skill, add `--skill xstructured` or
    `--skill xstructured-extend`. Add `-g` to install it for every project.

=== "Manual installation"

    Copy the skill directories into your agent's skills directory, for
    example:

    ```bash
    git clone --depth 1 https://github.com/smuniharish/xstructured.git
    cp -r xstructured/xstructured-skills/skills/xstructured \
      .agents/skills/xstructured
    cp -r xstructured/xstructured-skills/skills/xstructured-extend \
      .agents/skills/xstructured-extend
    ```

    [Install in your agent](install.md) lists the directory each agent reads.

</div>

## The skills

<div class="grid cards" markdown>

-   :material-play-circle-outline:{ .lg .middle } __[xstructured](xstructured.md)__

    ---

    Adds xstructured to an application. Covers wrapping chat models, chains
    and LangGraph graphs, agent middleware, output parsers, streaming, named
    payloads, bounded repair, OpenTelemetry, and troubleshooting.

    Includes an offline setup check and a test template.

-   :material-puzzle-outline:{ .lg .middle } __[xstructured-extend](xstructured-extend.md)__

    ---

    Extends xstructured. Use it to write a `JsonDecoder`, a
    `RecoveryStrategy`, an `Observer`, or any other extension point.

    Includes templates with their tests and a contract checker.

</div>

Each skill tells the agent when to use the other one, so you can install both
and the agent picks the right one. If your application only uses the
defaults, `xstructured` alone is enough.

## Use them

Once installed, describe the task. The agent loads a skill when the task
matches it:

| You ask | Skill |
| --- | --- |
| "Make our support bot reply in prose and return a validated ticket." | `xstructured` |
| "Give our create_agent agent a typed final answer, but keep its tools." | `xstructured` |
| "Stream the answer token by token, then render the ticket card." | `xstructured` |
| "Why does xstructured raise RecoveryError on this reply?" | `xstructured` |
| "Our model writes Python dicts. Write a decoder that accepts them." | `xstructured-extend` |
| "Send xstructured call metrics to Prometheus." | `xstructured-extend` |

You can also invoke a skill by name: `/xstructured` or `/xstructured-extend`
in Claude Code, Cursor and GitHub Copilot, and `$xstructured` or
`$xstructured-extend` in Codex.

Both skills teach the agent the rules that keep an integration correct:

- call the async API from async code;
- let xstructured write the instructions, and keep one output contract;
- bound repair, and never loop on `ParseError` by hand;
- never weaken validation or a contract test to make a test pass.

## Next steps

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } __[Install in your agent](install.md)__

    ---

    Where each agent looks for skills, and how to verify and update an
    installation.

-   :material-check-decagram-outline:{ .lg .middle } __[Evaluation](evaluation.md)__

    ---

    How the skills are tested in CI and evaluated against real tasks.

</div>

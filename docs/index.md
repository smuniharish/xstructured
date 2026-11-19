---
hide:
  - navigation
  - toc
---

<div class="xs-hero" markdown>

# xstructured

<p class="xs-tagline">
Validated Pydantic data <strong>and</strong> natural-language text from one LLM response.
Wrap any LangChain v1 Runnable or chat model, add middleware to any agent, or end a
chain with an output parser; get typed results that survive Markdown fences, chatty
prose, and token-by-token streaming.
</p>

[Get started](getting-started/index.md){ .md-button .md-button--primary }
[Browse examples](examples/index.md){ .md-button }
[API reference](api/index.md){ .md-button }

</div>

## Why xstructured

<div class="grid cards" markdown>

-   :material-shield-check:{ .lg .middle } __Validated, never guessed__

    ---

    Every value passes strict JSON decoding and Pydantic v2 validation in JSON mode.
    Recovery only chooses *which* part of a response to parse; it never rewrites JSON.

-   :material-text-box-check-outline:{ .lg .middle } __Prose and data together__

    ---

    The model answers in its own words and places a JSON payload in an envelope.
    You get both: `result.content` for people and `result.structured` for code.

-   :material-lightning-bolt:{ .lg .middle } __Ordered streaming__

    ---

    Stream text deltas to your UI while the structured payload arrives, then receive the
    validated value the moment its envelope closes.

-   :material-puzzle-outline:{ .lg .middle } __Composes with LangChain__

    ---

    Async-first Runnables, `create_agent` middleware, and an LCEL output parser:
    `ainvoke`, `abatch`, `astream`, tracing, retries, and fallbacks behave natively.

-   :material-lock-outline:{ .lg .middle } __Bounded by design__

    ---

    Input, envelope, payload, and nesting limits; duplicate keys, `NaN`, and overflowing
    numbers are rejected before validation.

-   :material-wrench-check-outline:{ .lg .middle } __Optional, bounded repair__

    ---

    When recovery is not enough, an opt-in repair Runnable gets a fixed number of
    attempts, and its output is held to the same schema.

-   :material-tune-variant:{ .lg .middle } __Extensible and observable__

    ---

    Every behavior is an abstract base class you can replace, Pydantic options pass
    straight through, and OpenTelemetry spans cover every call.

</div>

## Thirty-second tour

=== "pip"

    ```bash
    pip install xstructured
    ```

=== "uv"

    ```bash
    uv add xstructured
    ```

```python
import asyncio

from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from xstructured import with_xstructured_output


class Contact(BaseModel):
    name: str
    email: str


async def main() -> None:
    model = init_chat_model("openai:gpt-5-mini")
    extractor = with_xstructured_output(model, Contact)
    result = await extractor.ainvoke(
        "Please add Priya Shah (priya.shah@example.com) to the review."
    )
    print(result.structured)  # name='Priya Shah' email='priya.shah@...'
    print(result.content)  # "I've noted Priya Shah's details."


asyncio.run(main())
```

![How a request flows through xstructured](assets/diagrams/architecture-overview.png){ .diagram width="596" }

## Downloads

<p>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520sum%2528count%2529%2520v%2520FROM%2520pypi.pypi_downloads_per_day%2520WHERE%2520project%253D%2527xstructured%2527%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=downloads&amp;color=blue&amp;cacheSeconds=3600" alt="Total downloads"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520sum%2528count%2529%2520v%2520FROM%2520pypi.pypi_downloads_per_day%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520date%2520%253E%253D%2520toStartOfWeek%2528today%2528%2529%252C%25201%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=this%20week&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads this week"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520sum%2528count%2529%2520v%2520FROM%2520pypi.pypi_downloads_per_day%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520date%2520%253E%253D%2520toStartOfMonth%2528today%2528%2529%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=this%20month&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads this month"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520sum%2528count%2529%2520v%2520FROM%2520pypi.pypi_downloads_per_day%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520date%2520%253E%253D%2520toStartOfYear%2528today%2528%2529%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=this%20year&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads this year"></a>
</p>
<p>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528toString%2528y%2529%252C%2520%2527%253A%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520toYear%2528date%2529%2520y%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day%2520WHERE%2520project%253D%2527xstructured%2527%2520GROUP%2520BY%2520y%2520ORDER%2520BY%2520y%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=by%20year&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by year"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527A%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527B%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20A&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: A"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527B%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527C%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20B&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: B"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527C%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527D%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20C&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: C"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527D%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527E%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20D&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: D"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527E%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527F%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20E&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: E"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527F%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527G%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20F&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: F"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527G%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527H%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20G&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: G"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527H%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527I%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20H&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: H"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527I%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527J%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20I&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: I"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527J%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527K%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20J&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: J"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527K%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527L%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20K&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: K"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527L%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527M%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20L&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: L"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527M%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527N%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20M&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: M"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527N%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527P%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20N-O&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: N-O"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527P%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527Q%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20P&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: P"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527Q%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527R%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20Q&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: Q"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527R%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527S%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20R&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: R"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527S%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527T%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20S&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: S"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527T%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527U%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20T&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: T"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527U%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527Z%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20U-Y&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: U-Y"></a>
  <a href="https://clickpy.clickhouse.com/dashboard/xstructured"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fsql-clickhouse.clickhouse.com%2F%3Fuser%3Ddemo%26query%3DSELECT%2520arrayStringConcat%2528groupArray%2528concat%2528country_code%252C%2520%2527%2520%2527%252C%2520toString%2528c%2529%2529%2529%252C%2520%2527%2520%257C%2520%2527%2529%2520v%2520FROM%2520%2528SELECT%2520country_code%252C%2520sum%2528count%2529%2520c%2520FROM%2520pypi.pypi_downloads_per_day_by_version_by_country%2520WHERE%2520project%253D%2527xstructured%2527%2520AND%2520match%2528country_code%252C%2520%2527%255E%255BA-Z%255D%257B2%257D%2524%2527%2529%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253E%253D%2520%2527Z%2527%2520AND%2520substring%2528country_code%252C%25201%252C%25201%2529%2520%253C%2520%2527%255B%2527%2520GROUP%2520BY%2520country_code%2520HAVING%2520c%2520%253E%25200%2520ORDER%2520BY%2520c%2520DESC%252C%2520country_code%2529%2520FORMAT%2520JSON&amp;query=%24.data%5B0%5D.v&amp;label=countries%20Z&amp;color=blue&amp;cacheSeconds=3600" alt="Downloads by country: Z"></a>
</p>

The badges use the public ClickHouse PyPI dataset, which refreshes daily, so
counts may be about a day behind. Shields caches badge images for up to an
hour, and GitHub may cache them longer. Country badges group non-zero counts by
two-letter country code. Shields may truncate unusually long country groups.
Weeks start on Monday (UTC). For complete data and
interactive charts, visit the
[ClickPy dashboard](https://clickpy.clickhouse.com/dashboard/xstructured).

## Where to go next

<div class="grid cards" markdown>

-   :material-rocket-launch-outline: __[Quickstart](getting-started/quickstart.md)__

    Wrap a chat model, a chain, or an agent in a few lines.

-   :material-book-open-variant: __[User guide](guide/index.md)__

    Envelopes, recovery, schemas, streaming, repair, extension points, and testing.

-   :material-connection: __[Integrations](integrations/index.md)__

    LangChain Runnables, agent middleware, Deep Agents, LangGraph, and OpenTelemetry.

-   :material-flask-outline: __[Examples](examples/index.md)__

    Twelve runnable applications, from agent extraction to OpenTelemetry tracing.

-   :material-speedometer: __[Benchmarks](benchmarks.md)__

    Correctness and latency against plain JSON and LangChain's parsers.

-   :material-api: __[API reference](api/index.md)__

    Every public class and function, with parameters and examples.

</div>

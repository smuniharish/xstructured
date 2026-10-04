# Getting started

`xstructured` adds a response contract to a LangChain Runnable: the model writes its
answer in natural language and places a JSON payload inside an *envelope*;
`xstructured` extracts the payload, validates it with Pydantic, and returns both.

<div class="grid cards" markdown>

-   :material-download: __[Installation](installation.md)__

    Requirements and optional dependencies.

-   :material-rocket-launch-outline: __[Quickstart](quickstart.md)__

    Chat models, chains, agents, streaming, and parsing text you already have.

</div>

## How it works

1. **Instructions.** The wrapper adds instructions that describe your schema and the
   envelope format to the model input.
2. **Generation.** Your Runnable runs unchanged and returns text or a message.
3. **Extraction.** The envelope is located, even when the closing tag appears inside a
   JSON string or arrives split across stream chunks.
4. **Validation.** The payload is decoded as strict JSON and validated by Pydantic. If it
   is wrapped in Markdown or prose, conservative recovery tries a few well-defined
   substrings first.
5. **Result.** You receive an `XStructuredResult` with the prose, the validated value, the
   original output, and metadata.

A response looks like this:

```text
I found one contact in your message.
<xstructured>{"name": "Priya Shah", "email": "priya.shah@example.com"}</xstructured>
```

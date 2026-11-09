# Output parser chain

`XStructuredOutputParser` is the last step of an LCEL chain:
`prompt | model | parser`. The prompt includes the parser's
`get_format_instructions()`, and the parser returns an `XStructuredResult`
with the validated invoice and the prose around it.

```python title="examples/output_parser_chain.py"
--8<-- "examples/output_parser_chain.py"
```

## Output

```text
=== Output parser in an LCEL chain (offline: scripted model) ===
Invoice: Invoice(vendor='Northwind Traders', total=1280.5, currency='EUR')
Summary: The invoice is from Northwind and is payable in euros.
```

Use the parser when you compose the chain yourself; use
`with_xstructured_output` when you want instructions injected, bounded repair,
and structured streaming. See
[LangChain](../integrations/langchain.md#output-parser).

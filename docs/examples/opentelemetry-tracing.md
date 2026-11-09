# OpenTelemetry tracing

`OpenTelemetryObserver` records each call as a span named
`xstructured <operation>`, a child of the current span. The script prints the
spans; set `OTEL_EXPORTER_OTLP_ENDPOINT` to also export them over OTLP.

```python title="examples/opentelemetry_tracing.py"
--8<-- "examples/opentelemetry_tracing.py"
```

## Output

```text
=== OpenTelemetry tracing (offline: scripted model) ===
Routing: Routing(queue='billing', urgent=False)
span 'xstructured invoke': status=OK envelopes=1 name=ticket-router
span 'route ticket': status=UNSET envelopes=- name=-
```

Run Jaeger locally to browse the spans:

```bash
podman run --rm -d --name jaeger -p 16686:16686 -p 4318:4318 \
  docker.io/jaegertracing/jaeger:latest
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
  uv run python examples/opentelemetry_tracing.py
```

Then open <http://localhost:16686> and search for the `xstructured-example`
service. See [OpenTelemetry](../integrations/opentelemetry.md).

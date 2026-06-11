"""Dev-time tooling to generate bundled ITSI object schemas from Splunk docs.

These modules are NOT imported at runtime. They parse a locally-scraped copy
of the ITSI 4.21 REST API schema page into the structured JSON consumed by
``mcp_itsi.knowledge.schema``.
"""

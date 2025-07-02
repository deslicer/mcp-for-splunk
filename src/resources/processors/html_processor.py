"""
HTML to LLM-optimized content processor for Splunk documentation.
"""

import re
from datetime import datetime
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    # Define a placeholder for type checking
    BeautifulSoup = Any


class SplunkDocsProcessor:
    """Process Splunk HTML documentation into LLM-optimized format."""

    def __init__(self):
        self.section_hierarchy = []

    def process_html(self, html: str, url: str) -> str:
        """Main processing pipeline."""
        if not HAS_BS4:
            # Fallback to basic text extraction if BeautifulSoup not available
            return self._basic_text_extraction(html, url)

        soup = BeautifulSoup(html, "html.parser")

        # Extract main content area
        content_area = self.extract_main_content(soup)

        # Process sections hierarchically
        sections = self.extract_sections(content_area)

        # Generate LLM-optimized markdown
        return self.generate_llm_markdown(sections, url)

    def _basic_text_extraction(self, html: str, url: str) -> str:
        """Basic text extraction fallback when BeautifulSoup is not available."""
        # Remove script and style elements
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Extract text content
        text = re.sub(r"<[^>]+>", "", html)

        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return f"""# Splunk Documentation

{text.strip()}

---
**Source**: {url}
**Processed**: {datetime.now().isoformat()}
**Format**: Basic text extraction (BeautifulSoup not available)
"""

    def extract_main_content(self, soup: "BeautifulSoup") -> "BeautifulSoup":
        """Extract the main documentation content, removing navigation/footer."""
        # Splunk docs typically have main content in specific containers
        main_content = (
            soup.find("div", class_="main-content")
            or soup.find("article")
            or soup.find("div", class_="content")
            or soup.find("main")
            or soup.find("div", class_="documentation-content")
            or soup.find("div", id="content")
        )
        return main_content or soup

    def extract_sections(self, content: "BeautifulSoup") -> list[dict[str, Any]]:
        """Extract hierarchical sections from documentation."""
        sections = []
        current_section: dict[str, Any] | None = None

        for element in content.find_all(
            ["h1", "h2", "h3", "h4", "p", "pre", "code", "ul", "ol", "table"]
        ):
            if element.name in ["h1", "h2", "h3", "h4"]:
                if current_section:
                    sections.append(current_section)

                current_section = {
                    "level": int(element.name[1]),
                    "title": element.get_text().strip(),
                    "content": [],
                }
            elif current_section is not None:
                current_section["content"].append(self.process_element(element))

        if current_section:
            sections.append(current_section)

        return sections

    def process_element(self, element) -> str:
        """Process individual HTML elements."""
        if element.name == "pre":
            # Code blocks
            return f"```\n{element.get_text()}\n```"
        elif element.name == "code":
            # Inline code
            return f"`{element.get_text()}`"
        elif element.name in ["ul", "ol"]:
            # Lists
            items = [f"- {li.get_text().strip()}" for li in element.find_all("li")]
            return "\n".join(items)
        elif element.name == "table":
            # Tables - convert to markdown
            return self.table_to_markdown(element)
        else:
            # Regular text
            text = element.get_text().strip()
            return text if text else ""

    def table_to_markdown(self, table) -> str:
        """Convert HTML table to markdown format."""
        rows = []

        # Process headers
        headers = table.find("thead")
        if headers:
            header_cells = [th.get_text().strip() for th in headers.find_all(["th", "td"])]
            if header_cells:
                rows.append("| " + " | ".join(header_cells) + " |")
                rows.append("| " + " | ".join(["---"] * len(header_cells)) + " |")

        # Process body rows
        tbody = table.find("tbody") or table
        for row in tbody.find_all("tr"):
            cells = [td.get_text().strip() for td in row.find_all(["td", "th"])]
            if cells:
                rows.append("| " + " | ".join(cells) + " |")

        return "\n".join(rows) if rows else "*(Table content could not be processed)*"

    def generate_llm_markdown(self, sections: list[dict[str, Any]], url: str) -> str:
        """Generate final LLM-optimized markdown."""
        output = []

        for section in sections:
            # Add section header
            header_prefix = "#" * section["level"]
            output.append(f"{header_prefix} {section['title']}")
            output.append("")

            # Add section content
            for content_item in section["content"]:
                if content_item and content_item.strip():
                    output.append(content_item)
                    output.append("")

        # Add metadata footer
        output.extend(
            [
                "---",
                f"**Source**: {url}",
                f"**Processed**: {datetime.now().isoformat()}",
                "**Format**: Optimized for LLM consumption",
            ]
        )

        return "\n".join(output)

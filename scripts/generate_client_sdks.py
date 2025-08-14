#!/usr/bin/env python3
"""
Client SDK Generation Script for MCP Server for Splunk

This script generates client SDKs in multiple programming languages using the OpenAPI specification.
It supports Python, JavaScript/TypeScript, Go, Java, and C# client libraries.
"""

import json
import subprocess
import sys
from pathlib import Path


class ClientSDKGenerator:
    """
    Generates client SDKs for the MCP Server for Splunk using OpenAPI Generator.
    """

    def __init__(self, openapi_spec_path: str, output_dir: str):
        self.openapi_spec_path = Path(openapi_spec_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Supported languages and their configurations
        self.language_configs = {
            "python": {
                "generator": "python",
                "package_name": "splunk_mcp_client",
                "project_name": "Python SDK",
                "additional_properties": {
                    "packageName": "splunk_mcp_client",
                    "projectName": "splunk-mcp-client",
                    "packageVersion": "1.0.0",
                },
            },
            "typescript": {
                "generator": "typescript-fetch",
                "package_name": "splunk-mcp-client",
                "project_name": "TypeScript SDK",
                "additional_properties": {
                    "npmName": "splunk-mcp-client",
                    "npmVersion": "1.0.0",
                    "supportsES6": "true",
                    "withInterfaces": "true",
                },
            },
        }

    def check_openapi_generator(self) -> bool:
        """Check if OpenAPI Generator is available."""
        try:
            result = subprocess.run(
                ["openapi-generator-cli", "version"], capture_output=True, text=True, check=True
            )
            print(f"✓ OpenAPI Generator found: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("✗ OpenAPI Generator CLI not found")
            print("Please install it using:")
            print("  npm install @openapitools/openapi-generator-cli -g")
            print("  or")
            print("  brew install openapi-generator")
            return False

    def validate_openapi_spec(self) -> bool:
        """Validate the OpenAPI specification."""
        try:
            with open(self.openapi_spec_path) as f:
                spec = json.load(f)

            # Basic validation
            required_fields = ["openapi", "info", "paths"]
            for field in required_fields:
                if field not in spec:
                    print(f"✗ OpenAPI spec missing required field: {field}")
                    return False

            print("✓ OpenAPI specification is valid")
            return True
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON in OpenAPI spec: {e}")
            return False
        except FileNotFoundError:
            print(f"✗ OpenAPI spec file not found: {self.openapi_spec_path}")
            return False

    def generate_sdk(self, language: str) -> bool:
        """Generate SDK for a specific language."""
        if language not in self.language_configs:
            print(f"✗ Unsupported language: {language}")
            return False

        config = self.language_configs[language]
        output_path = self.output_dir / f"client-{language}"

        print(f"\n🔧 Generating {config['project_name']} SDK...")

        # Prepare command
        cmd = [
            "openapi-generator-cli",
            "generate",
            "-i",
            str(self.openapi_spec_path),
            "-g",
            config["generator"],
            "-o",
            str(output_path),
        ]

        # Add additional properties as a single comma-separated parameter
        if config["additional_properties"]:
            properties = ",".join(
                [f"{key}={value}" for key, value in config["additional_properties"].items()]
            )
            cmd.extend(["--additional-properties", properties])

        try:
            # Create output directory
            output_path.mkdir(parents=True, exist_ok=True)

            # Run generation
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            print(f"✓ {config['project_name']} SDK generated successfully")
            print(f"  Output: {output_path}")

            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to generate {config['project_name']} SDK")
            print(f"  Error: {e.stderr}")
            return False

    def generate_all_sdks(self, languages: list[str] | None = None) -> dict[str, bool]:
        """Generate SDKs for all or specified languages."""
        if languages is None:
            languages = list(self.language_configs.keys())

        results = {}

        print("🚀 Starting Client SDK Generation")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"📄 OpenAPI spec: {self.openapi_spec_path}")

        # Validate prerequisites
        if not self.check_openapi_generator():
            return {"error": "OpenAPI Generator not available"}

        if not self.validate_openapi_spec():
            return {"error": "Invalid OpenAPI specification"}

        # Generate each SDK
        for language in languages:
            results[language] = self.generate_sdk(language)

        # Summary
        successful = [lang for lang, success in results.items() if success]
        failed = [lang for lang, success in results.items() if not success]

        print("\n📊 SDK Generation Summary:")
        print(f"✓ Successful: {len(successful)} ({', '.join(successful)})")
        if failed:
            print(f"✗ Failed: {len(failed)} ({', '.join(failed)})")

        return results


def main():
    """Main entry point for the SDK generator."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate client SDKs for MCP Server for Splunk")
    parser.add_argument(
        "--spec", default="docs/api/openapi.json", help="Path to OpenAPI specification file"
    )
    parser.add_argument("--output", default="sdk", help="Output directory for generated SDKs")
    parser.add_argument(
        "--languages",
        nargs="+",
        choices=["python", "typescript"],
        help="Languages to generate SDKs for (default: all)",
    )

    args = parser.parse_args()

    # Create generator
    generator = ClientSDKGenerator(args.spec, args.output)

    # Generate SDKs
    results = generator.generate_all_sdks(args.languages)

    # Exit with error code if any generation failed
    if "error" in results or any(not success for success in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()

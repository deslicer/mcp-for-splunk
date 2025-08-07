"""
Tool for retrieving Splunk configurations.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class GetConfigurations(BaseTool):
    """
    Get Splunk configurations.
    """

    METADATA = ToolMetadata(
        name="get_configurations",
        description=(
            "Retrieves Splunk configuration settings from specified .conf files. "
            "Access settings from any Splunk configuration file (props.conf, transforms.conf, "
            "inputs.conf, outputs.conf, etc.) either by entire file or specific stanza. "
            "Returns structured configuration data showing all settings and their values.\n\n"
            "Args:\n"
            "    conf_file (str): Configuration file name without .conf extension "
            "(e.g., 'props', 'transforms', 'inputs', 'outputs', 'server', 'web')\n"
            "    stanza (str, optional): Specific stanza name within the conf file to retrieve. "
            "If not provided, returns all stanzas in the file."
        ),
        category="admin",
        tags=["configuration", "settings", "administration"],
        requires_connection=True,
    )

    async def execute(
        self, ctx: Context, conf_file: str, stanza: str = ""
    ) -> dict[str, Any]:
        """
        Get Splunk configurations from specific configuration files.

        Args:
            conf_file (str): Configuration file name without .conf extension 
                           (e.g., 'props', 'transforms', 'inputs', 'outputs', 'server', 'web')
            stanza (str, optional): Specific stanza name within the conf file to retrieve.
                                  If not provided, returns all stanzas in the file.

        Returns:
            Dict containing configuration settings with status, file name, and configuration data
        """
        log_tool_execution("get_configurations", conf_file=conf_file, stanza=stanza)

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info(f"Retrieving configurations from {conf_file}")
        await ctx.info(f"Retrieving configurations from {conf_file}")

        try:
            confs = service.confs[conf_file]

            if stanza:
                stanza_obj = confs[stanza]
                result = {"stanza": stanza, "settings": dict(stanza_obj.content)}
                await ctx.info(f"Retrieved configuration for stanza: {stanza}")
                return self.format_success_response(result)

            all_stanzas = {}
            for stanza_obj in confs:
                all_stanzas[stanza_obj.name] = dict(stanza_obj.content)

            await ctx.info(f"Retrieved {len(all_stanzas)} stanzas from {conf_file}")
            return self.format_success_response({"file": conf_file, "stanzas": all_stanzas})
        except Exception as e:
            self.logger.error(f"Failed to get configurations: {str(e)}")
            await ctx.error(f"Failed to get configurations: {str(e)}")
            return self.format_error_response(str(e))



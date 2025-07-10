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
        self, ctx: Context, conf_file: str, stanza: str | None = None
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
            # Access configuration using REST API endpoint instead of direct confs access
            # This avoids URL encoding issues with certain configuration files
            endpoint = f"/services/configs/conf-{conf_file}"
            
            if stanza:
                # Get specific stanza
                stanza_endpoint = f"{endpoint}/{stanza}"
                try:
                    stanza_response = service.get(stanza_endpoint)
                    # Parse the XML response to extract configuration
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(stanza_response.body.read())
                    
                    settings = {}
                    for entry in root.findall('.//{http://dev.splunk.com/ns/rest}entry'):
                        content = entry.find('.//{http://dev.splunk.com/ns/rest}content')
                        if content is not None:
                            for key_elem in content.findall('.//{http://dev.splunk.com/ns/rest}s'):
                                key = key_elem.get('name')
                                value = key_elem.text
                                if key and value is not None:
                                    settings[key] = value
                    
                    result = {"stanza": stanza, "settings": settings}
                    await ctx.info(f"Retrieved configuration for stanza: {stanza}")
                    return self.format_success_response(result)
                except Exception as stanza_error:
                    self.logger.warning(f"Failed to get stanza via REST API: {stanza_error}")
                    # Fallback to direct access
                    confs = service.confs[conf_file]
                    stanza_obj = confs[stanza]
                    result = {"stanza": stanza, "settings": dict(stanza_obj.content)}
                    await ctx.info(f"Retrieved configuration for stanza: {stanza}")
                    return self.format_success_response(result)
            else:
                # Get all stanzas
                try:
                    response = service.get(endpoint)
                    # Parse the XML response to extract all stanzas
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response.body.read())
                    
                    all_stanzas = {}
                    for entry in root.findall('.//{http://dev.splunk.com/ns/rest}entry'):
                        stanza_name = entry.get('name')
                        if stanza_name:
                            content = entry.find('.//{http://dev.splunk.com/ns/rest}content')
                            stanza_settings = {}
                            if content is not None:
                                for key_elem in content.findall('.//{http://dev.splunk.com/ns/rest}s'):
                                    key = key_elem.get('name')
                                    value = key_elem.text
                                    if key and value is not None:
                                        stanza_settings[key] = value
                            all_stanzas[stanza_name] = stanza_settings
                    
                    await ctx.info(f"Retrieved {len(all_stanzas)} stanzas from {conf_file}")
                    return self.format_success_response({"file": conf_file, "stanzas": all_stanzas})
                except Exception as rest_error:
                    self.logger.warning(f"Failed to get configurations via REST API: {rest_error}")
                    # Fallback to direct access
                    confs = service.confs[conf_file]
                    all_stanzas = {}
                    for stanza_obj in confs:
                        all_stanzas[stanza_obj.name] = dict(stanza_obj.content)

                    await ctx.info(f"Retrieved {len(all_stanzas)} stanzas from {conf_file}")
                    return self.format_success_response({"file": conf_file, "stanzas": all_stanzas})
                    
        except Exception as e:
            self.logger.error(f"Failed to get configurations: {str(e)}")
            await ctx.error(f"Failed to get configurations: {str(e)}")
            return self.format_error_response(str(e))



"""
Tool for retrieving Splunk configurations.
"""

from typing import Any, Dict

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class GetConfigurations(BaseTool):
    """
    Get Splunk configurations.
    """
    
    METADATA = ToolMetadata(
        name="get_configurations",
        description="Get Splunk configurations from specified conf files",
        category="admin",
        tags=["configuration", "settings", "administration"],
        requires_connection=True
    )
    
    async def execute(
        self, 
        ctx: Context, 
        conf_file: str,
        stanza: str | None = None
    ) -> Dict[str, Any]:
        """
        Get Splunk configurations.
        
        Args:
            conf_file: Configuration file name (e.g., 'props', 'transforms', 'inputs')
            stanza: Optional stanza name to get specific configuration
            
        Returns:
            Dict containing configuration settings
        """
        log_tool_execution("get_configurations", conf_file=conf_file, stanza=stanza)
        
        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info(f"Retrieving configurations from {conf_file}")
        ctx.info(f"Retrieving configurations from {conf_file}")

        try:
            confs = service.confs[conf_file]

            if stanza:
                stanza_obj = confs[stanza]
                result = {
                    "stanza": stanza,
                    "settings": dict(stanza_obj.content)
                }
                ctx.info(f"Retrieved configuration for stanza: {stanza}")
                return self.format_success_response(result)

            all_stanzas = {}
            for stanza_obj in confs:
                all_stanzas[stanza_obj.name] = dict(stanza_obj.content)

            ctx.info(f"Retrieved {len(all_stanzas)} stanzas from {conf_file}")
            return self.format_success_response({
                "file": conf_file,
                "stanzas": all_stanzas
            })
        except Exception as e:
            self.logger.error(f"Failed to get configurations: {str(e)}")
            ctx.error(f"Failed to get configurations: {str(e)}")
            return self.format_error_response(str(e)) 
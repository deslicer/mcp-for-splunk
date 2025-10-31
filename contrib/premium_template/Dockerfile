# Example Dockerfile for premium layer
# Replace 'yourorg/mcp-splunk:oss' with your published OSS base image
FROM yourorg/mcp-splunk:oss

# Copy and install premium wheel
COPY dist/mcp_splunk_premium-0.1.0-py3-none-any.whl /tmp/premium.whl
RUN pip install /tmp/premium.whl && rm -f /tmp/premium.whl

# Configure runtime secrets via environment (use real secret manager in prod)
ENV PREMIUM_API_KEY=""

# Default command inherits from base image (mcp-server)


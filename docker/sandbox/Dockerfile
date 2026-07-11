# =============================================================================
# Sandbox Execution Environment — Minimal Python Image
# =============================================================================
# This container is used for executing untrusted Python code with strict isolation.

FROM python:3.12-slim

WORKDIR /sandbox

# Install minimal scientific computing packages
RUN pip install --no-cache-dir \
    numpy \
    pandas \
    matplotlib \
    requests \
    pydantic && \
    # Create non-root user
    groupadd -r sandbox && \
    useradd -r -g sandbox -d /sandbox -s /sbin/nologin sandbox

# Set restrictive permissions
RUN chmod 755 /sandbox

USER sandbox

# Default: just keep the container alive for exec commands
CMD ["sleep", "infinity"]

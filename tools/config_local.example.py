# Copy to tools/config_local.py (gitignored) and fill in; tools/config.py reads PRINTER from it.
# The same setting can come from the environment: FPVTANK_PRINTER.
PRINTER = 'http://<printer-ip>:7125'
# The robot's Pi over ssh, for twin/wifi_test.py. Or the environment: FPVTANK_PI_SSH.
PI_SSH = '<user>@<pi-ip>'

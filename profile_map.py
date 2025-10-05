#!/usr/bin/env python
"""Profile terminal_map startup performance"""

import logging
import sys

# Configure logging to show PROFILE messages
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stderr
)

# Now run the normal script
sys.argv = ['run.py', 'test.config', '-as', 'terminal_map', '-tb', '2']
exec(open('run.py').read())

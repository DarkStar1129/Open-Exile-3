#!/usr/bin/env fish
if test (count $argv) -lt 1
    echo "Usage: ./run_analysis.fish /path/to/EXILE3"
    exit 2
end

set DATA_DIR $argv[1]

python tools/analyze_install.py "$DATA_DIR" --json analysis/local-asset-report.json
or exit $status

python tools/render_outdoor_sector.py "$DATA_DIR" \
    --sector 0 \
    --output analysis/local-sector0.png
or exit $status

python tools/render_outdoor_sector.py "$DATA_DIR" \
    --sector 73 \
    --output analysis/local-sector73.png
or exit $status

python tools/render_world_overview.py "$DATA_DIR" \
    --surface-only \
    --output analysis/local-valorim-surface.png
or exit $status

python -m unittest discover -s tests -v

import sys
import json

# Parse seedsyncarr status JSON from stdin
# Usage:
#   echo '{"server":{"up":true},...}' | python3 parse_status.py server_up
#   echo '{"controller":{"latest_remote_scan_time":"..."},...}' | python3 parse_status.py remote_scan_done

if __name__ == '__main__':
    check_type = sys.argv[1] if len(sys.argv) > 1 else 'server_up'

    try:
        status = json.load(sys.stdin)
        if check_type == 'server_up':
            print(status['server']['up'])
        elif check_type == 'remote_scan_done':
            # Check if remote scan has completed at least once
            scan_time = status.get('controller', {}).get('latest_remote_scan_time')
            print(scan_time is not None)
        else:
            print('False')
    except (json.JSONDecodeError, KeyError, TypeError):
        print('False')

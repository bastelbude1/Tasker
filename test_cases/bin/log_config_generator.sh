#!/bin/bash
# Generate log and config file formats for testing

case "$1" in
    "syslog")
        echo "Oct 25 10:15:23 server01 sshd[1234]: Accepted password for user from 192.168.1.100"
        ;;
    "apache_log")
        echo "192.168.1.100 - - [25/Oct/2024:10:15:23 +0000] \"GET /index.html HTTP/1.1\" 200 1234"
        ;;
    "passwd_format")
        # /etc/passwd style format
        echo "root:x:0:0:root:/root:/bin/bash"
        ;;
    "config_format")
        # Key:value config format
        echo "hostname:server01:datacenter:east:status:active:cpu:8"
        ;;
    "timestamp_log")
        echo "[2024-10-25 10:15:23] INFO: Application started successfully"
        ;;
    "json_like")
        echo "{\"id\":1234,\"status\":\"active\",\"timestamp\":\"2024-10-25T10:15:23Z\"}"
        ;;
    *)
        echo "2024-10-25 10:15:23 INFO Test message"
        ;;
esac
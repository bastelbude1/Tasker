# TEST_METADATA: {"description": "Complex workflow with decision blocks and conditional execution - Smart download with port checking and fallback", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "expected_execution_path": [0, 1, 2, 3, 10], "expected_final_task": 10}

# smart_download.txt - Optimized port checking with early exit and conditional execution
# Global configuration
SERVER=localhost
TARGET_HOST=download.example.com
FILENAME=installer.zip
DOWNLOAD_PATH=/tmp/downloads
TIMEOUT=10

# Task 0: Check Port 443 (HTTPS - preferred)
task=0
hostname=@SERVER@
command=obb_portcheck_ubsmc_443
arguments=@TARGET_HOST@
timeout=@TIMEOUT@
exec=local

# Task 1: Check Port 80 (HTTP - fallback)
task=1
hostname=@SERVER@
command=obb_portcheck_ubsmc_80
arguments=@TARGET_HOST@
timeout=@TIMEOUT@
exec=local

# Task 2: Decision - Early Exit if Both Ports Failed
task=2
type=decision
# If at least one port is available, try downloads (continues to task 3)
# If both ports failed, jump to error handler
success=@0_exit@=0|@1_exit@=0
on_failure=99

# Task 3: HTTPS Download (Conditional - only if port 443 open)
task=3
hostname=@SERVER@
command=obb_curl_rOBBin_tarball_443
arguments=@DOWNLOAD_PATH@/@FILENAME@ https://@TARGET_HOST@/@FILENAME@
timeout=300
exec=local
# Skip if port 443 was closed
condition=@0_exit@=0
on_success=10

# Task 4: HTTP Download (Conditional - only if port 80 open)
task=4
hostname=@SERVER@
command=obb_curl_rOBBin_tarball_80
arguments=@DOWNLOAD_PATH@/@FILENAME@ http://@TARGET_HOST@/@FILENAME@
timeout=300
exec=local
# Skip if port 80 was closed
condition=@1_exit@=0
on_success=10
on_failure=98

# Task 10: Process Downloaded File
task=10
hostname=@SERVER@
command=echo
arguments=SUCCESS: Downloaded @FILENAME@ from @TARGET_HOST@ - check @DOWNLOAD_PATH@/@FILENAME@
exec=local
next=never

# Task 98: Curl Failed
task=98
hostname=@SERVER@
command=echo
arguments=ERROR: Curl download failed
exec=local
return=2

# Task 99: No Ports Available
task=99
hostname=@SERVER@
command=echo
arguments=ERROR: No accessible ports (80,443) on @TARGET_HOST@ - download impossible
exec=local
return=1

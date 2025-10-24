# TEST_METADATA: {"description": "README Example: stdout_split with multiple tasks", "test_type": "positive", "expected_exit_code": 0, "expected_success": true, "source_readme_lines": "456-483", "features_demonstrated": ["stdout_split", "newline_delimiter", "colon_delimiter", "space_delimiter", "variable_substitution"]}

task=0
hostname=localhost
command=printf
arguments=line1\nBETA_VALUE\nline3
# Extract second line using newline delimiter
stdout_split=newline,1
exec=local

task=1
hostname=localhost
command=echo
arguments=user:x:1000:1000:Admin:/home/user:/bin/bash
# Extract username from /etc/passwd style output
stdout_split=colon,0
exec=local

task=2
hostname=localhost
command=echo
arguments=key1=value1 key2=value2 key3=value3
# Get "key2=value2" using space delimiter
stdout_split=space,1
exec=local

task=3
condition=@2_stdout@~key2=value2
hostname=localhost
command=echo
# Uses "key2=value2" from split
arguments=Processing config: @2_stdout@
exec=local

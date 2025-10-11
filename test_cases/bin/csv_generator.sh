#!/bin/bash
# Generate CSV-like data for testing

case "$1" in
    "simple")
        echo "Name,Age,City,Country"
        echo "Alice,30,NYC,USA"
        echo "Bob,25,London,UK"
        echo "Charlie,35,Paris,France"
        ;;
    "extract_row")
        # Output single row for extraction testing
        echo "ProductID,ProductName,Price,Stock"
        echo "1001,Laptop,999.99,15"
        ;;
    "multiline")
        # Multiple rows for newline splitting
        echo "ID,Status,Message"
        echo "001,SUCCESS,Operation completed"
        echo "002,WARNING,Low memory"
        echo "003,ERROR,Connection failed"
        ;;
    *)
        echo "ID,Value"
        echo "1,test"
        ;;
esac
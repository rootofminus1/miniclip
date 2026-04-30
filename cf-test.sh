 curl -o /dev/null -s -D - -w "\ntime: %{time_total}s\n" --range 0-0 https://d3e9c5simbpq3a.cloudfront.net/someuuid.mp4 | grep -E "x-cache|time"

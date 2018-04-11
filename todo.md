# TODO

## Urgent

- DONE ~aggregate overall time for multiple responses~
- DONE ~generate minimal number of treatments (only one default, and 0-0 size)~

## Next

- DONE ~improve data gathering for external tool, gather starting set~
- DONE ~move charting to external tool~
- DONE ~local vs ec2 environment in data~
    + DONE ~environment variable and command line override~
    + DONE ~subfolders for data (data/local, data/ec2, etc)~
    + DONE ~csv files include as first field environment ... 'local' or 'ec2'~
    + DONE ~json dictionary with meta, so `data = {'environment': 'local', 'datetime': '...', 'treatments': [...]}`~
    + DONE ~plots use subfolders, also included in title~
- make at least three standard charts
    + DONE ~TCP vs QUIC on each treatment~
    + DONE ~TCP vs QUIC along each dimension (twinned bar charts)~
    + Heatmap over 2 dimensions

## Nice

- DONE ~cleanup log~
- DONE ~add time prediction~
- DONE ~sql(lite) db of results~
- DONE ~add side traffic treatment dimension (as different environment)~
- DONE ~jitter treatment dimension~
- DONE ~add permanent log file at DEBUG level~

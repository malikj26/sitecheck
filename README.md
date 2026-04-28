# Sitecheck
Tool dedicated to analyzing a bulk set of websites for general analysis by accepting a .csv input with websites.

# Input Format
Your CSV file should contain a column of websites.
### Default format:
```csv
url
google.com
youtube.com
github.com
```

# Running with Docker
```
- Step 1: Build Docker Image: 
docker build -t sitecheck .

- Step 2: Spin up container and provide input file:
docker run --rm -it -v "$PWD:/data" sitecheck --input /data/examples/sites.csv
("${PWD}:/data" on Windows)

You can change the column name by using --column
docker run --rm -it -v "$PWD:/data" sitecheck --input /data/examples/sites.csv --column website
```

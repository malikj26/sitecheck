# Sitecheck
Tool meant to analyze a bulk set of websites for general analysis by accepting a .csv input with websites.

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
- Build Docker Image: 
docker build -t sitecheck .

- Step 2:
docker run --rm -v "$PWD:/data" sitecheck --input /data/examples/sites.csv --output /data/results.csv
```
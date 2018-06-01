# Unifi-Metrics-Collector

Export Unifi controller stats to Influx DB.
The Unifi Metrics Collector runs within a Python3 docker container.

Steps to run:
1. Clone repo
2. Update config.ini file with proper details
3. Build docker container
   `docker build --no-cache -t unifi-collector . `
4. Create container
   `docker create  --name=unifi_metrics_collector --restart=always unifi-collector`
5. Start container
   `docker start unifi_metrics_collector`


Troubleshooting:
View docker logs:
`docker logs -f unifi_metrics_collector`

# Unifi-Metrics-Collector

Export Unifi controller stats to Influx DB.
The Unifi Metrics Collector runs within a Python3 docker container.

Steps to run:
1. Clone repo
2. Update config.ini file with proper details
    a) Unifi controller v4/v5 must be using port 8443
    b) Sleep is the time between querying the controller
    c) Influx database must be created before running the controller.
3. All devices must have an Alias assigned in the Unifi controller to function.
4. Build docker container
   `docker build --no-cache -t unifi-collector . `
5. Create container
   `docker create  --name=unifi_metrics_collector --restart=always unifi-collector`
6. Start container
   `docker start unifi_metrics_collector`

Troubleshooting:
View docker logs:
`docker logs -f unifi_metrics_collector`

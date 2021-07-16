#!/bin/sh -x

# API-KEY Grafana, need change
KEY="eyJrIjoiWWJjWTMwb0l5U1NYTUhNMkF3NkNZZEJFVngwWlVrMzciLCJuIjoiMSIsImlkIjoxfQ=="
# Grafana Dashboard UID, need change
UID="$1"
DIR="./config/grafana/provisioning/dashboards/json/"

tmpFile=$(mktemp)
curl -H "Authorization: Bearer $KEY" \
        "http://localhost:3000/api/dashboards/uid/$UID"\
     -o "$tmpFile"
jq .dashboard "$tmpFile" > "$DIR/$UID.json"

git add "$DIR/$UID.json"
git commit -m "Update $UID"
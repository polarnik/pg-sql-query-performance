#!/bin/sh 

# API-KEY Grafana, need change
KEY="eyJrIjoiRGl4bjN0NzAzbEFwd0Z5RVhZN0ZtSnE5RjViSHZrZ24iLCJuIjoiYWRtaW5rZXkiLCJpZCI6MX0="
# Grafana Dashboard UID, need change
UID="pgstat"
DIR="./config/grafana/provisioning/dashboards/json/"

tmpFile=$(mktemp)
curl -H "Authorization: Bearer $KEY" \
        "http://localhost:3000/api/dashboards/uid/$UID"\
     -o "$tmpFile"
jq .dashboard "$tmpFile" > "$DIR/$UID.json"

#TITLE=`jq -r '.title' "$DIR/$UID.json"`
#jq --arg a "${TITLE} (GIT)" '.title = $a' "$DIR/$UID.json" > "$tmpFile"
#mv "$tmpFile" "$DIR/$UID.json"
#jq --arg a "${UID}_GIT" '.uid = $a' "$DIR/$UID.json" > "$tmpFile"
mv "$tmpFile" "$DIR/$UID.json"

git add "$DIR/$UID.json"
git commit -m "Update $UID"
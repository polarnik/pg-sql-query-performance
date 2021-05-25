#!/bin/bash

# setup.sh starts k8s cluster

# you need to have kubectl, docker and minikube installed

# variables
INFLUX_USER=influx
INFLUX_PASS=pass
GRAFANA_USER=grafana
GRAFANA_PASS=pass

# removing existing cluster
# minikube delete

# setting up minikube and starting cluster using Docker
# minikube start --driver=docker

minikube addons enable dashboard
minikube addons enable metallb
minikube addons enable metrics-server       # collects information about used resources. some dashboard features require it

kubectl apply -f ./srcs/metallb/metallb.yaml

# creating secrets and configmaps
kubectl create secret generic influx-secret --from-literal=user=$INFLUX_USER --from-literal=password="$INFLUX_PASS"
kubectl create secret generic grafana-secret --from-literal=user=$GRAFANA_USER --from-literal=password="$GRAFANA_PASS"

kubectl apply -f ./srcs/influxdb/influxdb.yaml

kubectl apply -f ./srcs/grafana/grafana.yaml

# Start Dashboard
minikube dashboard
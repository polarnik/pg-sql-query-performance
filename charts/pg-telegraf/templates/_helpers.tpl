{{- define "helm.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "helm.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "helm.labels" -}}
helm.sh/chart: {{ include "helm.chart" . }}
{{ include "helm.selectorLabels" . }}
{{- end }}

{{- define "helm.selectorLabels" -}}
app.kubernetes.io/name: {{ include "helm.fullname" . }}
app: {{ .Values.applicationName }}
project: {{ .Values.projectName }}
{{- end }}

{{/* Secret name of one instance: existingSecret or the chart-managed one */}}
{{- define "pgtelegraf.secretName" -}}
{{- if .instance.existingSecret -}}
{{- .instance.existingSecret -}}
{{- else -}}
{{- printf "%s-%s" (include "helm.fullname" .root) .instance.name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end }}

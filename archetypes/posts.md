---
title: "{{ .Name | humanize | title }}"
date: {{ .Date }}
bookComments: True
bookSearchExclude: false
rss_guid: "tag:bamboobone9.com,2026:{{ .Name }}-{{ now.UnixNano }}"
---

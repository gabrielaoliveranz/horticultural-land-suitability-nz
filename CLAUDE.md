## Stale-number audits

Whenever a fix changes a reported number (counts, percentages, thresholds,
layer IDs), before marking the task done: grep the whole repo for the old
value and list every file that references it — even files not named in the
original request. Include this in the same summary, don't wait to be asked.

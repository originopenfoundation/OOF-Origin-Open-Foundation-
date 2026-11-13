# LaRA server analytics

POST /_lara/admin/engine-analytics runs in the LaRA Node.js process. The existing host-only admin authentication uses LARA_ADMIN_TOKEN. The analysis runs without external dependencies or additional service settings.

Example request body: {"capability":"descriptive","values":[1,3]}. The response has status 200 and analysis.result.mean equal to 2.

- descriptive accepts a numeric sample and reports the mean, median, median absolute deviation and sample standard deviation. The singleton standard deviation is null.
- pearson accepts values and paired_values with equal lengths and variation in both samples. The result measures linear association.
- bootstrap_mean accepts values, an unsigned 32-bit seed and 100–2000 replicates. The percentile interval assumes independent, identically distributed observations. The JS generator is deterministic within this adapter.

Samples are bounded to 4096 observations and bootstrap to 200000 draws. The public chat does not invoke the admin route.

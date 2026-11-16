'use strict';

const {runEngineAnalysis} = require('./engine-analytics');

const samples = [
  {capability: 'descriptive', values: [1, 2, 3, 4, 5]},
  {capability: 'pearson', values: [1, 2, 3, 4], paired_values: [2, 4, 6, 8]},
  {capability: 'bootstrap_mean', values: [2, 4, 6, 8], seed: 42, replicates: 200},
];

async function engineDemo(enabled) {
  if (enabled !== 'true') {
    return {status: 404, body: {error: 'Public engine testing is disabled.'}};
  }
  const cases = await Promise.all(samples.map(async input => {
    const result = await runEngineAnalysis(input);
    return {input, ...result};
  }));
  return {status: cases.every(result => result.status === 200) ? 200 : 500, body: {cases}};
}

module.exports = {engineDemo};

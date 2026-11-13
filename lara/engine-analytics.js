'use strict';

const VERSION = '1.0.0';
const MAX_VALUES = 4096;
const capabilities = new Map([
  ['descriptive', ['observation', []]],
  ['pearson', ['association', ['paired_values']]],
  ['bootstrap_mean', ['simulation', ['seed', 'replicates']]],
]);

function mean(values) {
  const offset = values[0];
  return offset + values.reduce((sum, value) => sum + (value - offset), 0) / values.length;
}
const sorted = values => [...values].sort((a, b) => a - b);

function median(values) {
  const ordered = sorted(values);
  const mid = Math.floor(ordered.length / 2);
  return ordered.length % 2 ? ordered[mid] : (ordered[mid - 1] + ordered[mid]) / 2;
}

function series(values, minimum) {
  if (!Array.isArray(values) || values.length < minimum || values.length > MAX_VALUES) {
    throw new RangeError('Invalid sample size');
  }
  for (const value of values) {
    if (!Number.isFinite(value) || Math.abs(value) > 1e100) {
      throw new RangeError('Expected finite numeric values with magnitudes up to 1e100');
    }
  }
  return values;
}

function describe(values) {
  const average = mean(values);
  const middle = median(values);
  const deviations = values.map(value => value - average);
  const scale = Math.max(...deviations.map(Math.abs));
  const variance = scale ? deviations.reduce((sum, value) => sum + (value / scale) ** 2, 0) : 0;
  return {
    mean: average,
    median: middle,
    median_absolute_deviation: median(values.map(value => Math.abs(value - middle))),
    sample_standard_deviation: values.length > 1 ? scale * Math.sqrt(variance / (values.length - 1)) : null,
  };
}

function unitCentered(values) {
  const average = mean(values);
  const deviations = values.map(value => value - average);
  const scale = Math.max(...deviations.map(Math.abs));
  if (!scale || values.every(value => value === values[0])) {
    throw new RangeError('Pearson correlation requires variation in both samples');
  }
  const scaled = deviations.map(value => value / scale);
  const norm = Math.hypot(...scaled);
  return scaled.map(value => value / norm);
}

function pearson(values, paired) {
  if (values.length !== paired.length) throw new RangeError('Paired samples must have equal lengths');
  const left = unitCentered(values);
  const right = unitCentered(paired);
  const correlation = left.reduce((sum, value, index) => sum + value * right[index], 0);
  return { r: Math.max(-1, Math.min(1, correlation)) };
}

function bootstrap(values, seed, replicates) {
  if (!Number.isInteger(seed) || seed < 0 || seed >= 2 ** 32) {
    throw new RangeError('Expected an unsigned 32-bit seed');
  }
  if (!Number.isInteger(replicates) || replicates < 100 || replicates > 2000 ||
      replicates * values.length > 200000) {
    throw new RangeError('Expected 100 to 2000 replicates and at most 200000 draws');
  }
  let state = seed;
  const means = [];
  for (let i = 0; i < replicates; i++) {
    let sum = 0;
    for (let j = 0; j < values.length; j++) {
      state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
      sum += values[Math.floor((state / 2 ** 32) * values.length)];
    }
    means.push(sum / values.length);
  }
  means.sort((a, b) => a - b);
  return {
    seed, replicates,
    interval_95_percentile: [0.025, 0.975].map(p => means[Math.floor((means.length - 1) * p)]),
  };
}

function runEngineAnalysis(analysis) {
  try {
    const capability = analysis?.capability;
    const definition = capabilities.get(capability);
    if (!definition) throw new RangeError('Unsupported analytical capability');
    const [evidence_kind, extraFields] = definition;
    const allowed = ['capability', 'values', ...extraFields];
    if (Object.keys(analysis).some(field => !allowed.includes(field))) {
      throw new RangeError('Unexpected analytical request fields');
    }
    const values = series(analysis.values, capability === 'descriptive' ? 1 : 2);
    let result;
    switch (capability) {
      case 'descriptive':
        result = describe(values);
        break;
      case 'pearson':
        result = pearson(values, series(analysis.paired_values, 2));
        break;
      case 'bootstrap_mean':
        result = bootstrap(values, analysis.seed, analysis.replicates);
        break;
    }
    return {
      status: 200,
      body: { api_version: 'v1', analysis: {
        version: VERSION, capability, evidence_kind, sample_size: values.length, result,
      } },
    };
  } catch (error) {
    if (!(error instanceof RangeError)) throw error;
    return { status: 422, body: { error: error.message } };
  }
}

module.exports = { runEngineAnalysis };

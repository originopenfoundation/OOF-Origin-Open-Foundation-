'use strict';

// Internal review loop. Steps are trusted, synchronous application callbacks.
function reviewLoop({objective, iterations, budgetMs, observe, verify, repair}) {
  if (typeof objective !== 'string' || !objective.trim() || objective.length > 240 ||
      !Number.isInteger(iterations) || iterations < 1 || iterations > 5 ||
      !Number.isInteger(budgetMs) || budgetMs < 1 || budgetMs > 10000 ||
      [observe, verify, repair].some(step => typeof step !== 'function')) {
    throw new TypeError('Invalid review loop configuration');
  }
  const trace = [];
  const deadline = performance.now() + budgetMs;
  const finish = status => ({objective, status, trace});
  for (let attempt = 1; attempt <= iterations; attempt++) {
    if (performance.now() >= deadline) return finish('budget_exhausted');
    let stage = 'observe';
    try {
      const evidence = observe(attempt);
      if (performance.now() >= deadline) return finish('budget_exhausted');
      stage = 'verify';
      const passed = verify(evidence);
      if (typeof passed !== 'boolean') throw new TypeError('Verifier must return a boolean');
      trace.push({attempt, stage, passed});
      if (performance.now() >= deadline) return finish('budget_exhausted');
      if (passed) return finish('verified');
      if (attempt < iterations) {
        stage = 'repair';
        const repaired = repair(evidence);
        if (repaired !== undefined) throw new TypeError('Repair must return undefined');
        trace.push({attempt, stage});
      }
    } catch {
      trace.push({attempt, stage, failed: true});
      return finish('step_failed');
    }
  }
  return finish('iteration_limit');
}

module.exports = {reviewLoop};

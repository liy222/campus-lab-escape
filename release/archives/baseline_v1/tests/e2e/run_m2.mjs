// T13 full-manual baseline wrapper; inherits the independent isolated runner.
process.env.QA_SUITE = 'm2';
await import('./run_r1.mjs');

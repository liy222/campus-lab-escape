// Pure judgement helpers. Self-tests exercise these with invented values only.
export function completedCircuitPass(modules) {
  return modules.length === 9 && modules.every(module => module.completed === true && module.disabled === true && !['wait', 'progress'].includes(module.cursor));
}
export function minimumControlSizePass(controls, minimum = 44) {
  return controls.length > 0 && controls.every(control => control.width >= minimum && control.height >= minimum);
}
export function pendingCircuitPass(observation) {
  return observation.aria_busy === 'true' && observation.modules.length === 9 && observation.modules.every(module => module.disabled && module.cursor === 'wait');
}
export function runJudgementSelfTest() {
  const completed = Array.from({ length: 9 }, () => ({ completed: true, disabled: true, cursor: 'default' }));
  const cases = [
    { name: 'completed module with wait fails', expected: false, actual: completedCircuitPass(completed.map((module, index) => ({ ...module, cursor: index === 0 ? 'wait' : 'default' }))) },
    { name: 'control below 44px fails', expected: false, actual: minimumControlSizePass([{ width: 44, height: 43.99 }]) },
    { name: 'normal completed modules pass', expected: true, actual: completedCircuitPass(completed) },
    { name: '44px controls pass', expected: true, actual: minimumControlSizePass([{ width: 44, height: 44 }]) },
    { name: 'pending requires actual busy state', expected: false, actual: pendingCircuitPass({ aria_busy: 'false', modules: completed }) },
  ];
  return { kind: 'isolated judgement self-test, invented values only', real_ui_executed: false, cases: cases.map(item => ({ ...item, pass: item.actual === item.expected })), pass: cases.every(item => item.actual === item.expected) };
}

export function evaluateBooleanQuery(text: string, query: string): boolean {
  if (!query.trim()) return true;

  // Simple parser: handles "exact phrase", AND, OR, NOT
  const content = text.toLowerCase();
  let q = query.trim();

  // Extract quoted phrases
  const phrases: string[] = [];
  q = q.replace(/"([^"]+)"/g, (_, phrase) => {
    phrases.push(phrase.toLowerCase());
    return `__PHRASE_${phrases.length - 1}__`;
  });

  const tokens = q.split(/\s+/);
  
  // Convert tokens to a boolean evaluation stack or just simple eval.
  // We'll implement a basic evaluator that goes left to right with basic precedence: NOT, AND, OR
  // For a robust implementation in JS without eval(), we can parse it into a tree.
  // But for mock verification, let's do a simplified tree parser.


  // Shunting yard simplified
  const output: string[] = [];
  const ops: string[] = [];
  const precedence: Record<string, number> = { 'OR': 1, 'AND': 2, 'NOT': 3 };

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    if (token === 'AND' || token === 'OR' || token === 'NOT') {
      while (ops.length > 0 && precedence[ops[ops.length - 1]] >= precedence[token]) {
        output.push(ops.pop()!);
      }
      ops.push(token);
    } else {
      // It's a value
      output.push(token);
      // Implicit AND if next token is also a value
      if (i + 1 < tokens.length && !['AND', 'OR', 'NOT'].includes(tokens[i + 1])) {
        while (ops.length > 0 && precedence[ops[ops.length - 1]] >= precedence['AND']) {
          output.push(ops.pop()!);
        }
        ops.push('AND');
      }
    }
  }
  while (ops.length > 0) {
    output.push(ops.pop()!);
  }

  const stack: boolean[] = [];
  for (const token of output) {
    if (token === 'AND') {
      const b = stack.pop() ?? true;
      const a = stack.pop() ?? true;
      stack.push(a && b);
    } else if (token === 'OR') {
      const b = stack.pop() ?? false;
      const a = stack.pop() ?? false;
      stack.push(a || b);
    } else if (token === 'NOT') {
      const a = stack.pop() ?? true;
      stack.push(!a);
    } else {
      let val = token.toLowerCase();
      if (val.startsWith('__phrase_')) {
        const idx = parseInt(val.replace('__phrase_', '').replace('__', ''));
        val = phrases[idx];
      }
      stack.push(content.includes(val));
    }
  }

  return stack.pop() ?? false;
}

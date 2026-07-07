function bracketMatch(str) {
  const stack = [];
  const mapping = { ')': '(', '}': '{', ']': '[' };
  for (let i = 0; i < str.length; i++) {
    let char = str[i];
    if (Object.values(mapping).includes(char)) {
      stack.push(char);
    } else if (Object.keys(mapping).includes(char)) {
      if (stack.length === 0 || stack.pop() !== mapping[char]) {
        return false;
      }
    }
  }
  return stack.length === 0;
}

bracketMatch("({[]})");
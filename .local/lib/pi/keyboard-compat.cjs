// Old Kitty/Alacritty versions encode some key releases as duplicate presses.
// Pi requests flags 7 (disambiguation, event types, alternate keys); use 5
// instead, preserving enhanced shortcuts without requesting release events.
const originalWrite = process.stdout.write;
process.stdout.write = function (chunk, ...args) {
  if (typeof chunk === "string") {
    chunk = chunk.replaceAll("\x1b[>7u", "\x1b[>5u");
  }
  return originalWrite.call(this, chunk, ...args);
};

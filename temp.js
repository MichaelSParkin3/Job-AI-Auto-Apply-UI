const escapeAttr = (value) => String(value).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
console.log(escapeAttr("foo'bar\\baz"));

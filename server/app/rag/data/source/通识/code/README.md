# Runnable code examples

Every code snippet that appears in the book's chapters lives here as a runnable file
with a test, so the examples can't rot. Layout:

```
code/ch06/python/   # chapter 6 examples, Python
code/ch06/go/       # the same examples, Go (where a multi-language tab exists)
...
```

Conventions:

- **Python** files run with `python3 <file>` (plain `assert`-based checks run on import)
  or `pytest` where a test file exists.
- **Java** files compile with `javac` and run with `java` (single-file source launch).
- **JavaScript** files run with `node <file>` (Node ≥ 18, built-in `node:assert`).
- **Go** files run with `go run <file>` or `go test` for `_test.go` files.
- **Ruby** files run with `ruby <file>` (built-in `raise`/minitest checks).
- Each file states, in a header comment, the chapter section it appears in. The book
  text and these files are kept in sync by hand — if you change one, change both.

License: MIT, like all code in this book (prose is CC BY-SA 4.0).

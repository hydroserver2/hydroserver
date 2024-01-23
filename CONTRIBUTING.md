# HydroServer - Contributing

HydroServer is open source and released under the [BSD 3-Clause License](LICENSE). You are welcome to send us pull requests to contribute bug fixes or new features. We also invite you to participate in issues, which we use to track and diagnose bugs as well as request features.

If you’d like to contribute to this repository, please follow these steps:

1. [Create an issue](https://github.com/hydroserver2/hydroserver/issues/new/choose)
2. Discuss issue with moderators to make sure it's something we want to apply to the code base
3. Fork the frontend and backend repositories
4. Create a new branch (git checkout -b ISSUE#-my-new-feature) where ISSUE# is the issue id
5. Make changes and commit (git commit -am ‘Add some feature’)
6. Push to the branch (git push origin my-new-feature)
7. Create a pull request

## Pull Request Guidelines

- If adding a new feature:

  - Add an accompanying test case.
  - Provide a convincing reason to add this feature. Ideally, you should open an issue first and have it approved before working on it.

- If fixing a bug:

  - If you are resolving a special issue, add (fix #xxxx) (#xxxx is the issue id) in your PR title for better organization, e.g. update entities encoding/decoding (fix #3899).
  - Provide a detailed description of the bug in the PR.

- Make sure tests pass!

- The PR should fix the intended bug only and not introduce unrelated changes. This includes unnecessary refactors - a PR should focus on the fix and not code style, this makes it easier to trace changes in the future.

- Follow the programming language's conventions. This means if you're writing new code in TypeScript, use the TypeScript conventions. If you're writing Python code, use the Python conventions, etc.

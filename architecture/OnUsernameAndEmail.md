### 1. What is it, and why does Git require it?

Under the hood, Git does not just store a snapshot of your files. Every time you commit, Git generates a cryptographic hash (like `295b880...`) that represents a specific text file format called a "Commit Object."

According to the hardcoded rules of Git, a valid Commit Object **must** contain five things:

1. The Tree hash (the files).
2. The Parent hash (the previous commit).
3. **The Author Name.**
4. **The Author Email.**
5. The Timestamp.

If the name and email are missing, Git literally cannot compute the SHA-1 hash of the commit, and it throws that exact error you saw: `Author identity unknown`.

Git uses this metadata for things like `git blame` (to see who wrote a line of code). However, it is important to know a harsh reality: **Standard Git metadata is completely spoofable.** I can configure my local Git name as "Linus Torvalds" and make a commit, and Git will happily accept it. In our decentralized system, this Git name/email is just for *human readability*. The actual trust and security come from the Ed25519 cryptographic keys we put in `.peerpatch/`.

### 2. How would this work in a real Tailscale system?

In our Docker simulation, we used a hacked environment variable (`NODE_NAME=alice_node`) to automate the profile.

In a real production environment (like a Tailscale mesh), you generally do not want to scrape network hostnames to use as developer identities. A Tailscale machine name might be `pj-macbook-pro-2024.tailnet-xyz.ts.net`, which looks terrible in a Git commit log. You want the user's actual human name and standard developer email.

### 3. Should it be dynamic? (The Best Practice)

Yes, absolutely. Hardcoding it or scraping OS variables is a bad practice for a CLI tool.

If you were releasing PeerPatch as a real product, you would handle this by relying on Git's native fallback hierarchy, mixed with an interactive prompt:

1. **The Global Fallback:** When a developer installs PeerPatch on their laptop, they almost certainly already have standard Git installed and configured globally (`git config --global user.name`). Our Python script should check if those global variables exist first. If they do, we do absolutely nothing. We let Git use their existing profile seamlessly.
2. **The Interactive Prompt:** If `peerp init` or `peerp clone` detects that the user has *never* configured Git (like a fresh virtual machine or a new student), the CLI should pause and ask them:
```text
[*] Git profile not found.
Enter your name for commits: PJ
Enter your email: pj@example.com

```


The script then runs `git config user.name "PJ"` locally for that repository.

This provides a frictionless experience for veteran developers, while safely guiding new users.

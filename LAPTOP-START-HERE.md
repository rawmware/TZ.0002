# Install the approved desktop snapshot on your laptop

This commit preserves the working desktop app as it was when Roman asked to freeze it.
The application source was copied byte-for-byte; hashes are in `docs/DESKTOP-SNAPSHOT.json`.
No further application changes were made for this publication.

Install Python 3.10 or newer, Node.js/npm, Git, and Ollama. Start Ollama, then run:

```text
git clone https://github.com/rawmware/TZ.0002.git
cd TZ.0002
python -m pip install -r requirements-desktop-lock.txt
npm i -g opencode-ai@1.18.31
python install.py --setup-model --desktop
python tz.py --doctor
python tz.py
```

If already cloned, use `git pull --ff-only` in a clean checkout instead of cloning again.
On macOS/Linux, use `python3`; desktop shortcut installation is Windows-only.

The installer recreates the local model alias and launch commands. This requires an initial
model download (~2.5 GB). OpenCode uses local Ollama. The desktop used Ollama 0.34.1,
Node 24.14.0 and Python 3.10.6. Laptop performance depends on its hardware.

Open the TZ shortcut or type `tz`. `/passcode NAME` changes both the display name and
the launch command. `/opencode TASK` uses the integrated agent; `/opencode` opens its UI.

Git carries the application, not the desktop's private chats, credentials, downloaded
model weights or machine-specific paths. Registration recreates those paths on the laptop.
The PowerShell files are preserved for legacy use; `tz.py` is the current desktop entry point.

For Astra on the laptop: install this snapshot, run `--doctor`, and resolve only missing
machine dependencies. Do not redesign or refactor the application. It is the approved build.

#!/bin/bash

echo -e "\n\033[1;92m[⚡ GITHUB]\033[0m \033[1;37mINITIATING UPLINK TO TREVINO WAR ROOM...\033[0m"

# 1. Initialize if needed
if [ ! -d ".git" ]; then
    git init
    git branch -M master
    git remote add origin https://github.com/m5trevino/trevino_war_room.git
fi

# 2. Add all assets
git add .

# 3. Commit with detailed changelog
git commit -m "WAR ROOM v6.0: THE GHOST PROTOCOL

[FEATURE] Ghost Client (Indeed Camouflage V2)
- Added 'High Visibility' UI with Inter font and improved contrast.
- Implemented 'Dual-Mode' architecture (Job Feed vs My Archive).
- Added 'Smuggler Protocol' to inject job tags into the fake UI asynchronously.

[FEATURE] Integrated Groq Laboratory
- Added slide-down settings panel in the Ghost Client.
- Enabled custom model selection (Llama-3.3, Moonshot, etc).
- Added 'Prompt Manager' to save/load custom system prompts (Parker Lewis vs Sniper).

[FEATURE] Time Travel & Reset
- Added 'Burn/Reset' button to delete generated artifacts and revert job status.
- Added 'Dismiss' logic to move targets between lists.

[CORE] Server Logic
- Patched server.py to support prompt overrides and file deletion.
- Fixed 404 errors by restructuring route definitions.
"

# 4. Push
echo -e "\n\033[1;93m[⚡ GITHUB]\033[0m \033[1;37mPUSHING TO MASTER...\033[0m"
git push -u origin master

echo -e "\n\033[1;92m[⚡ GITHUB]\033[0m \033[1;37mDEPLOYMENT COMPLETE.\033[0m"
